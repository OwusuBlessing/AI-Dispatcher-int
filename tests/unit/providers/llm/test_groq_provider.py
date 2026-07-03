"""Unit tests for Groq LLM provider."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from src.providers.llm.base import LLMConfig
from src.providers.llm.groq_provider import GroqProvider


class EquipmentAnswer(BaseModel):
    equipment: str


@patch("langchain_groq.ChatGroq")
def test_build_model_passes_config_to_chat_groq(mock_chat_groq):
    mock_chat_groq.return_value = MagicMock()

    GroqProvider(
        LLMConfig(
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            max_tokens=256,
            api_key="groq-test",
            extra={"reasoning_format": "parsed"},
        )
    )

    mock_chat_groq.assert_called_once_with(
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        max_tokens=256,
        max_retries=2,
        api_key="groq-test",
        reasoning_format="parsed",
    )


@patch("langchain_groq.ChatGroq")
def test_complete_returns_text(mock_chat_groq):
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Dry van")
    mock_chat_groq.return_value = mock_model

    provider = GroqProvider(LLMConfig(model="llama-3.3-70b-versatile"))
    result = provider.complete(messages=[("human", "What equipment type?")])

    assert result == "Dry van"


@patch("langchain_groq.ChatGroq")
def test_complete_structured_returns_schema(mock_chat_groq):
    mock_model = MagicMock()
    structured_model = MagicMock()
    structured_model.invoke.return_value = EquipmentAnswer(equipment="reefer")
    mock_model.with_structured_output.return_value = structured_model
    mock_chat_groq.return_value = mock_model

    provider = GroqProvider(LLMConfig(model="llama-3.3-70b-versatile"))
    result = provider.complete_structured(
        EquipmentAnswer,
        prompt="Extract equipment",
    )

    assert result.equipment == "reefer"


def test_build_model_raises_when_dependency_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def import_mock(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "langchain_groq":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_mock)

    with pytest.raises(ImportError, match="langchain-groq is required"):
        GroqProvider(LLMConfig(model="llama-3.3-70b-versatile"))
