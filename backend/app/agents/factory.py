import json
import os
from pathlib import Path

from crewai import LLM

from app.agents.base import BaseAgent
from app.agents.strategist import StrategistAgent
from app.agents.data_analyst import DataAnalystAgent
from app.agents.plot_generator import PlotGeneratorAgent
from app.agents.latex_author import LatexAuthorAgent
from app.agents.qa_reviewer import QAReviewerAgent
from app.agents.presenter import PresenterAgent

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "agent_models.json"

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "strategist": StrategistAgent,
    "data_analyst": DataAnalystAgent,
    "plot_generator": PlotGeneratorAgent,
    "latex_author": LatexAuthorAgent,
    "qa_reviewer": QAReviewerAgent,
    "presenter": PresenterAgent,
}


class AgentFactory:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
        return {"default": {"model": "claude-sonnet-4-20250514"}, "agents": {}}

    def _build_llm(self, agent_name: str) -> LLM:
        """Build a CrewAI LLM from config, merging agent overrides onto defaults."""
        defaults = self.config.get("default", {})
        overrides = self.config.get("agents", {}).get(agent_name, {})
        merged = {**defaults, **{k: v for k, v in overrides.items() if v}}

        model = merged.get("model", "claude-sonnet-4-20250514")

        kwargs: dict = {"model": model}
        if "provider" in merged:
            kwargs["provider"] = merged["provider"]
        if "base_url" in merged:
            kwargs["base_url"] = merged["base_url"]
        if "api_key_env" in merged:
            kwargs["api_key"] = os.environ.get(merged["api_key_env"], "")

        return LLM(**kwargs)

    def create(self, agent_name: str) -> BaseAgent:
        cls = AGENT_REGISTRY.get(agent_name)
        if cls is None:
            raise ValueError(f"Unknown agent: {agent_name}")
        llm = self._build_llm(agent_name)
        return cls(name=agent_name, llm=llm)
