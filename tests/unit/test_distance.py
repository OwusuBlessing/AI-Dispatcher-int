"""Distance calculator unit tests."""

from __future__ import annotations

import math

import pytest

from src.domain.schemas import (
    DriverProfile,
    Load,
    ResolvedDriverProfile,
    ResolvedLocation,
)
from src.services.distance_service import (
    EARTH_RADIUS_MILES,
    compute_load_distances,
    haversine_miles,
)


def test_haversine_same_point_is_zero():
    assert haversine_miles(32.77, -96.79, 32.77, -96.79) == pytest.approx(0.0)


def test_haversine_dallas_to_houston_approximate():
    miles = haversine_miles(32.7767, -96.797, 29.7604, -95.3698)
    assert 210 <= miles <= 240


def test_haversine_uses_earth_radius_constant():
    # Quarter circumference should be roughly pi * radius / 2
    miles = haversine_miles(0.0, 0.0, 0.0, 90.0)
    assert miles == pytest.approx(math.pi * EARTH_RADIUS_MILES / 2, rel=0.01)


@pytest.fixture
def geocoded_driver() -> ResolvedDriverProfile:
    return ResolvedDriverProfile(
        profile=DriverProfile(),
        current_location=ResolvedLocation(
            city="Dallas",
            state="TX",
            lat=32.7767,
            lon=-96.797,
        ),
        home_base=ResolvedLocation(
            city="San Antonio",
            state="TX",
            lat=29.4241,
            lon=-98.4936,
        ),
    )


def test_compute_load_distances_fills_all_legs(geocoded_driver):
    load = Load(
        load_id="L08",
        origin_city="Dallas",
        origin_latitude=32.7767,
        origin_longitude=-96.797,
        destination_city="Mcallen",
        destination_latitude=26.2034,
        destination_longitude=-98.23,
        trailer="hotshot",
        price=1700.0,
    )

    metrics = compute_load_distances(geocoded_driver, load)

    assert metrics.deadhead_to_origin == pytest.approx(0.0, abs=0.1)
    assert metrics.loaded_miles is not None
    assert metrics.loaded_miles > 400
    assert metrics.deadhead_home is not None
    assert metrics.total_miles == pytest.approx(
        metrics.deadhead_to_origin + metrics.loaded_miles + metrics.deadhead_home
    )


def test_compute_load_distances_missing_destination_coords(geocoded_driver):
    load = Load(
        load_id="L07",
        origin_city="Tulsa",
        origin_latitude=36.154,
        origin_longitude=-95.9928,
        destination_city="",
        trailer="hotshot",
        price=1100.0,
    )

    metrics = compute_load_distances(geocoded_driver, load)

    assert metrics.deadhead_to_origin is not None
    assert metrics.loaded_miles is None
    assert metrics.deadhead_home is None
    assert metrics.total_miles is None
