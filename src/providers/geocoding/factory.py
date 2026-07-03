"""Geocoding provider factory."""

from __future__ import annotations

from configs.settings import Settings, get_settings
from src.providers.geocoding.base import BaseGeocodingProvider
from src.providers.geocoding.nominatim_provider import NominatimProvider


def create_geocoding_provider(
    provider: str | None = None,
    *,
    settings: Settings | None = None,
) -> BaseGeocodingProvider:
    """Create a configured geocoding provider."""
    app_settings = settings or get_settings()
    resolved_provider = (provider or app_settings.geocoder_provider).strip().lower()

    if resolved_provider == "nominatim":
        return NominatimProvider(user_agent=app_settings.nominatim_user_agent)

    raise ValueError(
        f"Unsupported geocoder provider '{resolved_provider}'. Supported: nominatim"
    )
