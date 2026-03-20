import json
import shutil
from pathlib import Path

from app.models import Project, ProjectFile, Message, _now_iso, _short_id


class ProjectManager:
    """Manages a single project's files, messages, and artifacts on disk."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    @property
    def project_file(self) -> Path:
        return self.project_dir / "project.json"

    @property
    def messages_file(self) -> Path:
        return self.project_dir / "messages.json"

    @property
    def files_meta_file(self) -> Path:
        return self.project_dir / "_files_meta.json"

    @property
    def files_dir(self) -> Path:
        d = self.project_dir / "files"
        d.mkdir(exist_ok=True)
        return d

    @property
    def artifacts_dir(self) -> Path:
        d = self.project_dir / "artifacts"
        d.mkdir(exist_ok=True)
        return d

    # --- Project ---

    def save_project(self, project: dict) -> None:
        project["updated_at"] = _now_iso()
        self.project_file.write_text(json.dumps(project, indent=2))

    def load_project(self) -> dict:
        if not self.project_file.exists():
            return {}
        return json.loads(self.project_file.read_text())

    def touch(self) -> None:
        """Update the project's updated_at timestamp."""
        project = self.load_project()
        if project:
            self.save_project(project)

    # --- Messages ---

    def load_messages(self) -> list[dict]:
        if not self.messages_file.exists():
            return []
        return json.loads(self.messages_file.read_text())

    def append_message(self, message: dict) -> dict:
        if "id" not in message:
            message["id"] = _short_id(8)
        if "created_at" not in message:
            message["created_at"] = _now_iso()
        messages = self.load_messages()
        messages.append(message)
        self.messages_file.write_text(json.dumps(messages, indent=2))
        self.touch()
        return message

    def update_message(self, message_id: str, updates: dict) -> dict | None:
        messages = self.load_messages()
        for msg in messages:
            if msg.get("id") == message_id:
                msg.update(updates)
                self.messages_file.write_text(json.dumps(messages, indent=2))
                return msg
        return None

    def delete_messages_after(self, message_id: str) -> int:
        """Delete all messages after the given message_id. Returns count deleted."""
        messages = self.load_messages()
        idx = next((i for i, m in enumerate(messages) if m.get("id") == message_id), None)
        if idx is None:
            return 0
        removed = len(messages) - idx - 1
        messages = messages[: idx + 1]
        self.messages_file.write_text(json.dumps(messages, indent=2))
        self.touch()
        return removed

    # --- Files ---

    def _load_files_meta(self) -> list[dict]:
        if not self.files_meta_file.exists():
            return []
        return json.loads(self.files_meta_file.read_text())

    def _save_files_meta(self, meta: list[dict]) -> None:
        self.files_meta_file.write_text(json.dumps(meta, indent=2))

    def list_files(self) -> list[dict]:
        return self._load_files_meta()

    def save_file(self, filename: str, content: bytes, mime_type: str = "application/octet-stream", note: str = "") -> dict:
        path = self.files_dir / filename
        path.write_bytes(content)

        file_meta = ProjectFile(
            filename=filename,
            original_name=filename,
            size_bytes=len(content),
            mime_type=mime_type,
            note=note,
        ).model_dump()

        meta = self._load_files_meta()
        # Replace if exists, otherwise append
        meta = [m for m in meta if m["filename"] != filename]
        meta.append(file_meta)
        self._save_files_meta(meta)
        self.touch()
        return file_meta

    def rename_file(self, old_name: str, new_name: str) -> dict | None:
        old_path = self.files_dir / old_name
        new_path = self.files_dir / new_name
        if not old_path.exists():
            return None
        old_path.rename(new_path)

        meta = self._load_files_meta()
        for m in meta:
            if m["filename"] == old_name:
                m["filename"] = new_name
                self._save_files_meta(meta)
                self.touch()
                return m
        return None

    def delete_file(self, filename: str) -> bool:
        path = self.files_dir / filename
        if path.exists():
            path.unlink()
        meta = self._load_files_meta()
        new_meta = [m for m in meta if m["filename"] != filename]
        if len(new_meta) == len(meta):
            return False
        self._save_files_meta(new_meta)
        self.touch()
        return True

    def update_file_note(self, filename: str, note: str) -> dict | None:
        meta = self._load_files_meta()
        for m in meta:
            if m["filename"] == filename:
                m["note"] = note
                self._save_files_meta(meta)
                return m
        return None

    def get_file_path(self, filename: str) -> Path:
        return self.files_dir / filename

    # --- Artifacts ---

    def save_artifact(self, filename: str, content: bytes) -> Path:
        path = self.artifacts_dir / filename
        path.write_bytes(content)
        self.touch()
        return path

    def get_artifact_path(self, filename: str) -> Path:
        return self.artifacts_dir / filename

    def list_artifacts(self) -> list[dict]:
        if not self.artifacts_dir.exists():
            return []
        artifacts = []
        for p in sorted(self.artifacts_dir.iterdir()):
            if p.is_file():
                artifacts.append({
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                })
        return artifacts


class ProjectIndex:
    """Manages the top-level project index for listing/creating/deleting projects."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[dict]:
        projects = []
        if not self.base_dir.exists():
            return projects
        for d in self.base_dir.iterdir():
            if d.is_dir():
                pfile = d / "project.json"
                if pfile.exists():
                    try:
                        projects.append(json.loads(pfile.read_text()))
                    except (json.JSONDecodeError, OSError):
                        continue
        projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return projects

    def create_project(self, name: str = "Untitled Presentation") -> dict:
        project = Project(name=name).model_dump()
        project_dir = self.base_dir / project["id"]
        project_dir.mkdir(parents=True, exist_ok=True)

        manager = ProjectManager(project_dir)
        manager.save_project(project)

        # Seed initial greeting message
        greeting = Message(
            role="assistant",
            content="What slides would you like to create today?",
            content_type="text",
        ).model_dump()
        manager.append_message(greeting)

        return project

    def delete_project(self, project_id: str) -> bool:
        project_dir = self.base_dir / project_id
        if not project_dir.exists():
            return False
        shutil.rmtree(project_dir)
        return True

    def get_manager(self, project_id: str) -> ProjectManager:
        project_dir = self.base_dir / project_id
        if not project_dir.exists():
            raise FileNotFoundError(f"Project {project_id} not found")
        return ProjectManager(project_dir)
