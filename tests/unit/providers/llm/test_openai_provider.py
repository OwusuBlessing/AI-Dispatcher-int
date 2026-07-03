"""Unit tests for OpenAI LLM provider."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from src.providers.llm.base import LLMConfig
from src.providers.llm.openai_provider import OpenAIProvider


class CityAnswer(BaseModel):
    city: str


@patch("langchain_openai.ChatOpenAI")
def test_build_model_passes_config_to_chat_openai(mock_chat_openai):
    mock_chat_openai.return_value = MagicMock()

    OpenAIProvider(
        LLMConfig(
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=128,
            api_key="sk-test",
        )
    )

    mock_chat_openai.assert_called_once_with(
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=128,
        max_retries=2,
        api_key="sk-test",
    )


@patch("langchain_openai.ChatOpenAI")
def test_complete_returns_text(mock_chat_openai):
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Bonjour")
    mock_chat_openai.return_value = mock_model

    provider = OpenAIProvider(LLMConfig(model="gpt-4o-mini"))
    result = provider.complete(messages=[("human", "Translate to French")])

    assert result == "Bonjour"


@patch("langchain_openai.ChatOpenAI")
def test_complete_structured_returns_schema(mock_chat_openai):
    mock_model = MagicMock()
    structured_model = MagicMock()
    structured_model.invoke.return_value = CityAnswer(city="Dallas")
    mock_model.with_structured_output.return_value = structured_model
    mock_chat_openai.return_value = mock_model

    provider = OpenAIProvider(LLMConfig(model="gpt-4o-mini"))
    result = provider.complete_structured(
        CityAnswer,
        prompt="Where is the driver?",
    )

    assert result.city == "Dallas"
    mock_model.with_structured_output.assert_called_once_with(
        CityAnswer,
        method="function_calling",
    )


def test_build_model_raises_when_dependency_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def import_mock(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "langchain_openai":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_mock)

    with pytest.raises(ImportError, match="langchain-openai is required"):
        OpenAIProvider(LLMConfig(model="gpt-4o-mini"))
