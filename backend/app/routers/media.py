from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(tags=["media"])


@router.get("/api/media/{project_id}/{filename}")
def serve_media(project_id: int, filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = settings.data_root / "projects" / str(project_id) / "uploads" / safe_name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
