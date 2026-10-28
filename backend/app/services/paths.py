from pathlib import Path

from app.config import settings
from app.models.entities import Project


def project_dir(project: Project) -> Path:
    return settings.data_root / "projects" / str(project.id)


def uploads_dir(project: Project) -> Path:
    path = project_dir(project) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir(project: Project) -> Path:
    path = project_dir(project) / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def staging_dataset_dir(project: Project, run_id: int) -> Path:
    return project_dir(project) / "staging" / str(run_id)


def media_url(project_id: int, filename: str) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/api/media/{project_id}/{filename}"
