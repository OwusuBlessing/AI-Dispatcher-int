"""Unit tests for LLM base utilities and interface."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.providers.llm.base import (
    LLMConfig,
    build_conversation,
    extract_text_content,
    normalize_messages,
)
from src.providers.llm.openai_provider import OpenAIProvider


class SampleSchema(BaseModel):
    answer: str = Field(description="Short answer")


def test_normalize_messages_from_string():
    messages = normalize_messages(["Hello"])
    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "Hello"


def test_normalize_messages_from_tuple_roles():
    messages = normalize_messages(
        [
            ("system", "You are helpful."),
            ("human", "Hello"),
            ("assistant", "Hi there"),
        ]
    )
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)


def test_normalize_messages_from_dict_roles():
    messages = normalize_messages(
        [{"role": "user", "content": "Hello"}, {"role": "ai", "content": "Hi"}]
    )
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)


def test_normalize_messages_rejects_empty_input():
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_messages([])


def test_normalize_messages_rejects_unknown_role():
    with pytest.raises(ValueError, match="Unsupported message role"):
        normalize_messages([("moderator", "Hello")])


def test_extract_text_content_from_string():
    message = AIMessage(content="plain text")
    assert extract_text_content(message) == "plain text"


def test_extract_text_content_from_blocks():
    message = AIMessage(content=[{"type": "text", "text": "block text"}])
    assert extract_text_content(message) == "block text"


@patch("langchain_openai.ChatOpenAI")
def test_model_kwargs_include_runtime_settings(mock_chat_openai):
    mock_chat_openai.return_value = MagicMock()
    provider = OpenAIProvider(
        LLMConfig(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=256,
            timeout=30.0,
            max_retries=3,
            api_key="test-key",
            extra={"service_tier": "flex"},
        )
    )
    kwargs = provider._model_kwargs()
    assert kwargs == {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 256,
        "timeout": 30.0,
        "max_retries": 3,
        "api_key": "test-key",
        "service_tier": "flex",
    }


def test_build_conversation_with_system_prompt_history_and_prompt():
    messages = build_conversation(
        system_prompt="You are a dispatcher assistant.",
        history=[
            ("human", "I'm in Dallas."),
            ("assistant", "Noted."),
        ],
        prompt="What is my minimum rate?",
    )

    assert len(messages) == 4
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "You are a dispatcher assistant."
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
    assert isinstance(messages[3], HumanMessage)
    assert messages[3].content == "What is my minimum rate?"


def test_build_conversation_rejects_mixed_input_modes():
    with pytest.raises(ValueError, match="not both"):
        build_conversation(
            system_prompt="System",
            messages=[("human", "Hello")],
        )


def test_build_conversation_requires_prompt_or_messages():
    with pytest.raises(ValueError, match="Either `messages` or `prompt`"):
        build_conversation(system_prompt="System only")


@patch("langchain_openai.ChatOpenAI")
def test_complete_invokes_model_with_normalized_messages(mock_chat_openai):
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Done")
    mock_chat_openai.return_value = mock_model

    provider = OpenAIProvider(LLMConfig(model="gpt-4o-mini"))
    result = provider.complete(
        messages=[("system", "Be concise"), ("human", "Summarize")],
    )

    assert result == "Done"
    invoked_messages = mock_model.invoke.call_args.args[0]
    assert isinstance(invoked_messages[0], SystemMessage)
    assert isinstance(invoked_messages[1], HumanMessage)


@patch("langchain_openai.ChatOpenAI")
def test_complete_supports_system_prompt_history_and_prompt(mock_chat_openai):
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="2.0")
    mock_chat_openai.return_value = mock_model

    provider = OpenAIProvider(LLMConfig(model="gpt-4o-mini"))
    result = provider.complete(
        "What is my minimum rate?",
        system_prompt="Extract freight profile fields.",
        history=[("human", "I need at least $2/mile."), ("assistant", "Understood.")],
    )

    assert result == "2.0"
    invoked_messages = mock_model.invoke.call_args.args[0]
    assert len(invoked_messages) == 4
    assert isinstance(invoked_messages[0], SystemMessage)
    assert isinstance(invoked_messages[-1], HumanMessage)


@patch("langchain_openai.ChatOpenAI")
def test_complete_structured_returns_validated_schema(mock_chat_openai):
    mock_model = MagicMock()
    structured_model = MagicMock()
    structured_model.invoke.return_value = SampleSchema(answer="42")
    mock_model.with_structured_output.return_value = structured_model
    mock_chat_openai.return_value = mock_model

    provider = OpenAIProvider(LLMConfig(model="gpt-4o-mini"))
    result = provider.complete_structured(
        SampleSchema,
        prompt="What is the answer?",
        system_prompt="Return only structured output.",
    )

    assert result.answer == "42"
    mock_model.with_structured_output.assert_called_once_with(SampleSchema)
    invoked_messages = structured_model.invoke.call_args.args[0]
    assert isinstance(invoked_messages[0], SystemMessage)
    assert isinstance(invoked_messages[1], HumanMessage)


@patch("langchain_openai.ChatOpenAI")
def test_complete_supports_call_time_overrides(mock_chat_openai):
    built_models: list[MagicMock] = []

    def build_side_effect(**kwargs):
        model = MagicMock()
        model.invoke.return_value = AIMessage(content="override")
        built_models.append((kwargs, model))
        return model

    mock_chat_openai.side_effect = lambda **kwargs: build_side_effect(**kwargs)

    provider = OpenAIProvider(LLMConfig(model="gpt-4o-mini", temperature=0.0))
    result = provider.complete(
        "Hello",
        temperature=0.7,
        max_tokens=100,
        model="gpt-4o",
    )

    assert result == "override"
    assert built_models[-1][0]["model"] == "gpt-4o"
    assert built_models[-1][0]["temperature"] == 0.7
    assert built_models[-1][0]["max_tokens"] == 100
