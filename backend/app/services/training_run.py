from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.entities import Project, TrainingRun
from app.services.dataset import build_dataset_from_export
from app.services.label_studio import LabelStudioClient, LabelStudioError
from app.services.paths import models_dir, staging_dataset_dir, uploads_dir
from app.services.train_service import train_image_folder

ProgressFn = Callable[[dict], None]


def run_training(
    project: Project,
    run_id: int,
    progress: ProgressFn | None = None,
) -> dict:
    def emit(event: dict) -> None:
        if progress:
            progress(event)

    ls = LabelStudioClient()
    if not project.label_studio_project_id:
        raise ValueError("No Label Studio project linked")

    emit({"stage": "export", "message": "Exporting labels from Label Studio…"})

    export = ls.export_json(project.label_studio_project_id)
    class_names = (project.class_a, project.class_b)
    dataset_path = staging_dataset_dir(project, run_id)

    if dataset_path.exists():
        shutil.rmtree(dataset_path)

    emit({"stage": "dataset", "message": "Building training dataset…"})

    counts = build_dataset_from_export(
        export,
        uploads_dir(project),
        dataset_path,
        class_names,
    )

    per_class = {k: v for k, v in counts.items() if not k.startswith("_")}
    if min(per_class.values()) < 2:
        raise ValueError(
            f"Need at least 2 labeled images per class. Counts: {per_class}"
        )

    model_path = models_dir(project) / f"run_{run_id}.pth"

    def on_epoch(epoch: int, total: int, loss: float, accuracy: float) -> None:
        emit({
            "stage": "epoch",
            "message": f"Training epoch {epoch} of {total}…",
            "epoch": epoch,
            "total_epochs": total,
            "loss": round(loss, 4),
            "training_accuracy": round(accuracy, 1),
        })

    emit({"stage": "train", "message": "Training model…", "total_epochs": 15})

    metrics = train_image_folder(
        dataset_path,
        model_path,
        on_epoch=on_epoch,
    )

    return {
        "metrics": metrics,
        "model_path": str(model_path),
        "model_filename": model_path.name,
    }


def run_training_persisted(project_id: int, run_id: int, progress: ProgressFn) -> None:
    session: Session = SessionLocal()
    try:
        project = session.get(Project, project_id)
        run = session.get(TrainingRun, run_id)
        if not project or not run:
            raise ValueError("Project or training run not found")

        run.status = "running"
        session.commit()

        try:
            result = run_training(project, run_id, progress=progress)
            run.status = "done"
            run.model_path = result["model_path"]
            run.metrics_json = json.dumps(result["metrics"])
            run.error_message = None
            session.commit()
            progress({
                "stage": "complete",
                "message": "Training finished.",
                "run_id": run_id,
                "model_filename": result["model_filename"],
                "model_path": result["model_path"],
                "metrics": result["metrics"],
            })
        except (LabelStudioError, ValueError) as exc:
            run.status = "failed"
            run.error_message = str(exc)
            session.commit()
            progress({"stage": "error", "message": str(exc)})
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            session.commit()
            progress({"stage": "error", "message": str(exc)})
    finally:
        session.close()
