"""Stage 3 — Location resolution via geocoder + cache."""

from __future__ import annotations

import re

from configs.settings import Settings, get_settings
from src.domain.schemas import (
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
    LocationRef,
    ResolvedDriverProfile,
    ResolvedLocation,
)
from src.providers.geocoding.base import BaseGeocodingProvider
from src.providers.geocoding.factory import create_geocoding_provider
from src.utils.cache import JsonFileCache

CITY_STATE_PATTERN = re.compile(r"^(.+),\s*([A-Z]{2})$")
GEOCODE_CACHE_FILENAME = "geocode.json"


def parse_city_state(location: str | None) -> LocationRef | None:
    """Parse geocoder-ready ``City, ST`` strings into a LocationRef."""
    if not location or not location.strip():
        return None

    match = CITY_STATE_PATTERN.match(location.strip())
    if not match:
        return None

    city, state = match.groups()
    return LocationRef(city=city.strip(), state=state.strip(), country="USA")


def location_cache_key(location: LocationRef) -> str:
    """Build a stable cache key for a structured location."""
    state = (location.state or "").strip().lower()
    city = location.city.strip().lower()
    country = location.country.strip().lower()
    return f"{city}|{state}|{country}"


class GeocoderService:
    """Resolve profile location strings to coordinates with local caching."""

    def __init__(
        self,
        provider: BaseGeocodingProvider,
        cache: JsonFileCache,
    ) -> None:
        self.provider = provider
        self.cache = cache

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> GeocoderService:
        """Build a geocoder using application settings."""
        app_settings = settings or get_settings()
        cache_path = app_settings.cache_dir / GEOCODE_CACHE_FILENAME
        provider = create_geocoding_provider(settings=app_settings)
        return cls(provider=provider, cache=JsonFileCache(cache_path))

    def resolve(self, location: str | None) -> ResolvedLocation | None:
        """Resolve a ``City, ST`` string to coordinates."""
        location_ref = parse_city_state(location)
        if location_ref is None:
            return None

        cache_key = location_cache_key(location_ref)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return ResolvedLocation.model_validate(cached)

        resolved = self.provider.geocode(location_ref)
        if resolved is None:
            return None

        self.cache.set(cache_key, resolved.model_dump(mode="json"))
        return resolved

    def resolve_profile(self, profile: DriverProfile) -> ResolvedDriverProfile:
        """Geocode current/home locations and backfill Part A lat/lon fields."""
        required = profile.required_fields
        current = self._resolve_and_fill(
            required,
            location_field_name="current_location",
            latitude_field_name="current_latitude",
            longitude_field_name="current_longitude",
        )
        home = self._resolve_and_fill(
            required,
            location_field_name="home_base",
            latitude_field_name="home_latitude",
            longitude_field_name="home_longitude",
        )

        canonical: list[str] = []
        if profile.operational.canonical_equipment is not None:
            canonical = list(profile.operational.canonical_equipment.value)
        elif required.equipment_types is not None:
            canonical = list(required.equipment_types.value)

        return ResolvedDriverProfile(
            profile=profile,
            current_location=current,
            home_base=home,
            canonical_equipment=canonical,
        )

    def _resolve_and_fill(
        self,
        required: DriverRequiredFields,
        *,
        location_field_name: str,
        latitude_field_name: str,
        longitude_field_name: str,
    ) -> ResolvedLocation | None:
        location_field: FieldValue[str] | None = getattr(
            required,
            location_field_name,
        )
        if location_field is None or not location_field.value:
            return None

        resolved = self.resolve(location_field.value)
        if resolved is None:
            return None

        coordinate_notes = (
            f"Geocoded from {location_field.value} "
            f"via {self.provider.__class__.__name__}."
        )
        setattr(
            required,
            latitude_field_name,
            FieldValue(
                value=resolved.lat,
                confidence=location_field.confidence,
                evidence=location_field.evidence,
                reasoning_notes=coordinate_notes,
            ),
        )
        setattr(
            required,
            longitude_field_name,
            FieldValue(
                value=resolved.lon,
                confidence=location_field.confidence,
                evidence=location_field.evidence,
                reasoning_notes=coordinate_notes,
            ),
        )
        return resolved
