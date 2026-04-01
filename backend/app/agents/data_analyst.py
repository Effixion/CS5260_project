import json
from typing import Any

from crewai import Agent as CrewAgent, Task

from app.agents.base import BaseAgent
from app.storage import ProjectManager


class DataAnalystAgent(BaseAgent):
    """Analyzes uploaded datasets and produces summary statistics and insights."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self, manager: ProjectManager, state: dict) -> dict[str, Any]:
        uploaded_files = state.get("uploaded_files", [])
        strategy = self._read_artifact_json(manager, "strategy.json")

        # Build detailed data summaries
        file_summaries = []
        for filename in uploaded_files:
            content = self._read_file_content(manager, filename)
            file_summaries.append(content)

        data_block = "\n\n".join(file_summaries) if file_summaries else "No data files available."
        strategy_block = json.dumps(strategy, indent=2) if strategy else "No strategy available."

        brief = state.get("brief", {})
        if not brief:
            brief = self._read_artifact_json(manager, "brief.json")
        brief_block = json.dumps(brief, indent=2) if brief else "No brief provided."

        agent = CrewAgent(
            role="Data Analyst",
            goal="Analyze datasets thoroughly and extract actionable insights for a presentation.",
            backstory=(
                "You are a senior data analyst who excels at finding patterns, trends, "
                "and key statistics in data. You produce clear, structured analyses that "
                "can be used to create compelling visualizations and presentations."
            ),
            llm=self.llm,
            verbose=False,
        )

        task = Task(
            description=f"""Analyze the following datasets and produce a structured analysis.

ORCHESTRATOR BRIEF (follow these instructions closely):
{brief_block}

PRESENTATION STRATEGY:
{strategy_block}

DATA FILES:
{data_block}

Produce a thorough analysis as a JSON object. Include:
- Per-file summaries with key statistics
- Trends and patterns you've identified
- Specific insights relevant to the presentation
- Recommended visualizations with exact column names

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
  "files_analyzed": ["filename1.csv"],
  "datasets": [
    {{
      "filename": "filename1.csv",
      "summary": "What this dataset represents",
      "key_statistics": [
        {{"label": "Total Records", "value": "1234"}},
        {{"label": "Date Range", "value": "Jan 2020 - Dec 2024"}}
      ],
      "trends": ["Trend description based on actual data"],
      "insights": ["Insight based on actual data"]
    }}
  ],
  "cross_file_insights": ["Insight spanning multiple files if applicable"],
  "recommended_visualizations": [
    {{
      "type": "line",
      "title": "Chart Title",
      "filename": "data.csv",
      "x_column": "exact_column_name",
      "y_column": "exact_column_name",
      "description": "Why this chart is useful"
    }}
  ]
}}

IMPORTANT: Use exact column names from the data. Only recommend chart types: bar, line, scatter, pie, histogram.
The brief specifies how many visualizations to recommend — follow num_visualizations from the brief.

SLIDE-FIT NOTE: These visualizations will be embedded on presentation slides.
- Prefer columns with short, readable labels (avoid recommending columns with long text values as x-axis categories)
- If a categorical column has >10 unique values, note this in the description so the renderer can group/limit them
- Chart titles in the recommendations should be short (~60 chars max)""",
            expected_output="A JSON object containing the data analysis with insights and visualization recommendations.",
            agent=agent,
        )

        result = self._run_crew(agent, task)

        try:
            analysis = self._parse_json(result)
        except (json.JSONDecodeError, ValueError):
            analysis = {
                "files_analyzed": uploaded_files,
                "datasets": [],
                "cross_file_insights": [result[:500]],
                "recommended_visualizations": [],
            }

        manager.save_artifact(
            "data_analysis.json",
            json.dumps(analysis, indent=2).encode(),
        )

        return {"analysis": analysis}
