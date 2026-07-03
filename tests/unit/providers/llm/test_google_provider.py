"""Unit tests for Google GenAI LLM provider."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from src.providers.llm.base import LLMConfig
from src.providers.llm.google_provider import GoogleProvider


class LocationAnswer(BaseModel):
    city: str
    state: str


@patch("langchain_google_genai.ChatGoogleGenerativeAI")
def test_build_model_passes_config_to_chat_google(mock_chat_google):
    mock_chat_google.return_value = MagicMock()

    GoogleProvider(
        LLMConfig(
            model="gemini-2.0-flash",
            temperature=0.3,
            max_tokens=300,
            api_key="google-test",
        )
    )

    mock_chat_google.assert_called_once_with(
        model="gemini-2.0-flash",
        temperature=0.3,
        max_tokens=300,
        max_retries=2,
        api_key="google-test",
    )


@patch("langchain_google_genai.ChatGoogleGenerativeAI")
def test_complete_returns_text(mock_chat_google):
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Dallas, Texas")
    mock_chat_google.return_value = mock_model

    provider = GoogleProvider(LLMConfig(model="gemini-2.0-flash"))
    result = provider.complete(messages=[("human", "Where is the driver?")])

    assert result == "Dallas, Texas"


@patch("langchain_google_genai.ChatGoogleGenerativeAI")
def test_complete_structured_returns_schema(mock_chat_google):
    mock_model = MagicMock()
    structured_model = MagicMock()
    structured_model.invoke.return_value = LocationAnswer(city="Dallas", state="Texas")
    mock_model.with_structured_output.return_value = structured_model
    mock_chat_google.return_value = mock_model

    provider = GoogleProvider(LLMConfig(model="gemini-2.0-flash"))
    result = provider.complete_structured(
        LocationAnswer,
        prompt="Extract location",
    )

    assert result.city == "Dallas"
    assert result.state == "Texas"


def test_build_model_raises_when_dependency_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def import_mock(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "langchain_google_genai":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_mock)

    with pytest.raises(ImportError, match="langchain-google-genai is required"):
        GoogleProvider(LLMConfig(model="gemini-2.0-flash"))
