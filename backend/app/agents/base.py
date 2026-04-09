import json
import re
from abc import ABC, abstractmethod
from typing import Any

from crewai import Agent as CrewAgent, Task, Crew, LLM
from litellm import cost_per_token

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

    def _run_crew(self, agent: CrewAgent, task: Task) -> tuple[str, dict]:
        """Create a single-agent Crew, kick it off, and return the raw result."""
        crew = Crew(
            agents=[agent],
            tasks=[task],
            # Set to True to track AI progress
            verbose=True,
        )
        # 1. THE SAFETY NET: Catch internal CrewAI/LiteLLM crashes
        try:
            result = crew.kickoff()
        except Exception as e:
            print(f"\n--- API OR LIBRARY CRASH CAUGHT ---\n{e}\n-----------------------------------")
            # If the library crashes, return a safe empty string.
            # Your agents will gracefully fall back to their default JSON/Text 
            # instead of crashing the whole pipeline!
            return "", {"cost_usd": 0.0}

        # 2. Safe Token Extraction
        usage_dict = {"cost_usd": 0.0}
        
        try:
            # Safely check for token usage without letting the library crash
            if hasattr(result, "token_usage") and result.token_usage:
                prompt_tokens = getattr(result.token_usage, "prompt_tokens", 0)
                comp_tokens = getattr(result.token_usage, "completion_tokens", 0)
                
                usage_dict["prompt_tokens"] = prompt_tokens
                usage_dict["completion_tokens"] = comp_tokens
                usage_dict["total_tokens"] = getattr(result.token_usage, "total_tokens", 0)

                # Calculate Cost
                prompt_cost, comp_cost = cost_per_token(
                    model=self.llm.model, 
                    prompt_tokens=prompt_tokens,
                    completion_tokens=comp_tokens
                )
                usage_dict["cost_usd"] = prompt_cost + comp_cost
        except Exception as e:
            print(f"Token tracking skipped due to API quirk: {e}")

        # Ensure we always safely return a string for the result
        raw_output = result.raw if hasattr(result, "raw") else str(result)
        return raw_output, usage_dict