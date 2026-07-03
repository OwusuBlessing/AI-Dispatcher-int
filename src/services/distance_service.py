"""Stage 8 — Distance calculator."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.schemas import Load, ResolvedDriverProfile

EARTH_RADIUS_MILES = 3958.8


@dataclass(frozen=True)
class LoadDistanceMetrics:
    """Miles for each leg of current → origin → destination → home."""

    deadhead_to_origin: float | None
    loaded_miles: float | None
    deadhead_home: float | None

    @property
    def total_miles(self) -> float | None:
        if (
            self.deadhead_to_origin is None
            or self.loaded_miles is None
            or self.deadhead_home is None
        ):
            return None
        return self.deadhead_to_origin + self.loaded_miles + self.deadhead_home


def haversine_miles(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Great-circle distance between two WGS84 points in statute miles."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def _loaded_miles(load: Load) -> float | None:
    if (
        load.origin_latitude is not None
        and load.origin_longitude is not None
        and load.destination_latitude is not None
        and load.destination_longitude is not None
    ):
        return haversine_miles(
            load.origin_latitude,
            load.origin_longitude,
            load.destination_latitude,
            load.destination_longitude,
        )
    if load.loaded_miles is not None:
        return load.loaded_miles
    return None


def compute_load_distances(
    driver: ResolvedDriverProfile,
    load: Load,
) -> LoadDistanceMetrics:
    """Compute deadhead, loaded, and return-home miles for one load."""
    deadhead_to_origin: float | None = None
    if (
        driver.current_location is not None
        and load.origin_latitude is not None
        and load.origin_longitude is not None
    ):
        deadhead_to_origin = haversine_miles(
            driver.current_location.lat,
            driver.current_location.lon,
            load.origin_latitude,
            load.origin_longitude,
        )

    loaded = _loaded_miles(load)

    deadhead_home: float | None = None
    if (
        driver.home_base is not None
        and load.destination_latitude is not None
        and load.destination_longitude is not None
    ):
        deadhead_home = haversine_miles(
            load.destination_latitude,
            load.destination_longitude,
            driver.home_base.lat,
            driver.home_base.lon,
        )

    return LoadDistanceMetrics(
        deadhead_to_origin=deadhead_to_origin,
        loaded_miles=loaded,
        deadhead_home=deadhead_home,
    )
