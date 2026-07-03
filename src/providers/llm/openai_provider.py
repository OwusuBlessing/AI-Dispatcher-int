"""OpenAI LLM provider."""

from __future__ import annotations

from typing import Any, Sequence, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from src.providers.llm.base import BaseLLMProvider, MessageInput, build_conversation

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(BaseLLMProvider):
    """LangChain ChatOpenAI wrapper."""

    def _build_model(self) -> BaseChatModel:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required. Install with: pip install -e '.[ai]'"
            ) from exc

        return ChatOpenAI(**self._model_kwargs())

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
        """Use function calling — OpenAI strict JSON schema rejects nested optional fields."""
        model = self._get_model(**overrides)
        conversation = build_conversation(
            system_prompt=system_prompt,
            history=history,
            prompt=prompt,
            messages=messages,
        )
        structured_model = model.with_structured_output(
            schema,
            method="function_calling",
        )
        result = structured_model.invoke(conversation)
        if not isinstance(result, schema):
            raise TypeError(f"Expected {schema.__name__}, got {type(result)!r}")
        return result
