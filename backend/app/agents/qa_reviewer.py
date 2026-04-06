import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from crewai import Agent as CrewAgent, Task

from app.agents.base import BaseAgent
from app.storage import ProjectManager


class QAReviewerAgent(BaseAgent):
    """Reviews the generated presentation for quality and accuracy.

    Performs two QA passes:
      1. LaTeX code review  — LLM analyses .tex source + pdflatex compilation log
      2. Visual PDF review  — PyMuPDF renders pages to images, VLM inspects for overflow
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Pass 0: Compile LaTeX
    # ------------------------------------------------------------------

    def _compile_and_check(self, manager: ProjectManager) -> dict:
        """Compile presentation.tex and parse the pdflatex log for issues."""
        artifacts_dir = manager.artifacts_dir
        tex_path = artifacts_dir / "presentation.tex"
        pdf_path = artifacts_dir / "presentation.pdf"

        result = {
            "success": False,
            "errors": [],
            "warnings": [],
            "overfull_boxes": [],
            "pdf_path": None,
        }

        if not tex_path.exists():
            result["errors"].append("presentation.tex not found")
            return result

        try:
            last_stdout = ""
            for pass_num in range(2):
                proc = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "presentation.tex"],
                    cwd=str(artifacts_dir),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                last_stdout = proc.stdout or ""

                if proc.returncode != 0 and pass_num == 0:
                    self._parse_log(last_stdout, result)
                    return result

            self._parse_log(last_stdout, result)

            if pdf_path.exists():
                result["success"] = True
                result["pdf_path"] = str(pdf_path)

        except FileNotFoundError:
            result["errors"].append("pdflatex not installed on this system")
        except subprocess.TimeoutExpired:
            result["errors"].append("pdflatex compilation timed out (>30s)")

        return result

    def _parse_log(self, log_text: str, result: dict) -> None:
        """Parse pdflatex log output for errors, warnings, and overfull boxes."""
        for line in log_text.split("\n"):
            line = line.strip()
            if line.startswith("!"):
                result["errors"].append(line)
            elif "LaTeX Warning:" in line:
                result["warnings"].append(line)
            elif re.match(r"(Over|Under)full \\[hv]box", line):
                result["overfull_boxes"].append(line)

    # ------------------------------------------------------------------
    # Pass 1: LaTeX code QA (text LLM)
    # ------------------------------------------------------------------

    def _run_latex_qa(
        self,
        latex_content: str,
        brief_block: str,
        strategy_block: str,
        analysis_block: str,
        compilation_report: str,
    ) -> dict:
        """LLM pass over the raw .tex source and compilation log."""
        agent = CrewAgent(
            role="LaTeX QA Reviewer",
            goal="Review the LaTeX source code for correctness, style, and slide-fit.",
            backstory=(
                "You are a meticulous LaTeX expert. You check Beamer source code for "
                "broken commands, missing escapes, content overflow, and whether the "
                "slides faithfully represent the underlying data analysis."
            ),
            llm=self.llm,
            verbose=False,
        )

        task = Task(
            description=f"""Review this LaTeX Beamer presentation source code.

ORCHESTRATOR BRIEF:
{brief_block}

STRATEGY:
{strategy_block}

DATA ANALYSIS:
{analysis_block}

{compilation_report}

LATEX SOURCE:
{latex_content}

Review for:
1. Content accuracy — do slides reflect the actual data analysis?
2. Completeness — are all strategy sections covered?
3. LaTeX formatting — broken commands, missing escapes, unclosed braces?
4. Flow and clarity — coherent story arc?
5. COMPILATION ISSUES — review the compilation result above. Flag errors and overfull boxes.
6. SLIDE-FIT — critical:
   - >5-6 bullet points per frame? Flag it.
   - Bullets >~12 words? They will overflow.
   - \\includegraphics mixed with too much text? Image will push content off-screen.
   - Two \\includegraphics on the same frame? Flag it.
   - Frame titles >~50 chars? Will be cut off.

Respond with ONLY a valid JSON object (no markdown):
{{
  "issues": [
    {{"severity": "low|critical", "slide": "slide id", "issue": "description", "suggestion": "fix"}}
  ],
  "strengths": ["strength1"],
  "summary": "one-paragraph summary"
}}""",
            expected_output="JSON object with LaTeX QA results.",
            agent=agent,
        )

        result, usage = self._run_crew(agent, task)

        try:
            parsed_result = self._parse_json(result)
        except (json.JSONDecodeError, ValueError):
            parsed_result = {"issues": [], "strengths": [], "summary": result[:500]}
        
        return parsed_result, usage

    # ------------------------------------------------------------------
    # Pass 2: Visual PDF QA (PyMuPDF + VLM)
    # ------------------------------------------------------------------

    def _render_pdf_pages(self, pdf_path: str, max_pages: int = 30) -> list[bytes]:
        """Render each PDF page to a PNG image using PyMuPDF."""
        try:
            import pymupdf
        except ImportError:
            return []

        images: list[bytes] = []
        try:
            doc = pymupdf.open(pdf_path)
            for i, page in enumerate(doc):
                if i >= max_pages:
                    break
                # Render at 2x resolution for clarity
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
                images.append(pix.tobytes("png"))
            doc.close()
        except Exception:
            pass

        return images

    def _run_visual_qa(self, page_images: list[bytes]) -> dict:
        """Send rendered slide images to a VLM for visual inspection."""
        if not page_images:
            return {"visual_issues": [], "visual_summary": "No PDF pages to inspect."}, {}

        try:
            from google.genai import types
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                return {
                    "visual_issues": [],
                    "visual_summary": "Skipped: GEMINI_API_KEY not set.",
                }, {}

            client = genai.Client(api_key=api_key)

            # Build multimodal content: prompt + all slide images
            parts: list[types.PartUnion] = [
                types.Part.from_text(
                    """You are a presentation QA reviewer. I am showing you every slide of a Beamer PDF presentation rendered as images.

