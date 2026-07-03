"""Groq LLM provider."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from src.providers.llm.base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    """LangChain ChatGroq wrapper."""

    def _build_model(self) -> BaseChatModel:
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise ImportError(
                "langchain-groq is required. Install with: pip install -e '.[ai]'"
            ) from exc

        return ChatGroq(**self._model_kwargs())
