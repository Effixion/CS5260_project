import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.storage import ProjectIndex
from app.models import Message
from app.utils import parse_file_refs
from app.orchestrator import handle_message, handle_visualization_selection

router = APIRouter(prefix="/projects/{project_id}", tags=["chat"])

STORAGE_PATH = Path(os.environ.get("PROJECT_STORAGE_PATH", "./projects"))
index = ProjectIndex(STORAGE_PATH)


def _get_manager(project_id: str):
    try:
        return index.get_manager(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")


class SendMessageRequest(BaseModel):
    content: str
    file_refs: list[str] | None = None


class SelectVisualizationsRequest(BaseModel):
    selected: list[str]


@router.get("/messages")
async def get_messages(project_id: str):
    manager = _get_manager(project_id)
    return manager.load_messages()


@router.post("/messages")
async def send_message(project_id: str, body: SendMessageRequest):
    manager = _get_manager(project_id)

    # Parse @file references from content
    available_files = [f["filename"] for f in manager.list_files()]
    _, parsed_refs = parse_file_refs(body.content, available_files)

    # Merge explicit file_refs with parsed ones
    all_refs = list(set((body.file_refs or []) + parsed_refs))

    # Persist the user message
    user_msg = Message(
        role="user",
        content=body.content,
        content_type="text",
        file_refs=all_refs,
    ).model_dump()
    manager.append_message(user_msg)

    # Get full message history for orchestrator context
    messages = manager.load_messages()

    # Return SSE stream from orchestrator
    return EventSourceResponse(handle_message(manager, user_msg, messages))


@router.delete("/messages/{message_id}/after")
async def delete_messages_after(project_id: str, message_id: str):
    manager = _get_manager(project_id)
    removed = manager.delete_messages_after(message_id)
    return {"removed": removed}


@router.post("/messages/{message_id}/select")
async def select_visualizations(
    project_id: str,
    message_id: str,
    body: SelectVisualizationsRequest,
):
    manager = _get_manager(project_id)

    if not body.selected:
        raise HTTPException(status_code=400, detail="Must select at least one visualization")

    return EventSourceResponse(
        handle_visualization_selection(manager, message_id, body.selected)
    )
