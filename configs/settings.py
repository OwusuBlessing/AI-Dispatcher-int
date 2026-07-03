"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from src.domain.enums import LLMProvider

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = PROJECT_ROOT / "src" / "outputs"
CONFIGS_DIR = PROJECT_ROOT / "configs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

LLM_API_KEY_ENV_VARS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GROQ: "GROQ_API_KEY",
    LLMProvider.GOOGLE: "GOOGLE_API_KEY",
}


@dataclass
class Settings:
    """Central application settings backed by `.env` and process environment."""

    llm_provider: LLMProvider = LLMProvider.OPENAI
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_api_key: str | None = None
    google_api_key: str | None = None
    geocoder_provider: str = "nominatim"
    nominatim_user_agent: str = "ai-dispatcher/0.1.0"
    data_dir: Path = DATA_DIR
    cache_dir: Path = CACHE_DIR
    output_dir: Path = OUTPUT_DIR
    log_level: str = "INFO"
    _env_file: Path | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, env_file: Path | str | None = None) -> Settings:
        """Load settings from `.env` and the current process environment."""
        resolved_env_file = Path(env_file) if env_file else PROJECT_ROOT / ".env"
        if resolved_env_file.exists():
            load_dotenv(dotenv_path=resolved_env_file, override=False)

        llm_provider = _parse_llm_provider(os.getenv("LLM_PROVIDER", LLMProvider.OPENAI))

        return cls(
            llm_provider=llm_provider,
            openai_api_key=_empty_to_none(os.getenv("OPENAI_API_KEY")),
            anthropic_api_key=_empty_to_none(os.getenv("ANTHROPIC_API_KEY")),
            groq_api_key=_empty_to_none(os.getenv("GROQ_API_KEY")),
            google_api_key=_empty_to_none(os.getenv("GOOGLE_API_KEY")),
            geocoder_provider=os.getenv("GEOCODER_PROVIDER", "nominatim"),
            nominatim_user_agent=os.getenv(
                "NOMINATIM_USER_AGENT",
                "ai-dispatcher/0.1.0",
            ),
            data_dir=PROJECT_ROOT / os.getenv("DATA_DIR", "data"),
            cache_dir=PROJECT_ROOT / os.getenv("CACHE_DIR", "data/cache"),
            output_dir=PROJECT_ROOT / os.getenv("OUTPUT_DIR", "src/outputs"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            _env_file=resolved_env_file if resolved_env_file.exists() else None,
        )

    def get_llm_api_key(self, provider: LLMProvider | str | None = None) -> str | None:
        """Return the API key for the requested provider, or the default provider."""
        resolved_provider = provider or self.llm_provider
        if not isinstance(resolved_provider, LLMProvider):
            resolved_provider = _parse_llm_provider(resolved_provider)

        key_by_provider = {
            LLMProvider.OPENAI: self.openai_api_key,
            LLMProvider.ANTHROPIC: self.anthropic_api_key,
            LLMProvider.GROQ: self.groq_api_key,
            LLMProvider.GOOGLE: self.google_api_key,
        }
        return key_by_provider[resolved_provider]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings.from_env()


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_llm_provider(value: LLMProvider | str) -> LLMProvider:
    if isinstance(value, LLMProvider):
        return value
    return LLMProvider(str(value).strip().lower())
