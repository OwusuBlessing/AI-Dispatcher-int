"""Location matching for driver no-go and preference checks."""

from __future__ import annotations

import re

from src.domain.schemas import DriverProfile, Load

_CITY_STATE_PATTERN = re.compile(r"^\s*(?P<city>.+?)\s*,\s*(?P<state>[A-Za-z]{2})\s*$")


def parse_location_label(label: str) -> tuple[str, str | None]:
    """Parse ``City, ST`` or plain city into comparable parts."""
    text = label.strip()
    match = _CITY_STATE_PATTERN.match(text)
    if match:
        return match.group("city").strip().lower(), match.group("state").upper()
    return text.lower(), None


def format_load_stop(city: str, state: str | None = None) -> str:
    """Build a readable stop label for audit messages."""
    city = city.strip()
    if not city:
        return "unknown location"
    if state and state.strip():
        return f"{city}, {state.strip().upper()}"
    return city


def load_stop_matches_label(
    label: str,
    city: str,
    state: str | None = None,
) -> bool:
    """Return True when a load origin/destination matches a profile location label."""
    if not city or not city.strip():
        return False

    label_city, label_state = parse_location_label(label)
    load_city = city.strip().lower()
    if label_city != load_city:
        return False

    if label_state:
        if state and state.strip():
            return label_state == state.strip().upper()
        return True
    return True


def collect_hard_avoided_places(profile: DriverProfile) -> list[str]:
    """Return explicit no-go cities/regions from the driver profile."""
    preferences = profile.preferences
    places: list[str] = []

    for field in (preferences.avoided_cities, preferences.avoided_regions):
        if field is None or not field.value:
            continue
        places.extend(str(item) for item in field.value if str(item).strip())

    return places


def find_blocked_load_stops(
    profile: DriverProfile,
    load: Load,
) -> list[tuple[str, str]]:
    """Return blocked (stop_role, place_label) pairs for hard no-go matches."""
    blocked: list[tuple[str, str]] = []
    avoided = collect_hard_avoided_places(profile)
    if not avoided:
        return blocked

    stops = (
        ("pickup", load.origin_city, load.origin_state),
        ("delivery", load.destination_city, load.destination_state),
    )
    for role, city, state in stops:
        for place in avoided:
            if load_stop_matches_label(place, city, state):
                blocked.append((role, format_load_stop(city, state)))
                break
    return blocked
