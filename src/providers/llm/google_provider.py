"""Google GenAI LLM provider."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from src.providers.llm.base import BaseLLMProvider


class GoogleProvider(BaseLLMProvider):
    """LangChain ChatGoogleGenerativeAI wrapper."""

    def _build_model(self) -> BaseChatModel:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise ImportError(
                "langchain-google-genai is required. Install with: pip install -e '.[ai]'"
            ) from exc

        return ChatGoogleGenerativeAI(**self._model_kwargs())
