import json
import re
from abc import ABC, abstractmethod
from typing import Any

from crewai import Agent as CrewAgent, Task, Crew, LLM

from app.storage import ProjectManager


class BaseAgent(ABC):
    """Base class for all pipeline agents."""

    def __init__(self, name: str, llm: LLM):
        self.name = name
        self.llm = llm

    @abstractmethod
    async def execute(self, manager: ProjectManager, state: dict) -> dict[str, Any]:
        ...

    def _read_file_content(self, manager: ProjectManager, filename: str) -> str:
        """Read an uploaded file and return a text summary."""
        path = manager.get_file_path(filename)
        if not path.exists():
            return f"[File {filename} not found]"

        suffix = path.suffix.lower()

        if suffix == ".csv":
            import pandas as pd
            df = pd.read_csv(path)
            parts = [
                f"CSV: {filename} — {len(df)} rows, {len(df.columns)} columns",
                f"Columns: {list(df.columns)}",
                f"\nFirst 50 rows:\n{df.head(50).to_string()}",
                f"\nDescriptive stats:\n{df.describe(include='all').to_string()}",
            ]
            return "\n".join(parts)

        if suffix == ".pdf":
            try:
                from pdfminer.high_level import extract_text
                return f"PDF: {filename}\n\n{extract_text(str(path))[:10000]}"
            except Exception:
                return f"[Could not extract text from PDF {filename}]"

        # Plain text / other
        try:
            return f"File: {filename}\n\n{path.read_text(errors='ignore')[:10000]}"
        except Exception:
            return f"[Could not read {filename}]"

    def _read_artifact_json(self, manager: ProjectManager, filename: str) -> dict:
        """Read a previously saved JSON artifact."""
        path = manager.get_artifact_path(filename)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _parse_json(self, text: str) -> dict | list:
        """Parse JSON from LLM response, stripping markdown fences."""
        text = text.strip()
        # Strip ```json ... ``` or ``` ... ```
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
        return json.loads(text)

    def _run_crew(self, agent: CrewAgent, task: Task) -> str:
        """Create a single-agent Crew, kick it off, and return the raw result."""
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False,
        )
        result = crew.kickoff()
        return result.raw
