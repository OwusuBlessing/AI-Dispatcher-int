"""Unit tests for Anthropic LLM provider."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from src.providers.llm.anthropic_provider import AnthropicProvider
from src.providers.llm.base import LLMConfig


class RateAnswer(BaseModel):
    minimum_rate_per_mile: float


@patch("langchain_anthropic.ChatAnthropic")
def test_build_model_passes_config_to_chat_anthropic(mock_chat_anthropic):
    mock_chat_anthropic.return_value = MagicMock()

    AnthropicProvider(
        LLMConfig(
            model="claude-haiku-4-5-20251001",
            temperature=0.0,
            max_tokens=512,
            api_key="anthropic-test",
        )
    )

    mock_chat_anthropic.assert_called_once_with(
        model="claude-haiku-4-5-20251001",
        temperature=0.0,
        max_tokens=512,
        max_retries=2,
        api_key="anthropic-test",
    )


@patch("langchain_anthropic.ChatAnthropic")
def test_complete_returns_text(mock_chat_anthropic):
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Structured evidence ready.")
    mock_chat_anthropic.return_value = mock_model

    provider = AnthropicProvider(LLMConfig(model="claude-haiku-4-5-20251001"))
    result = provider.complete(messages=[("human", "Organize this conversation")])

    assert result == "Structured evidence ready."


@patch("langchain_anthropic.ChatAnthropic")
def test_complete_structured_returns_schema(mock_chat_anthropic):
    mock_model = MagicMock()
    structured_model = MagicMock()
    structured_model.invoke.return_value = RateAnswer(minimum_rate_per_mile=2.0)
    mock_model.with_structured_output.return_value = structured_model
    mock_chat_anthropic.return_value = mock_model

    provider = AnthropicProvider(LLMConfig(model="claude-haiku-4-5-20251001"))
    result = provider.complete_structured(
        RateAnswer,
        prompt="Extract minimum rate",
    )

    assert result.minimum_rate_per_mile == 2.0


def test_build_model_raises_when_dependency_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def import_mock(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "langchain_anthropic":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_mock)

    with pytest.raises(ImportError, match="langchain-anthropic is required"):
        AnthropicProvider(LLMConfig(model="claude-haiku-4-5-20251001"))
