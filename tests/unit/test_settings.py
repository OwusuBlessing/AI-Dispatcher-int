"""Unit tests for application settings."""

import os
from pathlib import Path

import pytest

from configs.settings import Settings, get_settings
from src.domain.enums import LLMProvider

ENV_KEYS = [
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
    "LOG_LEVEL",
    "GEOCODER_PROVIDER",
    "NOMINATIM_USER_AGENT",
    "DATA_DIR",
    "CACHE_DIR",
    "OUTPUT_DIR",
]


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    get_settings.cache_clear()
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield
    get_settings.cache_clear()


def test_from_env_loads_dotenv_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LLM_PROVIDER=anthropic",
                "ANTHROPIC_API_KEY=anthropic-from-dotenv",
                "OPENAI_API_KEY=openai-from-dotenv",
                "LOG_LEVEL=DEBUG",
            ]
        )
    )

    settings = Settings.from_env(env_file)

    assert settings.llm_provider == LLMProvider.ANTHROPIC
    assert settings.anthropic_api_key == "anthropic-from-dotenv"
    assert settings.openai_api_key == "openai-from-dotenv"
    assert settings.log_level == "DEBUG"
    assert settings._env_file == env_file


def test_from_env_does_not_override_existing_process_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=from-dotenv")

    monkeypatch.setenv("OPENAI_API_KEY", "from-process-env")

    settings = Settings.from_env(env_file)

    assert settings.openai_api_key == "from-process-env"


def test_empty_env_values_become_none(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=\nANTHROPIC_API_KEY=   ")

    settings = Settings.from_env(env_file)

    assert settings.openai_api_key is None
    assert settings.anthropic_api_key is None


def test_get_llm_api_key_returns_provider_specific_key(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LLM_PROVIDER=openai",
                "OPENAI_API_KEY=openai-key",
                "GROQ_API_KEY=groq-key",
            ]
        )
    )
    settings = Settings.from_env(env_file)

    assert settings.get_llm_api_key() == "openai-key"
    assert settings.get_llm_api_key(LLMProvider.GROQ) == "groq-key"


def test_get_settings_is_cached(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=cached-key")
    monkeypatch.setattr("configs.settings.PROJECT_ROOT", tmp_path)

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.openai_api_key == "cached-key"
