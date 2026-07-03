"""Geocoder unit tests."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from src.domain.schemas import (
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
    LocationRef,
    ResolvedLocation,
)
from src.providers.geocoding.nominatim_provider import (
    NOMINATIM_SEARCH_URL,
    NominatimProvider,
)
from src.services.geocoder import (
    GeocoderService,
    location_cache_key,
    parse_city_state,
)
from src.utils.cache import JsonFileCache


class FakeGeocodingProvider:
    """In-memory geocoder for tests."""

    def __init__(
        self,
        results: dict[str, ResolvedLocation] | None = None,
    ) -> None:
        self.results = results or {}
        self.calls: list[LocationRef] = []

    def geocode(self, location: LocationRef) -> ResolvedLocation | None:
        self.calls.append(location)
        return self.results.get(location_cache_key(location))


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "geocode.json"


@pytest.fixture
def geocoder(cache_path: Path) -> GeocoderService:
    provider = FakeGeocodingProvider(
        {
            location_cache_key(
                LocationRef(city="Dallas", state="TX", country="USA")
            ): ResolvedLocation(
                city="Dallas",
                state="TX",
                country="USA",
                lat=32.7767,
                lon=-96.7970,
            ),
        }
    )
    return GeocoderService(provider=provider, cache=JsonFileCache(cache_path))


def test_parse_city_state_accepts_city_st_format():
    parsed = parse_city_state("Dallas, TX")

    assert parsed is not None
    assert parsed.city == "Dallas"
    assert parsed.state == "TX"
    assert parsed.country == "USA"


def test_parse_city_state_rejects_non_geocoder_strings():
    assert parse_city_state("Buckeye area west of Phoenix") is None
    assert parse_city_state(None) is None
    assert parse_city_state("") is None


def test_resolve_uses_provider_and_writes_cache(geocoder: GeocoderService, cache_path: Path):
    resolved = geocoder.resolve("Dallas, TX")

    assert resolved is not None
    assert resolved.lat == pytest.approx(32.7767)
    assert resolved.lon == pytest.approx(-96.7970)
    assert len(geocoder.provider.calls) == 1  # type: ignore[attr-defined]
    assert cache_path.exists()

    # Second call should hit cache, not provider.
    geocoder.provider.calls.clear()  # type: ignore[attr-defined]
    cached = geocoder.resolve("Dallas, TX")

    assert cached is not None
    assert geocoder.provider.calls == []  # type: ignore[attr-defined]


def test_resolve_returns_none_for_unparseable_location(geocoder: GeocoderService):
    assert geocoder.resolve("South Texas") is None


def test_resolve_profile_fills_coordinates_on_driver_profile(geocoder: GeocoderService):
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            current_location=FieldValue(value="Dallas, TX", confidence=1.0),
            home_base=FieldValue(value="San Antonio, TX", confidence=0.95),
        )
    )

    resolved_profile = geocoder.resolve_profile(profile)
    required = resolved_profile.profile.required_fields

    assert resolved_profile.current_location is not None
    assert required.current_latitude is not None
    assert required.current_longitude is not None
    assert required.current_latitude.value == pytest.approx(32.7767)

    # Home not in fake provider — stays unresolved without error.
    assert resolved_profile.home_base is None
    assert required.home_latitude is None
    assert required.home_longitude is None


def test_resolve_profile_skips_null_location_fields(geocoder: GeocoderService):
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            current_location=FieldValue(value="Dallas, TX", confidence=1.0),
        )
    )

    resolved_profile = geocoder.resolve_profile(profile)

    assert resolved_profile.current_location is not None
    assert resolved_profile.home_base is None


@respx.mock
def test_nominatim_provider_parses_search_response():
    respx.get(NOMINATIM_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "lat": "29.4241",
                    "lon": "-98.4936",
                    "display_name": "San Antonio, TX, USA",
                }
            ],
        )
    )
    provider = NominatimProvider(
        user_agent="ai-dispatcher-test",
        min_request_interval=0.0,
    )

    resolved = provider.geocode(
        LocationRef(city="San Antonio", state="TX", country="USA")
    )

    assert resolved is not None
    assert resolved.lat == pytest.approx(29.4241)
    assert resolved.lon == pytest.approx(-98.4936)


@respx.mock
def test_nominatim_provider_returns_none_when_no_results():
    respx.get(NOMINATIM_SEARCH_URL).mock(return_value=httpx.Response(200, json=[]))
    provider = NominatimProvider(
        user_agent="ai-dispatcher-test",
        min_request_interval=0.0,
    )

    assert (
        provider.geocode(LocationRef(city="Nowhere", state="ZZ", country="USA"))
        is None
    )
