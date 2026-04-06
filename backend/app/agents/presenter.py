import json
from typing import Any

from crewai import Agent as CrewAgent, Task

from app.agents.base import BaseAgent
from app.storage import ProjectManager


class PresenterAgent(BaseAgent):
    """Generates a presenter script with speaker notes for each slide."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self, manager: ProjectManager, state: dict) -> dict[str, Any]:
        strategy = self._read_artifact_json(manager, "strategy.json")
        analysis = self._read_artifact_json(manager, "data_analysis.json")

        tex_path = manager.get_artifact_path("presentation.tex")
        latex_content = ""
        if tex_path.exists():
            latex_content = tex_path.read_text(errors="ignore")

        brief = state.get("brief", {})
        if not brief:
            brief = self._read_artifact_json(manager, "brief.json")
        brief_block = json.dumps(brief, indent=2) if brief else "No brief provided."

        strategy_block = json.dumps(strategy, indent=2) if strategy else "No strategy."
        analysis_block = json.dumps(analysis, indent=2) if analysis else "No analysis."

        agent = CrewAgent(
            role="Presentation Coach",
            goal="Create detailed, natural speaker notes for every slide in the presentation.",
            backstory=(
                "You are an experienced presentation coach who helps speakers deliver "
                "compelling talks. You write natural, conversational speaker notes that "
                "help presenters explain their data clearly and confidently."
            ),
            llm=self.llm,
            verbose=False,
        )

        task = Task(
            description=f"""Generate detailed speaker notes for each slide in this presentation.

ORCHESTRATOR BRIEF (match the tone and audience):
{brief_block}

PRESENTATION STRATEGY:
{strategy_block}

DATA ANALYSIS:
{analysis_block}

LATEX SOURCE:
{latex_content}

For each slide (identified by \\begin{{frame}}{{Title}}), write:
- A natural speaking script (2-3 paragraphs)
- Key talking points to emphasize
- Transition phrases to the next slide

Format as plain text:

===== Slide 1: Title Slide =====
[speaker notes for title slide]

===== Slide 2: [Next Slide Title] =====
[speaker notes]

Continue for ALL slides in the presentation.
Use actual data points and insights from the analysis in the speaker notes.""",
            expected_output="Complete speaker notes for every slide in the presentation.",
            agent=agent,
        )

        result, usage = self._run_crew(agent, task)

        # Clean up markdown fences if present
        script = result.strip()
        if script.startswith("```"):
            lines = script.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            script = "\n".join(lines).strip()

        manager.save_artifact("presenter_script.txt", script.encode())

        artifacts = [{
            "type": "presenter_script",
            "url": f"/projects/{state['id']}/artifacts/presenter_script.txt",
            "filename": "presenter_script.txt",
        }]

        return {"artifacts": artifacts, "usage": usage}
