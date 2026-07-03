"""Nominatim geocoding provider."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from src.domain.schemas import LocationRef, ResolvedLocation
from src.providers.geocoding.base import BaseGeocodingProvider

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_TIMEOUT_SECONDS = 10.0
MIN_REQUEST_INTERVAL_SECONDS = 1.0


@dataclass
class NominatimProvider(BaseGeocodingProvider):
    """OpenStreetMap Nominatim search API."""

    user_agent: str
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    min_request_interval: float = MIN_REQUEST_INTERVAL_SECONDS
    _last_request_at: float = field(default=0.0, init=False, repr=False)

    def geocode(self, location: LocationRef) -> ResolvedLocation | None:
        self._respect_rate_limit()
        query = self._build_query(location)
        headers = {"User-Agent": self.user_agent}

        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            response = client.get(
                NOMINATIM_SEARCH_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "us",
                },
            )
            response.raise_for_status()
            results = response.json()

        if not results:
            return None

        top = results[0]
        return ResolvedLocation(
            city=location.city,
            state=location.state,
            country=location.country,
            lat=float(top["lat"]),
            lon=float(top["lon"]),
        )

    def _build_query(self, location: LocationRef) -> str:
        parts = [location.city]
        if location.state:
            parts.append(location.state)
        parts.append(location.country)
        return ", ".join(parts)

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_at = time.monotonic()
