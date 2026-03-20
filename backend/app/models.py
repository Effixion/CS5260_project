from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id(length: int = 12) -> str:
    import uuid
    return uuid.uuid4().hex[:length]


class Project(BaseModel):
    id: str = Field(default_factory=lambda: _short_id(12))
    name: str = "Untitled Presentation"
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)
    status: str = "active"  # "active" | "completed"


class ProjectFile(BaseModel):
    filename: str
    original_name: str
    size_bytes: int
    mime_type: str = "application/octet-stream"
    note: str = ""
    uploaded_at: str = Field(default_factory=_now_iso)


class Message(BaseModel):
    id: str = Field(default_factory=lambda: _short_id(8))
    role: str  # "user" | "assistant" | "system"
    content: str
    content_type: str = "text"  # "text" | "visualization_picker" | "artifact" | "status"
    file_refs: list[str] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now_iso)
