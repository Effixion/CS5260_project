import asyncio
import json
from typing import AsyncGenerator

from crewai import LLM

from app.storage import ProjectManager
from app.agents import AgentFactory
from app.models import Message

STAGE_A_AGENTS = ["strategist", "data_analyst", "plot_generator"]
STAGE_B_AGENTS = ["latex_author", "qa_reviewer", "presenter"]

ORCHESTRATOR_SYSTEM_PROMPT = """You are the orchestrator for Haitham, an AI-powered academic presentation generator.

You are having a conversation with a user who wants to create a presentation. Based on the conversation history and current project state, decide what action to take next.

Current project state:
- Project name: {project_name}
- Uploaded files: {uploaded_files}
- Generated artifacts: {artifacts}
- Project status: {project_status}

You MUST respond with a JSON object in one of these formats (and nothing else):

1. To reply conversationally:
{{"action": "respond", "message": "your reply here"}}

2. To run data analysis and generate visualizations (use when files are uploaded and user wants analysis):
{{"action": "run_analysis", "message": "brief intro message before analysis starts", "brief": {{...}}}}

3. To generate the presentation (use ONLY after visualizations have been selected):
{{"action": "run_presentation", "message": "brief intro message before generation starts", "brief": {{...}}}}

THE "brief" OBJECT IS CRITICAL. Every time you trigger run_analysis or run_presentation, you MUST include a "brief" object that tells the sub-agents exactly what to produce. Infer as much as you can from the conversation — what the user said, their tone, the type of data, the audience. Fill in sensible defaults for anything the user hasn't specified.

"brief" schema:
{{
  "presentation_type": "academic" | "business" | "pitch" | "lecture" | "report",
  "audience": "who the presentation is for",
  "tone": "formal" | "casual" | "technical" | "persuasive",
  "num_slides": <integer — total slides including title and conclusion>,
  "num_visualizations": <integer — how many candidate plots to generate>,
  "focus_areas": ["specific topics or angles the user wants emphasized"],
  "additional_instructions": "any other user preferences or constraints verbatim"
}}

Guidelines:
- If the user just started and has no files, welcome them and ask what they'd like to present about. Encourage them to upload data files.
- If files are uploaded but not yet analyzed, suggest running the analysis or ask if they want to upload more files.
- If the user references files with @filename, acknowledge those specific files.
- If the user asks to analyze/create/generate and there are uploaded files, use run_analysis.
- If the user asks for changes after a presentation is complete, determine if they need a new analysis or just a presentation re-generation.
- Be helpful, concise, and natural in your messages.
- Before triggering run_analysis, try to gather enough context from the user to fill the brief well. If the user is vague, ask 1-2 quick clarifying questions first (via "respond") rather than guessing blindly.
- If the user says "short" → ~5-8 slides, 2-3 visualizations. "Detailed" → 12-20 slides, 5-8 visualizations. Default → ~8-12 slides, 3-5 visualizations.

IMPORTANT: Respond ONLY with a valid JSON object. No markdown, no code fences, no extra text."""


def _build_orchestrator_llm() -> LLM:
    """Build the orchestrator LLM using the same config as agents."""
    factory = AgentFactory()
    config = factory.config
    orch_config = config.get("orchestrator", config.get("default", {}))
    model = orch_config.get("model", "anthropic/claude-sonnet-4-20250514")

    kwargs = {"model": model}
    if "provider" in orch_config:
        kwargs["provider"] = orch_config["provider"]
    if "base_url" in orch_config:
        kwargs["base_url"] = orch_config["base_url"]

    return LLM(**kwargs)


def _format_messages_for_llm(messages: list[dict]) -> str:
    """Convert our message history to a text conversation for the LLM."""
    lines = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        content_type = msg.get("content_type", "text")

        if content_type == "visualization_picker":
            artifacts = msg.get("artifacts", [])
            plot_names = [a.get("filename", "") for a in artifacts]
            content = f"[System generated {len(plot_names)} candidate visualizations: {', '.join(plot_names)}]"
        elif content_type == "artifact":
            artifacts = msg.get("artifacts", [])
            fnames = [a.get("filename", "") for a in artifacts]
            content = f"[System generated artifacts: {', '.join(fnames)}]"
        elif content_type == "status":
            continue

        if content.strip():
            label = "User" if role == "user" else "Assistant"
            lines.append(f"{label}: {content}")

    return "\n".join(lines)