For EACH slide, check:
1. Text overflow — is any text cut off at the edges or overlapping other elements?
2. Image overflow — does any figure extend beyond the slide boundary?
3. Overlapping elements — do any text blocks, images, or bullet points overlap each other?
4. Readability — is any text too small to read, or is the slide too cluttered?
5. Missing content — are there blank slides, placeholder text, or broken image references?
6. Layout — is the slide visually balanced and professional?

Respond with ONLY a valid JSON object (no markdown):
{
  "visual_issues": [
    {"slide_number": 1, "issue": "description of the problem", "severity": "low|critical"}
  ],
  "visual_summary": "one-paragraph overall visual quality assessment"
}

If all slides look fine, return an empty visual_issues array."""
                ),
            ]

            for i, img_bytes in enumerate(page_images):
                parts.append(
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=types.Content(role="user", parts=parts),
            )

            vlm_usage = {
                "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
                "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            }

            response_text = response.text or ""
            # Strip markdown fences
            response_text = re.sub(r"^```(?:json)?\s*\n?", "", response_text.strip())
            response_text = re.sub(r"\n?```\s*$", "", response_text.strip())

            return json.loads(response_text), vlm_usage

        except ImportError:
            return {"visual_issues": [], "visual_summary": "Skipped: google-genai not installed."}, {}
        except Exception as e:
            return {"visual_issues": [], "visual_summary": f"Visual QA error: {e}"}, {}

    # ------------------------------------------------------------------
    # Main execute
    # ------------------------------------------------------------------

    async def execute(self, manager: ProjectManager, state: dict) -> dict[str, Any]:
        # --- Compile ---
        compilation = self._compile_and_check(manager)

        # --- Read artifacts ---
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

        # Build compilation report
        compilation_report = "COMPILATION RESULT:\n"
        if compilation["success"]:
            compilation_report += "- PDF compiled successfully.\n"
        else:
            compilation_report += "- PDF compilation FAILED.\n"
        if compilation["errors"]:
            compilation_report += "- Errors:\n" + "\n".join(f"  {e}" for e in compilation["errors"]) + "\n"
        if compilation["warnings"]:
            compilation_report += "- Warnings:\n" + "\n".join(f"  {w}" for w in compilation["warnings"]) + "\n"
        if compilation["overfull_boxes"]:
            compilation_report += "- Overfull/Underfull boxes:\n" + "\n".join(f"  {o}" for o in compilation["overfull_boxes"]) + "\n"

        # --- Pass 1: LaTeX code QA ---
        latex_qa, latex_usage = self._run_latex_qa(
            latex_content, brief_block, strategy_block, analysis_block, compilation_report
        )

        # --- Pass 2: Visual PDF QA ---
        visual_qa = {"visual_issues": [], "visual_summary": "Skipped: compilation failed."}
        visual_usage = {}
        if compilation["success"] and compilation["pdf_path"]:
            page_images = self._render_pdf_pages(compilation["pdf_path"])
            visual_qa, visual_usage = self._run_visual_qa(page_images)

        # --- Merge results ---
        all_issues = latex_qa.get("issues", [])

        # Fold visual issues into the main issues list
        for vi in visual_qa.get("visual_issues", []):
            all_issues.append({
                "severity": vi.get("severity", "low"),
                "slide": f"Slide {vi.get('slide_number', '?')}",
                "issue": f"[Visual] {vi.get('issue', '')}",
                "suggestion": "",
            })

        has_critical = any(i.get("severity") == "critical" for i in all_issues)
        compilation_failed = not compilation["success"] and bool(compilation["errors"])

        review = {
            "status": "needs_revision" if (has_critical or compilation_failed) else "approved",
            "overall_score": max(1, 10 - len([i for i in all_issues if i.get("severity") == "critical"]) * 2 - len(all_issues)),
            "issues": all_issues,
            "strengths": latex_qa.get("strengths", []),
            "summary": latex_qa.get("summary", ""),
            "visual_summary": visual_qa.get("visual_summary", ""),
            "compilation": {
                "success": compilation["success"],
                "errors": compilation["errors"],
                "warnings": compilation["warnings"],
                "overfull_boxes": compilation["overfull_boxes"],
            },
        }

        manager.save_artifact(
            "qa_review.json",
            json.dumps(review, indent=2).encode(),
        )

        return {
            "review": review, 
            "usage": {
                "latex_qa": latex_usage,
                "visual_qa": visual_usage
            }
        }
