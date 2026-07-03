"""Unit tests for LLM provider factory."""

import os
from unittest.mock import patch

import pytest

from configs.settings import Settings
from src.domain.enums import LLMProvider
from src.providers.llm.anthropic_provider import AnthropicProvider
from src.providers.llm.factory import create_llm_provider
from src.providers.llm.google_provider import GoogleProvider
from src.providers.llm.groq_provider import GroqProvider
from src.providers.llm.openai_provider import OpenAIProvider


@patch("langchain_openai.ChatOpenAI")
def test_create_openai_provider(mock_chat_openai):
    mock_chat_openai.return_value = object()

    provider = create_llm_provider(
        LLMProvider.OPENAI,
        model="gpt-4o",
        temperature=0.2,
        api_key="sk-test",
    )

    assert isinstance(provider, OpenAIProvider)
    assert provider.config.model == "gpt-4o"
    assert provider.config.temperature == 0.2
    assert provider.config.api_key == "sk-test"


@patch("langchain_anthropic.ChatAnthropic")
def test_create_anthropic_provider(mock_chat_anthropic):
    mock_chat_anthropic.return_value = object()

    provider = create_llm_provider("anthropic")

    assert isinstance(provider, AnthropicProvider)
    assert provider.config.model == "claude-haiku-4-5-20251001"


@patch("langchain_groq.ChatGroq")
def test_create_groq_provider(mock_chat_groq):
    mock_chat_groq.return_value = object()

    provider = create_llm_provider("groq")

    assert isinstance(provider, GroqProvider)
    assert provider.config.model == "llama-3.3-70b-versatile"


@patch("langchain_google_genai.ChatGoogleGenerativeAI")
def test_create_google_provider(mock_chat_google):
    mock_chat_google.return_value = object()

    provider = create_llm_provider("google")

    assert isinstance(provider, GoogleProvider)
    assert provider.config.model == "gemini-2.0-flash"


@patch.dict(os.environ, {}, clear=True)
@patch("langchain_anthropic.ChatAnthropic")
def test_create_provider_from_environment(mock_chat_anthropic):
    mock_chat_anthropic.return_value = object()
    settings = Settings(
        llm_provider=LLMProvider.ANTHROPIC,
        anthropic_api_key="env-key",
    )

    provider = create_llm_provider(settings=settings)

    assert isinstance(provider, AnthropicProvider)
    assert provider.config.api_key == "env-key"


def test_create_provider_rejects_unknown_name():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_provider("unknown-provider")
