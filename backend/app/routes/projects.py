import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage import ProjectIndex

router = APIRouter(prefix="/projects", tags=["projects"])

STORAGE_PATH = Path(os.environ.get("PROJECT_STORAGE_PATH", "./projects"))
index = ProjectIndex(STORAGE_PATH)


class CreateProjectRequest(BaseModel):
    name: str = "Untitled Presentation"


class UpdateProjectRequest(BaseModel):
    name: str | None = None


@router.get("")
async def list_projects():
    return index.list_projects()


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest | None = None):
    name = body.name if body else "Untitled Presentation"
    project = index.create_project(name=name)
    return project


@router.get("/{project_id}")
async def get_project(project_id: str):
    try:
        manager = index.get_manager(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    project = manager.load_project()
    project["files"] = manager.list_files()
    project["artifacts"] = manager.list_artifacts()
    project["message_count"] = len(manager.load_messages())
    project["token_usage"] = project.get("token_usage") or {}
    return project


@router.patch("/{project_id}")
async def update_project(project_id: str, body: UpdateProjectRequest):
    try:
        manager = index.get_manager(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    project = manager.load_project()
    if body.name is not None:
        project["name"] = body.name
    manager.save_project(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    if not index.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return None
