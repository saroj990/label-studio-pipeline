from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.entities import Project, TrainingRun, User
from app.schemas.projects import (
    LabelRequest,
    PredictResponse,
    ProjectCreate,
    ProjectResponse,
    SaveModelRequest,
    SavedModelResponse,
    TaskResponse,
    TrainResponse,
)
from app.services.dataset import parse_label
from app.services.label_studio import LabelStudioClient, LabelStudioError
from app.services.paths import media_url, models_dir, uploads_dir
from app.services.predict_service import predict_image
from app.services.training_run import run_training, run_training_persisted

router = APIRouter(prefix="/projects", tags=["projects"])


def _resolve_training_run(project: Project, db: Session) -> TrainingRun | None:
    if project.active_training_run_id:
        run = (
            db.query(TrainingRun)
            .filter(
                TrainingRun.id == project.active_training_run_id,
                TrainingRun.project_id == project.id,
                TrainingRun.status == "done",
                TrainingRun.model_path.isnot(None),
            )
            .first()
        )
        if run:
            return run
    return (
        db.query(TrainingRun)
        .filter(
            TrainingRun.project_id == project.id,
            TrainingRun.status == "done",
            TrainingRun.model_path.isnot(None),
        )
        .order_by(TrainingRun.id.desc())
        .first()
    )