def _load_artifact_json(manager: ProjectManager, filename: str) -> dict:
    """Load a JSON artifact, returning {} if missing or invalid."""
    path = manager.get_artifact_path(filename)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _parse_llm_response(text: str) -> dict:
    """Parse the LLM's JSON response, handling common formatting issues."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: treat entire response as a conversational reply
        return {"action": "respond", "message": text}


async def _run_agents(
    manager: ProjectManager,
    state: dict,
    agent_names: list[str],
    factory: AgentFactory,
) -> AsyncGenerator[dict, None]:
    """Run a sequence of agents, yielding SSE events and tracking token usage."""
    
    project = manager.load_project()
    if not project.get("token_usage"):
        project["token_usage"] = {}
    
    for agent_name in agent_names:
        yield {
            "event": "agent_status",
            "data": json.dumps({"agent": agent_name, "status": "running"}),
        }

        try:
            agent = factory.create(agent_name)
            result = await agent.execute(manager, state)

            for artifact in result.get("artifacts", []):
                yield {
                    "event": "artifact",
                    "data": json.dumps(artifact),
                }

            usage = result.get("usage", {})
            if usage:
                if agent_name not in project["token_usage"]:
                    project["token_usage"][agent_name] = []
                    
                project["token_usage"][agent_name].append(usage)

                manager.save_project(project)

            yield {
                "event": "agent_status",
                "data": json.dumps({"agent": agent_name, "status": "completed", "usage": usage}),
            }

        except Exception as e:
            yield {
                "event": "agent_status",
                "data": json.dumps({"agent": agent_name, "status": "error"}),
            }
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Agent {agent_name} failed: {str(e)}"}),
            }
            return

        await asyncio.sleep(0.3)


async def handle_message(
    manager: ProjectManager,
    user_message: dict,
    messages: list[dict],
) -> AsyncGenerator[dict, None]:
    """
    Process a user message through the LLM-routed orchestrator.
    Yields SSE events for the frontend.
    """
    project = manager.load_project()
    files = manager.list_files()
    artifacts = manager.list_artifacts()

    # Build state dict for agents
    state = {
        **project,
        "uploaded_files": [f["filename"] for f in files],
        "file_contexts": {f["filename"]: f.get("note", "") for f in files if f.get("note")},
    }

    # Format system prompt
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
        project_name=project.get("name", "Untitled"),
        uploaded_files=json.dumps([f["filename"] for f in files]) if files else "None",
        artifacts=json.dumps([a["filename"] for a in artifacts]) if artifacts else "None",
        project_status=project.get("status", "active"),
    )

    # Format conversation
    conversation = _format_messages_for_llm(messages)

    # Build the prompt for the LLM
    full_prompt = f"{system_prompt}\n\nConversation so far:\n{conversation}\n\nRespond with a JSON action:"

    # Call the LLM via CrewAI's LLM class
    llm = _build_orchestrator_llm()

    try:
        response_text = llm.call(messages=[{"role": "user", "content": full_prompt}])
    except Exception as e:
        fallback_msg = Message(
            role="assistant",
            content=f"I'm having trouble right now. Please try again. (Error: {str(e)[:100]})",
            content_type="text",
        ).model_dump()
        manager.append_message(fallback_msg)
        yield {"event": "message", "data": json.dumps(fallback_msg)}
        yield {"event": "done", "data": json.dumps({"project_status": project.get("status", "active")})}
        return

    # Parse the LLM's decision
    decision = _parse_llm_response(response_text)
    action = decision.get("action", "respond")
    msg_text = decision.get("message", "")

    factory = AgentFactory()

    if action == "respond":
        msg = Message(
            role="assistant",
            content=msg_text,
            content_type="text",
        ).model_dump()
        manager.append_message(msg)
        yield {"event": "message", "data": json.dumps(msg)}
        yield {"event": "done", "data": json.dumps({"project_status": project.get("status", "active")})}

    elif action == "run_analysis":
        # Merge the orchestrator's brief into state so all agents can read it
        brief = decision.get("brief", {})
        state["brief"] = brief

        # Persist the brief as an artifact so Stage B agents can access it too
        manager.save_artifact("brief.json", json.dumps(brief, indent=2).encode())

        # Send intro message
        intro = Message(
            role="assistant",
            content=msg_text or "Analyzing your data...",
            content_type="status",
        ).model_dump()
        manager.append_message(intro)
        yield {"event": "message", "data": json.dumps(intro)}

        # Run Stage A agents
        async for event in _run_agents(manager, state, STAGE_A_AGENTS, factory):
            yield event

        # Summary + visualization picker
        summary_msg = Message(
            role="assistant",
            content="I've analyzed your data and generated candidate visualizations. Please select the ones you'd like to include in your presentation:",
            content_type="text",
        ).model_dump()
        manager.append_message(summary_msg)
        yield {"event": "message", "data": json.dumps(summary_msg)}

        # Collect generated plot artifacts
        plot_artifacts = []
        for a in manager.list_artifacts():
            if a["filename"].startswith("candidate_plot_"):
                plot_artifacts.append({
                    "type": "candidate_plot",
                    "url": f"/projects/{project['id']}/artifacts/{a['filename']}",
                    "filename": a["filename"],
                })

        viz_msg = Message(
            role="assistant",
            content="",
            content_type="visualization_picker",
            artifacts=plot_artifacts,
        ).model_dump()
        manager.append_message(viz_msg)
        yield {"event": "message", "data": json.dumps(viz_msg)}

        yield {"event": "done", "data": json.dumps({"project_status": "active"})}

    elif action == "run_presentation":
        # Merge brief into state (may come from this decision or from the saved artifact)
        brief = decision.get("brief", {})
        if not brief:
            brief = _load_artifact_json(manager, "brief.json")
        state["brief"] = brief

        intro = Message(
            role="assistant",
            content=msg_text or "Generating your presentation...",
            content_type="status",
        ).model_dump()
        manager.append_message(intro)
        yield {"event": "message", "data": json.dumps(intro)}

        async for event in _run_agents(manager, state, STAGE_B_AGENTS, factory):
            yield event

        artifact_list = _collect_presentation_artifacts(manager, project["id"])

        done_msg = Message(
            role="assistant",
            content="Your presentation is ready! You can preview it below or download the files.",
            content_type="artifact",
            artifacts=artifact_list,
        ).model_dump()
        manager.append_message(done_msg)
        yield {"event": "message", "data": json.dumps(done_msg)}

        project["status"] = "completed"
        manager.save_project(project)

        yield {"event": "done", "data": json.dumps({"project_status": "completed"})}

    else:
        # Unknown action — treat as respond
        msg = Message(
            role="assistant",
            content=msg_text or "I'm not sure what to do. Could you clarify?",
            content_type="text",
        ).model_dump()
        manager.append_message(msg)
        yield {"event": "message", "data": json.dumps(msg)}
        yield {"event": "done", "data": json.dumps({"project_status": project.get("status", "active")})}


def _collect_presentation_artifacts(manager: ProjectManager, project_id: str) -> list[dict]:
    """Collect presentation-related artifacts for the completion message."""
    artifact_list = []
    for a in manager.list_artifacts():
        if a["filename"] in ("presentation.tex", "presenter_script.txt") or a["filename"].endswith(".pdf"):
            artifact_list.append({
                "type": a["filename"].split(".")[-1],
                "url": f"/projects/{project_id}/artifacts/{a['filename']}",
                "filename": a["filename"],
            })
    return artifact_list


async def handle_visualization_selection(
    manager: ProjectManager,
    message_id: str,
    selected: list[str],
) -> AsyncGenerator[dict, None]:
    """Handle when the user selects visualizations from the picker."""
    manager.update_message(message_id, {
        "metadata": {"selected": selected, "confirmed": True},
    })

    user_msg = Message(
        role="user",
        content=f"I've selected these visualizations: {', '.join(selected)}",
        content_type="text",
    ).model_dump()
    manager.append_message(user_msg)
    yield {"event": "message", "data": json.dumps(user_msg)}

    project = manager.load_project()
    brief = _load_artifact_json(manager, "brief.json")
    state = {
        **project,
        "selected_visualizations": selected,
        "uploaded_files": [f["filename"] for f in manager.list_files()],
        "brief": brief,
    }

    intro = Message(
        role="assistant",
        content="Great choices! Generating your presentation now...",
        content_type="status",
    ).model_dump()
    manager.append_message(intro)
    yield {"event": "message", "data": json.dumps(intro)}

    factory = AgentFactory()
    async for event in _run_agents(manager, state, STAGE_B_AGENTS, factory):
        yield event

    artifact_list = _collect_presentation_artifacts(manager, project["id"])

    done_msg = Message(
        role="assistant",
        content="Your presentation is ready! You can preview it below or download the files.",
        content_type="artifact",
        artifacts=artifact_list,
    ).model_dump()
    manager.append_message(done_msg)
    yield {"event": "message", "data": json.dumps(done_msg)}

    project["status"] = "completed"
    manager.save_project(project)

    yield {"event": "done", "data": json.dumps({"project_status": "completed"})}
