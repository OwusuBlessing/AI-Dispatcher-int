#!/usr/bin/env python3
"""Manual smoke test for Stage 5 load reader/normalizer.

    python scripts/test_load_reader.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rules.missing_data_rule import evaluate_missing_data
from src.services.load_normalizer import load_and_normalize_loads

LOADS_FILE = PROJECT_ROOT / "data/raw/loads.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "src/outputs"


def main() -> None:
    if not LOADS_FILE.exists():
        raise SystemExit(f"Loads file not found: {LOADS_FILE}")

    print("=" * 72)
    print("Load reader / normalizer smoke test (Stage 5)")
    print(f"File: {LOADS_FILE}")
    print("=" * 72)

    report = load_and_normalize_loads(LOADS_FILE)
    print(f"\nNormalized loads : {len(report.loads)}")
    print(f"Skipped rows     : {len(report.skipped_rows)}")
    print(f"Warnings         : {len(report.warnings)}")

    trailer_counts = Counter(load.trailer for load in report.loads)
    print("\n--- Trailer counts ---")
    for trailer, count in sorted(trailer_counts.items()):
        print(f"{trailer:12} {count}")

    missing_data_failures = [
        load.load_id
        for load in report.loads
        if evaluate_missing_data(load).status.value == "FAIL"
    ]
    print("\n--- Missing-data rule failures ---")
    print(f"count: {len(missing_data_failures)}")
    if missing_data_failures:
        print("ids:", ", ".join(missing_data_failures[:10]))

    sample = report.loads[:3]
    print("\n--- Sample loads ---")
    print(json.dumps([load.model_dump(mode="json") for load in sample], indent=2))

    if OUTPUT_DIR:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "loads_normalized.json"
        output_path.write_text(
            json.dumps([load.model_dump(mode="json") for load in report.loads], indent=2),
            encoding="utf-8",
        )
        print(f"\nSaved → {output_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
