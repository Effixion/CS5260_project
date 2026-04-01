import json
import subprocess
from typing import Any

from crewai import Agent as CrewAgent, Task

from app.agents.base import BaseAgent
from app.storage import ProjectManager


class LatexAuthorAgent(BaseAgent):
    """Generates LaTeX source for the presentation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self, manager: ProjectManager, state: dict) -> dict[str, Any]:
        strategy = self._read_artifact_json(manager, "strategy.json")
        analysis = self._read_artifact_json(manager, "data_analysis.json")
        selected_plots = state.get("selected_visualizations", [])

        brief = state.get("brief", {})
        if not brief:
            brief = self._read_artifact_json(manager, "brief.json")
        brief_block = json.dumps(brief, indent=2) if brief else "No brief provided."
        num_slides = brief.get("num_slides", 10)

        strategy_block = json.dumps(strategy, indent=2) if strategy else "No strategy available."
        analysis_block = json.dumps(analysis, indent=2) if analysis else "No analysis available."
        plots_block = ", ".join(selected_plots) if selected_plots else "No plots selected."

        agent = CrewAgent(
            role="LaTeX Presentation Author",
            goal="Generate a complete, compilable Beamer LaTeX presentation with real content from the data analysis.",
            backstory=(
                "You are an expert LaTeX author who creates professional academic presentations "
                "using Beamer. You write clear, well-structured slides with real data insights."
            ),
            llm=self.llm,
            verbose=False,
        )

        task = Task(
            description=f"""Generate a complete LaTeX Beamer presentation with exactly {num_slides} slides total (including title and conclusion).

ORCHESTRATOR BRIEF (follow these instructions closely):
{brief_block}

PRESENTATION STRATEGY:
{strategy_block}

DATA ANALYSIS:
{analysis_block}

SELECTED PLOT IMAGES (include these with \\includegraphics):
{plots_block}

Requirements:
- Use \\documentclass{{beamer}} with the Madrid theme
- Set the title from the strategy
- Author: Haitham AI
- Create a title slide
- Create content slides for each section in the strategy
- Include REAL data insights and statistics from the analysis — not placeholder text
- For each selected plot image, include it on an appropriate slide using:
  \\includegraphics[width=\\textwidth]{{{selected_plots[0] if selected_plots else 'plot.png'}}}
  (use the exact filenames provided)
- Add bullet points with actual findings
- Include a conclusions slide summarizing key takeaways
- Properly escape special characters (%, &, $, #, _)

SLIDE-FIT CONSTRAINTS (critical — all content must fit on screen without overflow):
- Max 5-6 bullet points per slide, each bullet max ~12 words
- When a slide has an \\includegraphics, use [width=0.85\\textwidth] and limit surrounding text to 1-2 short lines so the image + text both fit
- Never put two \\includegraphics on the same frame
- Keep frame titles under ~50 characters
- If a section has too much content, split into multiple frames rather than cramming
- Use \\small or \\footnotesize ONLY for source citations, never for body text
- Prefer tables with \\small and max 5 rows when showing numeric comparisons — they fit better than long bullet lists

Respond with ONLY the complete LaTeX source code. No markdown fences, no explanation.""",
            expected_output="Complete LaTeX Beamer source code for the presentation.",
            agent=agent,
        )

        result = self._run_crew(agent, task)

        # Clean up any markdown fences the LLM might have added
        latex_content = result.strip()
        if latex_content.startswith("```"):
            lines = latex_content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            latex_content = "\n".join(lines).strip()

        manager.save_artifact("presentation.tex", latex_content.encode())

        artifacts = [{
            "type": "tex",
            "url": f"/projects/{state['id']}/artifacts/presentation.tex",
            "filename": "presentation.tex",
        }]

        # Attempt PDF compilation
        pdf_path = self._compile_pdf(manager)
        if pdf_path:
            artifacts.append({
                "type": "pdf",
                "url": f"/projects/{state['id']}/artifacts/presentation.pdf",
                "filename": "presentation.pdf",
            })

        return {"artifacts": artifacts}

    def _compile_pdf(self, manager: ProjectManager):
        """Try to compile presentation.tex to PDF. Returns path if successful, None otherwise."""
        artifacts_dir = manager.artifacts_dir
        tex_path = artifacts_dir / "presentation.tex"
        pdf_path = artifacts_dir / "presentation.pdf"

        if not tex_path.exists():
            return None

        try:
            # Run pdflatex twice for references
            for _ in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "presentation.tex"],
                    cwd=str(artifacts_dir),
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    return None

            if pdf_path.exists():
                return pdf_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # pdflatex not installed or timed out
            pass

        return None
