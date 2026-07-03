"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

MessageInput = str | tuple[str, str] | dict[str, str]

ROLE_MAP = {
    "system": SystemMessage,
    "human": HumanMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
    "ai": AIMessage,
}


@dataclass
class LLMConfig:
    """Runtime configuration for an LLM provider."""

    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: float | None = None
    max_retries: int = 2
    api_key: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def normalize_messages(messages: Sequence[MessageInput]) -> list[BaseMessage]:
    """Convert flexible message inputs into LangChain message objects."""
    if not messages:
        raise ValueError("messages must not be empty")

    normalized: list[BaseMessage] = []
    for message in messages:
        if isinstance(message, str):
            normalized.append(HumanMessage(content=message))
            continue

        if isinstance(message, tuple):
            role, content = message
            message_cls = ROLE_MAP.get(role.lower())
            if message_cls is None:
                raise ValueError(f"Unsupported message role: {role}")
            normalized.append(message_cls(content=content))
            continue

        if isinstance(message, dict):
            role = message.get("role")
            content = message.get("content")
            if not role or content is None:
                raise ValueError("Dict messages require 'role' and 'content' keys")
            message_cls = ROLE_MAP.get(str(role).lower())
            if message_cls is None:
                raise ValueError(f"Unsupported message role: {role}")
            normalized.append(message_cls(content=content))
            continue

        raise TypeError(f"Unsupported message type: {type(message)!r}")

    return normalized


def build_conversation(
    *,
    system_prompt: str | None = None,
    history: Sequence[MessageInput] | None = None,
    prompt: str | None = None,
    messages: Sequence[MessageInput] | None = None,
) -> list[BaseMessage]:
    """Build a full message list from system prompt, history, and current prompt."""
    has_legacy_messages = messages is not None
    has_prompt_inputs = any(
        value is not None for value in (system_prompt, history, prompt)
    )

    if has_legacy_messages and has_prompt_inputs:
        raise ValueError(
            "Pass either `messages` or (`system_prompt`/`history`/`prompt`), not both."
        )

    if has_legacy_messages:
        return normalize_messages(messages)

    if prompt is None:
        raise ValueError("Either `messages` or `prompt` must be provided.")

    composed: list[MessageInput] = []
    if system_prompt:
        composed.append(("system", system_prompt))
    if history:
        composed.extend(history)
    composed.append(prompt)

    return normalize_messages(composed)


def extract_text_content(response: AIMessage) -> str:
    """Return plain text from a LangChain AIMessage."""
    if hasattr(response, "text") and response.text:
        return response.text

    content = response.content
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))
        return "".join(text_parts)

    return str(content)


class BaseLLMProvider(ABC):
    """Provider-agnostic interface for text and structured LLM calls."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._model = self._build_model()

    @abstractmethod
    def _build_model(self) -> BaseChatModel:
        """Instantiate the provider-specific LangChain chat model."""

    def _model_kwargs(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build kwargs passed to the underlying chat model constructor."""
        overrides = overrides or {}
        kwargs: dict[str, Any] = {
            "model": overrides.get("model", self.config.model),
            "max_retries": overrides.get("max_retries", self.config.max_retries),
        }

        temperature = overrides.get("temperature", self.config.temperature)
        if temperature is not None:
            kwargs["temperature"] = temperature

        max_tokens = overrides.get("max_tokens", self.config.max_tokens)
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        timeout = overrides.get("timeout", self.config.timeout)
        if timeout is not None:
            kwargs["timeout"] = timeout

        api_key = overrides.get("api_key", self.config.api_key)
        if api_key is not None:
            kwargs["api_key"] = api_key

        extra = {**self.config.extra, **overrides.get("extra", {})}
        for key, value in extra.items():
            if key not in kwargs:
                kwargs[key] = value

        return kwargs

    def _get_model(self, **overrides: Any) -> BaseChatModel:
        """Return the configured model, optionally rebuilt with call-time overrides."""
        if not overrides:
            return self._model

        original_config = self.config
        try:
            self.config = LLMConfig(
                model=overrides.get("model", original_config.model),
                temperature=overrides.get("temperature", original_config.temperature),
                max_tokens=overrides.get("max_tokens", original_config.max_tokens),
                timeout=overrides.get("timeout", original_config.timeout),
                max_retries=overrides.get("max_retries", original_config.max_retries),
                api_key=overrides.get("api_key", original_config.api_key),
                extra={**original_config.extra, **overrides.get("extra", {})},
            )
            return self._build_model()
        finally:
            self.config = original_config

    def complete(
        self,
        prompt: str | None = None,
        *,
        system_prompt: str | None = None,
        history: Sequence[MessageInput] | None = None,
        messages: Sequence[MessageInput] | None = None,
        **overrides: Any,
    ) -> str:
        """Run a standard text completion and return the model response."""
        model = self._get_model(**overrides)
        conversation = build_conversation(
            system_prompt=system_prompt,
            history=history,
            prompt=prompt,
            messages=messages,
        )
        response = model.invoke(conversation)
        if not isinstance(response, AIMessage):
            raise TypeError(f"Expected AIMessage, got {type(response)!r}")
        return extract_text_content(response)

    def complete_structured(
        self,
        schema: type[T],
        prompt: str | None = None,
        *,
        system_prompt: str | None = None,
        history: Sequence[MessageInput] | None = None,
        messages: Sequence[MessageInput] | None = None,
        **overrides: Any,
    ) -> T:
        """Run a structured completion and return a validated Pydantic object."""
        model = self._get_model(**overrides)
        conversation = build_conversation(
            system_prompt=system_prompt,
            history=history,
            prompt=prompt,
            messages=messages,
        )
        structured_model = model.with_structured_output(schema)
        result = structured_model.invoke(conversation)
        if not isinstance(result, schema):
            raise TypeError(f"Expected {schema.__name__}, got {type(result)!r}")
        return result
