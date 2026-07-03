"""Anthropic LLM provider."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from src.providers.llm.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """LangChain ChatAnthropic wrapper."""

    def _build_model(self) -> BaseChatModel:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError(
                "langchain-anthropic is required. Install with: pip install -e '.[ai]'"
            ) from exc

        return ChatAnthropic(**self._model_kwargs())