def get_owned_project(
    project_id: int,
    user: User,
    db: Session,
) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Project).filter(Project.owner_id == user.id).all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.class_a.strip().lower() == body.class_b.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Class names must be different",
        )

    ls = LabelStudioClient()
    try:
        ls_id = ls.create_project(body.name, body.class_a, body.class_b)
    except LabelStudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    project = Project(
        owner_id=user.id,
        name=body.name,
        class_a=body.class_a.strip(),
        class_b=body.class_b.strip(),
        label_studio_project_id=ls_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    uploads_dir(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_owned_project(project_id, user, db)


@router.get("/{project_id}/label-studio-url")
def label_studio_url(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    if not project.label_studio_project_id:
        raise HTTPException(status_code=400, detail="No Label Studio project linked")
    ls = LabelStudioClient()
    return {"url": ls.project_url(project.label_studio_project_id)}


@router.post("/{project_id}/upload")
async def upload_images(
    project_id: int,
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    if not project.label_studio_project_id:
        raise HTTPException(status_code=400, detail="No Label Studio project linked")

    up = uploads_dir(project)
    ls = LabelStudioClient()
    tasks_to_import: list[dict] = []
    saved: list[str] = []

    for upload in files:
        if not upload.filename:
            continue
        safe_name = Path(upload.filename).name
        dest = up / safe_name
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = up / f"{stem}_{counter}{suffix}"
                counter += 1

        content = await upload.read()
        dest.write_bytes(content)
        saved.append(dest.name)

        url = media_url(project.id, dest.name)
        tasks_to_import.append({
            "data": {"image": url},
            "meta": {"filename": dest.name},
        })

    if tasks_to_import:
        try:
            ls.import_tasks(project.label_studio_project_id, tasks_to_import)
        except LabelStudioError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"uploaded": saved, "count": len(saved)}


@router.get("/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    if not project.label_studio_project_id:
        return []

    ls = LabelStudioClient()
    try:
        tasks = ls.list_tasks(project.label_studio_project_id)
    except LabelStudioError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    class_names = (project.class_a, project.class_b)
    result: list[TaskResponse] = []

    for task in tasks:
        if not isinstance(task, dict):
            continue
        data = task.get("data") or {}
        if isinstance(data, str):
            image_url = data
            data = {}
        else:
            image_url = str(data.get("image") or data.get("image_url") or "")
        meta = task.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        filename = meta.get("filename")
        if not filename and image_url:
            filename = Path(image_url).name
        label = parse_label(task, class_names)
        task_id = task.get("id")
        if task_id is None:
            continue
        result.append(
            TaskResponse(
                id=int(task_id),
                image_url=image_url,
                filename=filename,
                label=label,
            )
        )
    return result


@router.post("/{project_id}/tasks/{task_id}/label")
def label_task(
    project_id: int,
    task_id: int,
    body: LabelRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    choice = body.choice.strip()
    if choice not in (project.class_a, project.class_b):
        raise HTTPException(
            status_code=400,
            detail=f"Choice must be {project.class_a!r} or {project.class_b!r}",
        )

    ls = LabelStudioClient()
    try:
        ls.create_annotation(task_id, choice)
    except LabelStudioError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"task_id": task_id, "label": choice}


@router.post("/{project_id}/train", response_model=TrainResponse)
def train_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    if not project.label_studio_project_id:
        raise HTTPException(status_code=400, detail="No Label Studio project linked")

    run = TrainingRun(project_id=project.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        result = run_training(project, run.id)
        run.status = "done"
        run.model_path = result["model_path"]
        run.metrics_json = json.dumps(result["metrics"])
        db.commit()
        return TrainResponse(
            run_id=run.id,
            status=run.status,
            metrics=result["metrics"],
            model_filename=result["model_filename"],
            model_path=result["model_path"],
        )
    except (LabelStudioError, ValueError) as exc:
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{project_id}/train/stream")
def train_project_stream(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    if not project.label_studio_project_id:
        raise HTTPException(status_code=400, detail="No Label Studio project linked")

    run = TrainingRun(project_id=project.id, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)

    event_queue: queue.Queue[dict | None] = queue.Queue()

    def worker() -> None:
        run_training_persisted(project.id, run.id, event_queue.put)
        event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            item = event_queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{project_id}/models/active", response_model=SavedModelResponse | None)
def get_active_model(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    run = _resolve_training_run(project, db)
    if not run or not run.model_path:
        return None
    path = Path(run.model_path)
    return SavedModelResponse(
        run_id=run.id,
        model_filename=path.name,
        model_path=str(path),
        saved=project.active_training_run_id == run.id,
    )


@router.post("/{project_id}/models/save", response_model=SavedModelResponse)
def save_active_model(
    project_id: int,
    body: SaveModelRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    run: TrainingRun | None = None
    if body.run_id is not None:
        run = (
            db.query(TrainingRun)
            .filter(
                TrainingRun.id == body.run_id,
                TrainingRun.project_id == project.id,
                TrainingRun.status == "done",
                TrainingRun.model_path.isnot(None),
            )
            .first()
        )
    else:
        run = _resolve_training_run(project, db)

    if not run or not run.model_path:
        raise HTTPException(status_code=404, detail="No trained model to save")

    path = Path(run.model_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Model file missing on disk")

    project.active_training_run_id = run.id
    db.commit()

    return SavedModelResponse(
        run_id=run.id,
        model_filename=path.name,
        model_path=str(path),
        saved=True,
    )


@router.get("/{project_id}/models/latest")
def download_latest_model(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    run = _resolve_training_run(project, db)
    if not run or not run.model_path:
        raise HTTPException(status_code=404, detail="No trained model yet")

    path = Path(run.model_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Model file missing on disk")

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=path.name,
    )


@router.post("/{project_id}/predict", response_model=PredictResponse)
async def predict(
    project_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(project_id, user, db)
    run = _resolve_training_run(project, db)
    if not run or not run.model_path:
        raise HTTPException(
            status_code=400,
            detail="Save or train a model before predicting",
        )

    model_path = Path(run.model_path)
    if not model_path.is_file():
        raise HTTPException(status_code=404, detail="Model file missing")

    tmp_dir = models_dir(project) / "predict_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    tmp_path = tmp_dir / f"upload{suffix}"
    tmp_path.write_bytes(await file.read())

    try:
        prediction, scores = predict_image(model_path, tmp_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return PredictResponse(prediction=prediction, scores=scores)
