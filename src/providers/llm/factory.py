"""LLM provider factory."""

from __future__ import annotations

from typing import Any

from configs.settings import LLM_API_KEY_ENV_VARS, Settings, get_settings
from src.domain.enums import LLMProvider
from src.providers.llm.anthropic_provider import AnthropicProvider
from src.providers.llm.base import BaseLLMProvider, LLMConfig
from src.providers.llm.google_provider import GoogleProvider
from src.providers.llm.groq_provider import GroqProvider
from src.providers.llm.openai_provider import OpenAIProvider

DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.ANTHROPIC: "claude-haiku-4-5-20251001",
    LLMProvider.GROQ: "llama-3.3-70b-versatile",
    LLMProvider.GOOGLE: "gemini-2.0-flash",
}

PROVIDER_CLASSES: dict[LLMProvider, type[BaseLLMProvider]] = {
    LLMProvider.OPENAI: OpenAIProvider,
    LLMProvider.ANTHROPIC: AnthropicProvider,
    LLMProvider.GROQ: GroqProvider,
    LLMProvider.GOOGLE: GoogleProvider,
}

API_KEY_ENV_VARS = LLM_API_KEY_ENV_VARS


def create_llm_provider(
    provider: LLMProvider | str | None = None,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    max_retries: int = 2,
    api_key: str | None = None,
    extra: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> BaseLLMProvider:
    """Create a configured LLM provider instance."""
    app_settings = settings or get_settings()
    resolved_provider = _resolve_provider(provider, app_settings)
    provider_cls = PROVIDER_CLASSES[resolved_provider]
    resolved_model = model or DEFAULT_MODELS[resolved_provider]
    resolved_api_key = api_key or app_settings.get_llm_api_key(resolved_provider)

    config = LLMConfig(
        model=resolved_model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        api_key=resolved_api_key,
        extra=extra or {},
    )
    return provider_cls(config)


def _resolve_provider(
    provider: LLMProvider | str | None,
    settings: Settings,
) -> LLMProvider:
    if provider is None:
        provider = settings.llm_provider

    if isinstance(provider, LLMProvider):
        return provider

    normalized = str(provider).strip().lower()
    try:
        return LLMProvider(normalized)
    except ValueError as exc:
        supported = ", ".join(member.value for member in LLMProvider)
        raise ValueError(
            f"Unsupported LLM provider '{provider}'. Supported: {supported}"
        ) from exc
