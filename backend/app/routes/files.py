import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.storage import ProjectIndex

router = APIRouter(prefix="/projects/{project_id}", tags=["files"])

STORAGE_PATH = Path(os.environ.get("PROJECT_STORAGE_PATH", "./projects"))
index = ProjectIndex(STORAGE_PATH)


def _get_manager(project_id: str):
    try:
        return index.get_manager(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")


class UpdateFileRequest(BaseModel):
    name: str | None = None
    note: str | None = None


# --- User-uploaded files ---

@router.get("/files")
async def list_files(project_id: str):
    manager = _get_manager(project_id)
    return manager.list_files()


@router.post("/files", status_code=201)
async def upload_files(project_id: str, files: list[UploadFile] = File(...)):
    manager = _get_manager(project_id)
    results = []
    for f in files:
        content = await f.read()
        mime = f.content_type or "application/octet-stream"
        meta = manager.save_file(f.filename, content, mime_type=mime)
        results.append(meta)
    return results


@router.patch("/files/{filename:path}")
async def update_file(project_id: str, filename: str, body: UpdateFileRequest):
    manager = _get_manager(project_id)

    result = None
    if body.name is not None and body.name != filename:
        result = manager.rename_file(filename, body.name)
        if result is None:
            raise HTTPException(status_code=404, detail="File not found")
        filename = body.name

    if body.note is not None:
        result = manager.update_file_note(filename, body.note)
        if result is None:
            raise HTTPException(status_code=404, detail="File not found")

    if result is None:
        raise HTTPException(status_code=400, detail="No updates provided")
    return result


@router.delete("/files/{filename:path}", status_code=204)
async def delete_file(project_id: str, filename: str):
    manager = _get_manager(project_id)
    if not manager.delete_file(filename):
        raise HTTPException(status_code=404, detail="File not found")
    return None


@router.get("/files/{filename:path}/download")
async def download_file(project_id: str, filename: str):
    manager = _get_manager(project_id)
    path = manager.get_file_path(filename)

    # Path traversal protection
    safe_path = path.resolve()
    safe_base = manager.files_dir.resolve()
    if not str(safe_path).startswith(str(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(safe_path)


# --- Generated artifacts ---

@router.get("/artifacts/{filename:path}")
async def get_artifact(project_id: str, filename: str):
    manager = _get_manager(project_id)
    path = manager.get_artifact_path(filename)

    # Path traversal protection
    safe_path = path.resolve()
    safe_base = manager.artifacts_dir.resolve()
    if not str(safe_path).startswith(str(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(safe_path, filename=safe_path.name)
