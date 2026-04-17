import os

from crewai import LLM

from app.agents.base import BaseAgent
from app.agents.strategist import StrategistAgent
from app.agents.data_analyst import DataAnalystAgent
from app.agents.plot_generator import PlotGeneratorAgent
from app.agents.latex_author import LatexAuthorAgent
from app.agents.qa_reviewer import QAReviewerAgent
from app.agents.presenter import PresenterAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "strategist": StrategistAgent,
    "data_analyst": DataAnalystAgent,
    "plot_generator": PlotGeneratorAgent,
    "latex_author": LatexAuthorAgent,
    "qa_reviewer": QAReviewerAgent,
    "presenter": PresenterAgent,
}


def resolve_model(name: str) -> str:
    """Resolve the model for a component from its env var.

    Each component has its own env var: ORCHESTRATOR_MODEL, STRATEGIST_MODEL, etc.
    API keys are picked up automatically by LiteLLM based on the provider
    prefix: gemini/ → GEMINI_API_KEY, anthropic/ → ANTHROPIC_API_KEY,
    openai/ → OPENAI_API_KEY, etc.
    """
    env_key = f"{name.upper()}_MODEL"
    model = os.environ.get(env_key)
    if not model:
        raise ValueError(
            f"Missing env var {env_key}. "
            f"Set it to a LiteLLM model string (e.g. gemini/gemini-2.5-flash, anthropic/claude-sonnet-4-20250514)."
        )
    return model


class AgentFactory:
    def _build_llm(self, agent_name: str) -> LLM:
        # is_litellm=True forces CrewAI to route through LiteLLM rather than
        # native provider SDKs — our usage/cost callback only fires on that path.
        return LLM(model=resolve_model(agent_name), is_litellm=True)

    def create(self, agent_name: str) -> BaseAgent:
        cls = AGENT_REGISTRY.get(agent_name)
        if cls is None:
            raise ValueError(f"Unknown agent: {agent_name}")
        llm = self._build_llm(agent_name)
        return cls(name=agent_name, llm=llm)
