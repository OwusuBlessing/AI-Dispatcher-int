"""Central LLM settings for each agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from configs.settings import Settings, get_settings
from src.domain.enums import LLMProvider
from src.providers.llm.base import BaseLLMProvider
from src.providers.llm.factory import create_llm_provider

AgentName = Literal[
    "conversation_organizer",
    "profile_extractor",
    "equipment_matcher",
    "readme_generator",
]

# Shared model picks for this project — change here only.
ANTHROPIC_SONNET = "claude-sonnet-4-6"


@dataclass(frozen=True)
class AgentLLMConfig:
    """Provider/model settings for one agent."""

    provider: LLMProvider
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    max_retries: int = 2


# All agents use explicit provider/model — no .env LLM_PROVIDER fallback.
AGENT_LLM_CONFIGS: dict[AgentName, AgentLLMConfig] = {
    "conversation_organizer": AgentLLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model=ANTHROPIC_SONNET,
        temperature=0.0,
        max_tokens=4096,
    ),
    "profile_extractor": AgentLLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model=ANTHROPIC_SONNET,
        temperature=0.0,
        max_tokens=4096,
    ),
    "equipment_matcher": AgentLLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model=ANTHROPIC_SONNET,
        temperature=0.0,
        max_tokens=2048,
    ),
    "readme_generator": AgentLLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model=ANTHROPIC_SONNET,
        temperature=0.2,
        max_tokens=1024,
    ),
}


def get_agent_llm_config(agent_name: AgentName) -> AgentLLMConfig:
    """Return the configured LLM settings for an agent."""
    if agent_name not in AGENT_LLM_CONFIGS:
        supported = ", ".join(AGENT_LLM_CONFIGS)
        raise KeyError(f"Unknown agent '{agent_name}'. Supported: {supported}")
    return AGENT_LLM_CONFIGS[agent_name]


def create_agent_llm(
    agent_name: AgentName,
    *,
    settings: Settings | None = None,
) -> BaseLLMProvider:
    """Create an LLM provider using the central per-agent configuration."""
    cfg = get_agent_llm_config(agent_name)
    return create_llm_provider(
        provider=cfg.provider,
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        max_retries=cfg.max_retries,
        settings=settings or get_settings(),
    )
