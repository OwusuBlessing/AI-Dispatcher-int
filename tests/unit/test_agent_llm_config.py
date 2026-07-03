"""Central agent LLM config unit tests."""

from unittest.mock import patch

from configs.agent_llm_config import (
    AGENT_LLM_CONFIGS,
    create_agent_llm,
    get_agent_llm_config,
)
from src.domain.enums import LLMProvider


def test_get_agent_llm_config_returns_profile_extractor_settings():
    cfg = get_agent_llm_config("profile_extractor")

    assert cfg.provider == LLMProvider.ANTHROPIC
    assert cfg.model == "claude-sonnet-4-6"
    assert cfg.temperature == 0.0


def test_get_agent_llm_config_returns_explicit_organizer_settings():
    cfg = get_agent_llm_config("conversation_organizer")

    assert cfg.provider == LLMProvider.ANTHROPIC
    assert cfg.model == "claude-sonnet-4-6"


def test_all_agent_configs_have_explicit_provider_and_model():
    for agent_name, cfg in AGENT_LLM_CONFIGS.items():
        assert isinstance(cfg.provider, LLMProvider), agent_name
        assert cfg.model, agent_name


def test_all_agents_have_config_entries():
    assert set(AGENT_LLM_CONFIGS) == {
        "conversation_organizer",
        "profile_extractor",
        "equipment_matcher",
        "readme_generator",
    }


@patch("configs.agent_llm_config.create_llm_provider")
def test_create_agent_llm_uses_central_settings(mock_create):
    create_agent_llm("conversation_organizer")

    mock_create.assert_called_once()
    kwargs = mock_create.call_args.kwargs
    assert kwargs["provider"] == LLMProvider.ANTHROPIC
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["temperature"] == 0.0
    assert kwargs["max_tokens"] == 4096
