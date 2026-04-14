import json
import os
import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from crewai import LLM, Agent as CrewAgent, Task, Crew

from app.storage import ProjectIndex
from app.agents import AgentFactory

router = APIRouter(prefix="/projects/{project_id}", tags=["editor"])

STORAGE_PATH = Path(os.environ.get("PROJECT_STORAGE_PATH", "./projects"))
index = ProjectIndex(STORAGE_PATH)


def _get_manager(project_id: str):
    try:
        return index.get_manager(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")


# --- Request models ---


class CompileRequest(BaseModel):
    tex_content: str | None = None


class EditRequest(BaseModel):
    instruction: str
    current_tex: str
    file_refs: list[str] | None = None


class SaveTexRequest(BaseModel):
    content: str


# --- Endpoints ---


@router.post("/compile")
async def compile_tex(project_id: str, req: CompileRequest):
    """Compile presentation.tex to PDF and return results."""
    manager = _get_manager(project_id)
    artifacts_dir = manager.artifacts_dir

    # If tex content is provided, save it first
    if req.tex_content is not None:
        manager.save_artifact("presentation.tex", req.tex_content.encode())

    tex_path = artifacts_dir / "presentation.tex"
    pdf_path = artifacts_dir / "presentation.pdf"

    if not tex_path.exists():
        raise HTTPException(status_code=404, detail="presentation.tex not found")

    result = {
        "success": False,
        "errors": [],
        "warnings": [],
        "overfull_boxes": [],
        "pdf_url": None,
    }

    # Remove any stale PDF so success never reflects a prior run
    if pdf_path.exists():
        pdf_path.unlink()

    try:
        log_text = ""
        returncode = 0
        for _ in range(2):
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "presentation.tex"],
                cwd=str(artifacts_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            log_text += (proc.stdout or "") + "\n"
            returncode = proc.returncode
            if proc.returncode != 0:
                break

        lines = log_text.split("\n")
        for i, raw in enumerate(lines):
            line = raw.rstrip()
            stripped = line.strip()
            if stripped.startswith("!"):
                context = stripped
                for j in range(i + 1, min(i + 4, len(lines))):
                    nxt = lines[j].strip()
                    if nxt.startswith("l."):
                        context += f" ({nxt})"
                        break
                result["errors"].append(context)
            elif stripped.startswith("Emergency stop") or stripped.startswith("Fatal error"):
                result["errors"].append(stripped)
            elif "LaTeX Warning:" in stripped:
                result["warnings"].append(stripped)
            elif re.match(r"(Over|Under)full \\[hv]box", stripped):
                result["overfull_boxes"].append(stripped)

        if returncode == 0 and pdf_path.exists():
            result["success"] = True
            result["pdf_url"] = f"/projects/{project_id}/artifacts/presentation.pdf"
        elif not result["errors"]:
            tail = "\n".join(lines[-20:]).strip()
            result["errors"].append(
                f"pdflatex failed (exit {returncode}). Log tail:\n{tail}"
            )

    except FileNotFoundError:
        result["errors"].append("pdflatex not installed on this system")
    except subprocess.TimeoutExpired:
        result["errors"].append("pdflatex compilation timed out")

    return result


@router.post("/edit")
async def edit_tex(project_id: str, req: EditRequest):
    """Send an instruction to edit the LaTeX via LLM. Returns SSE stream."""
    manager = _get_manager(project_id)

    # Read additional file context if referenced
    file_context = ""
    if req.file_refs:
        for ref in req.file_refs:
            file_path = manager.get_file_path(ref)
            if file_path.exists():
                try:
                    content = file_path.read_text(errors="ignore")[:5000]
                    file_context += f"\n--- File: {ref} ---\n{content}\n"
                except Exception:
                    pass

    async def stream():
        try:
            # Save the current version before editing
            manager.push_tex_version(req.current_tex, source="pre_edit", instruction=req.instruction)

            # Build the LLM for editing (reuse latex_author config)
            factory = AgentFactory()
            llm = factory._build_llm("latex_author")

            agent = CrewAgent(
                role="LaTeX Editor",
                goal="Edit a LaTeX Beamer presentation according to user instructions.",
                backstory=(
                    "You are an expert LaTeX editor. You modify existing Beamer presentations "
                    "based on user instructions. You preserve the overall structure and only change "
                    "what the user asks for. You always produce valid, compilable LaTeX."
                ),
                llm=llm,
                verbose=False,
            )

            prompt = f"""Edit this LaTeX Beamer presentation according to the instruction below.

CURRENT LATEX SOURCE:
{req.current_tex}
{f"REFERENCED FILES:{file_context}" if file_context else ""}

USER INSTRUCTION:
{req.instruction}

Requirements:
- Apply ONLY the changes the user asked for
- Keep all other content, structure, and formatting intact
- Ensure the result is valid, compilable LaTeX
- Properly escape special characters (%, &, $, #, _)
- Maintain slide-fit constraints (max 5-6 bullets per slide, ~12 words each)

Respond with ONLY the complete updated LaTeX source code. No markdown fences, no explanation."""

            task = Task(
                description=prompt,
                expected_output="Complete updated LaTeX source code.",
                agent=agent,
            )

            crew = Crew(agents=[agent], tasks=[task], verbose=False)
            crew_result = crew.kickoff()
            updated_tex = str(crew_result).strip()

            # Clean up markdown fences
            if updated_tex.startswith("```"):
                lines = updated_tex.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                updated_tex = "\n".join(lines).strip()

            # Save the edited version
            version = manager.push_tex_version(updated_tex, source="ai_edit", instruction=req.instruction)

            yield {
                "event": "updated_tex",
                "data": json.dumps({"tex_content": updated_tex, "version": version}),
            }
            yield {"event": "done", "data": json.dumps({"success": True})}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(stream())


@router.put("/tex")
async def save_tex(project_id: str, req: SaveTexRequest):
    """Save manual edits to presentation.tex."""
    manager = _get_manager(project_id)
    version = manager.push_tex_version(req.content, source="manual_edit")
    return {"success": True, "version": version}


@router.post("/undo")
async def undo_tex(project_id: str):
    """Undo the last tex edit, restoring the previous version."""
    manager = _get_manager(project_id)
    content = manager.undo_tex()
    if content is None:
        raise HTTPException(status_code=400, detail="No more versions to undo")
    return {
        "tex_content": content,
        "remaining_undos": manager.get_undo_count(),
    }


@router.get("/tex")
async def get_tex(project_id: str):
    """Get the current presentation.tex content."""
    manager = _get_manager(project_id)
    content = manager.get_tex_content()
    if content is None:
        raise HTTPException(status_code=404, detail="No presentation.tex found")
    return {
        "tex_content": content,
        "undo_count": manager.get_undo_count(),
    }
