#!/usr/bin/env python3
"""Manual smoke test for Stage 3 geocoding.

    python scripts/test_geocoder.py

Uses saved profile JSON by default (no LLM). Set RUN_LIVE_NOMINATIM=True to hit OSM.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.schemas import DriverProfile
from src.services.geocoder import GeocoderService, parse_city_state

PROFILE_FILE = PROJECT_ROOT / "src/outputs/driver_profile_conversation.json"
RUN_LIVE_NOMINATIM = True

SAMPLE_LOCATIONS = [
    "Dallas, TX",
    "San Antonio, TX",
    "Buckeye, AZ",
    "Albuquerque, NM",
]


def main() -> None:
    geocoder = GeocoderService.from_settings()

    print("=" * 72)
    print("Geocoder smoke test (Stage 3)")
    print("=" * 72)

    print("\n--- Parse checks ---")
    for location in SAMPLE_LOCATIONS + ["South Texas", "Buckeye area west of Phoenix"]:
        parsed = parse_city_state(location)
        print(f"{location:35} -> {parsed}")

    if not RUN_LIVE_NOMINATIM:
        print("\nRUN_LIVE_NOMINATIM is False — skipping live API lookups.")
        return

    print("\n--- Live geocode lookups ---")
    for location in SAMPLE_LOCATIONS:
        resolved = geocoder.resolve(location)
        if resolved is None:
            print(f"{location:20} FAILED")
        else:
            print(
                f"{location:20} lat={resolved.lat:.4f}, lon={resolved.lon:.4f}"
            )

    if PROFILE_FILE.exists():
        print(f"\n--- Resolve profile: {PROFILE_FILE.name} ---")
        profile = DriverProfile.model_validate_json(
            PROFILE_FILE.read_text(encoding="utf-8")
        )
        resolved_profile = geocoder.resolve_profile(profile)
        print(
            json.dumps(
                resolved_profile.model_dump(mode="json"),
                indent=2,
            )
        )
        output_path = PROJECT_ROOT / "src/outputs/resolved_driver_profile_conversation.json"
        output_path.write_text(
            json.dumps(resolved_profile.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        print(f"\nSaved → {output_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
