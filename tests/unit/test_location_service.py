"""Location matching unit tests."""

from src.domain.schemas import DriverPreferences, DriverProfile, FieldValue, Load
from src.rules.avoided_location_rule import evaluate_avoided_locations
from src.services.location_service import find_blocked_load_stops, load_stop_matches_label


def test_load_stop_matches_city_with_or_without_state():
    assert load_stop_matches_label("Houston, TX", "Houston", None)
    assert load_stop_matches_label("Houston, TX", "Houston", "TX")
    assert not load_stop_matches_label("Houston, TX", "Houston", "OK")


def test_find_blocked_load_stops_checks_pickup_and_delivery():
    profile = DriverProfile(
        preferences=DriverPreferences(
            avoided_cities=FieldValue(
                value=["Houston, TX"],
                evidence="I do not run loads to Houston at all.",
            ),
        ),
    )
    load = Load(
        load_id="L01",
        origin_city="Dallas",
        destination_city="Houston",
        trailer="hotshot",
        price=1500.0,
    )

    blocked = find_blocked_load_stops(profile, load)

    assert blocked == [("delivery", "Houston")]


def test_avoided_location_rule_passes_when_no_policy():
    profile = DriverProfile()
    load = Load(
        load_id="L02",
        origin_city="Austin",
        destination_city="Corpus Christi",
        trailer="hotshot",
        price=1500.0,
    )

    check = evaluate_avoided_locations(profile, load)

    assert check.status.value == "PASS"
