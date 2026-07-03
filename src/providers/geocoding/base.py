"""Base geocoding provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.schemas import LocationRef, ResolvedLocation


class BaseGeocodingProvider(ABC):
    """Resolve structured locations to coordinates."""

    @abstractmethod
    def geocode(self, location: LocationRef) -> ResolvedLocation | None:
        """Return coordinates for a location, or None when lookup fails."""
