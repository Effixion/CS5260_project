import json
from typing import Any

from crewai import Agent as CrewAgent, Task

from app.agents.base import BaseAgent
from app.storage import ProjectManager


class StrategistAgent(BaseAgent):
    """Analyzes uploaded data and creates a presentation strategy."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self, manager: ProjectManager, state: dict) -> dict[str, Any]:
        uploaded_files = state.get("uploaded_files", [])
        file_contexts = state.get("file_contexts", {})

        # Build data summaries
        file_summaries = []
        for filename in uploaded_files:
            note = file_contexts.get(filename, "")
            content = self._read_file_content(manager, filename)
            entry = f"--- {filename} ---"
            if note:
                entry += f"\nUser note: {note}"
            entry += f"\n{content}"
            file_summaries.append(entry)

        data_block = "\n\n".join(file_summaries) if file_summaries else "No files uploaded yet."

        brief = state.get("brief", {})
        brief_block = json.dumps(brief, indent=2) if brief else "No brief provided — use sensible defaults."

        agent = CrewAgent(
            role="Presentation Strategist",
            goal="Create a clear, compelling presentation strategy based on the provided data.",
            backstory=(
                "You are an expert at structuring academic and business presentations. "
                "You analyze data to identify the most important themes and create a logical "
                "flow that tells a compelling story."
            ),
            llm=self.llm,
            verbose=False,
        )

        task = Task(
            description=f"""Analyze the following data files and create a presentation strategy.

ORCHESTRATOR BRIEF (follow these instructions closely):
{brief_block}

DATA FILES:
{data_block}

Create a JSON presentation strategy with:
- A compelling title based on the actual data
- A subtitle
- Sections that match the requested num_slides from the brief (subtract 2 for title+conclusion slides). Each section has key_points and suggested_plots.
- Overall themes
- The tone, audience, and presentation_type from the brief should shape the language and structure

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
  "title": "Presentation title based on the data",
  "subtitle": "Optional subtitle",
  "author": "Haitham AI",
  "sections": [
    {{
      "title": "Section Name",
      "key_points": ["point based on real data", "another point"],
      "suggested_plots": ["description of a useful chart for this section"]
    }}
  ],
  "themes": ["theme1", "theme2"]
}}""",
            expected_output="A JSON object containing the presentation strategy.",
            agent=agent,
        )

        result, usage = self._run_crew(agent, task)

        try:
            strategy = self._parse_json(result)
        except (json.JSONDecodeError, ValueError):
            strategy = {
                "title": "Data Presentation",
                "subtitle": "",
                "author": "Haitham AI",
                "sections": [
                    {"title": "Overview", "key_points": [result[:500]], "suggested_plots": []}
                ],
                "themes": [],
            }

        strategy["uploaded_files"] = uploaded_files

        manager.save_artifact(
            "strategy.json",
            json.dumps(strategy, indent=2).encode(),
        )

        return {"strategy": strategy, "usage": usage}
