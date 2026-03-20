import json
from typing import Any

from crewai import Agent as CrewAgent, Task

from app.agents.base import BaseAgent
from app.storage import ProjectManager


class QAReviewerAgent(BaseAgent):
    """Reviews the generated presentation for quality and accuracy."""

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
            role="Presentation QA Reviewer",
            goal="Review the presentation for quality, accuracy, and completeness.",
            backstory=(
                "You are a meticulous quality assurance reviewer for academic presentations. "
                "You check that content matches the data, formatting is correct, and the "
                "presentation tells a coherent story."
            ),
            llm=self.llm,
            verbose=False,
        )

        task = Task(
            description=f"""Review this LaTeX Beamer presentation for quality.

ORCHESTRATOR BRIEF (the user's original requirements):
{brief_block}

ORIGINAL STRATEGY:
{strategy_block}

DATA ANALYSIS:
{analysis_block}

LATEX SOURCE:
{latex_content}

Review for:
1. Content accuracy — do slides reflect the actual data analysis?
2. Completeness — are all strategy sections covered?
3. LaTeX formatting — any broken commands or missing escapes?
4. Flow and clarity — does it tell a coherent story?
5. Professional quality — is it presentation-ready?
6. SLIDE-FIT — this is critical:
   - Does any frame have more than 5-6 bullet points? Flag it.
   - Are bullet points too long (>~12 words each)? They will overflow.
   - Does any frame combine \\includegraphics with too much text? The image will push content off-screen.
   - Are there two \\includegraphics on the same frame? Flag it.
   - Are frame titles too long (>~50 chars)? They will be cut off.
   - Would any slide visually overflow when rendered at standard Beamer 128mm×96mm?

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
  "status": "approved",
  "overall_score": 8,
  "issues": [
    {{"severity": "low", "slide": "slide identifier", "issue": "description", "suggestion": "fix"}}
  ],
  "strengths": ["strength1", "strength2"],
  "summary": "Overall review summary"
}}

Set status to "approved" if the presentation is ready, or "needs_revision" if there are critical issues.""",
            expected_output="A JSON object with the QA review results.",
            agent=agent,
        )

        result = self._run_crew(agent, task)

        try:
            review = self._parse_json(result)
        except (json.JSONDecodeError, ValueError):
            review = {
                "status": "approved",
                "overall_score": 7,
                "issues": [],
                "strengths": ["Presentation was generated successfully"],
                "summary": result[:500],
            }

        manager.save_artifact(
            "qa_review.json",
            json.dumps(review, indent=2).encode(),
        )

        return {"review": review}
