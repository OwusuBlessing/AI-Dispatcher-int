#!/usr/bin/env python3
"""Manual smoke test: full matching pipeline (Stages 5–10).

    python scripts/test_matching.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.enums import EligibilityStatus
from src.domain.schemas import RankedLoad, ResolvedDriverProfile
from src.pipelines.matching_pipeline import MatchingPipeline

LOADS_FILE = PROJECT_ROOT / "data/raw/loads.xlsx"
PROFILE_FILE = PROJECT_ROOT / "src/outputs/resolved_driver_profile_conversation.json"
OUTPUT_DIR = PROJECT_ROOT / "src/outputs"


def _format_rate(audit_rate: float | None) -> str:
    return f"${audit_rate:.2f}/mi" if audit_rate is not None else "n/a"


def _format_miles(total_miles: float | None) -> str:
    return f"{total_miles:.0f} mi" if total_miles is not None else "n/a"


def _print_ranked_table(title: str, items: list[RankedLoad], *, sort_label: str) -> None:
    print(f"\n--- {title} ({sort_label}) ---")
    if not items:
        print("(none)")
        return
    print(f"{'#':<3} {'Load':<5} {'Price':>8} {'Rate':>12} {'Miles':>10}  Route / reason")
    print("-" * 72)
    for item in items:
        audit = item.audit
        price = f"${item.load.price:,.0f}" if item.load.price is not None else "n/a"
        route = f"{item.load.origin_city} → {item.load.destination_city or '?'}"
        print(
            f"{item.rank:<3} {item.load.load_id:<5} {price:>8} "
            f"{_format_rate(audit.effective_rate):>12} {_format_miles(audit.total_miles):>10}  "
            f"{route}"
        )
        print(f"    → {audit.reason}")


def main() -> None:
    if not LOADS_FILE.exists():
        raise SystemExit(f"Loads file not found: {LOADS_FILE}")
    if not PROFILE_FILE.exists():
        raise SystemExit(
            f"Resolved profile not found: {PROFILE_FILE}. "
            "Run scripts/test_geocoder.py first."
        )

    driver = ResolvedDriverProfile.model_validate_json(
        PROFILE_FILE.read_text(encoding="utf-8")
    )
    pipeline = MatchingPipeline()

    print("=" * 72)
    print("Matching pipeline smoke test (Stages 5–10)")
    print(f"Profile: {PROFILE_FILE.name}")
    print(f"Loads  : {LOADS_FILE.name}")
    print(f"Driver equipment: {driver.canonical_equipment}")
    print("=" * 72)

    report, result = pipeline.run_from_files(driver, LOADS_FILE)

    print(f"\nNormalized loads: {len(report.loads)}")
    print(f"Audit entries   : {len(result.audits)}")

    print("\n--- Eligibility summary ---")
    for audit in result.audits:
        status = audit.eligible.value
        print(
            f"{audit.load_id:4} {status:6} | {_format_rate(audit.effective_rate):>10} | "
            f"{_format_miles(audit.total_miles):>8} | {audit.reason}"
        )

    eligible = [a for a in result.audits if a.eligible == EligibilityStatus.ACCEPT]
    rejected = [a for a in result.audits if a.eligible == EligibilityStatus.REJECT]
    print(f"\nAccept: {len(eligible)}  Reject: {len(rejected)}")

    _print_ranked_table(
        "Top 3 eligible loads",
        result.top_loads,
        sort_label="by effective rate",
    )

    _print_ranked_table(
        "Top 3 high-paying rejected loads",
        result.top_rejected_loads,
        sort_label="by flat price",
    )

    if result.featured_rejected_load is not None:
        featured = result.featured_rejected_load
        print("\n--- Featured rejected load (Part A pick) ---")
        print(
            f"{featured.load.load_id}: ${featured.load.price:,.0f} "
            f"{featured.load.origin_city} → {featured.load.destination_city or '?'}"
        )
        print(f"Why rejected: {featured.audit.reason}")

    if OUTPUT_DIR:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        audit_path = OUTPUT_DIR / "load_audit.json"
        audit_path.write_text(
            json.dumps(
                [audit.model_dump(mode="json") for audit in result.audits],
                indent=2,
            ),
            encoding="utf-8",
        )
        ranked_path = OUTPUT_DIR / "top_loads.json"
        ranked_path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in result.top_loads],
                indent=2,
            ),
            encoding="utf-8",
        )
        rejected_path = OUTPUT_DIR / "rejected_high_paying.json"
        rejected_path.write_text(
            json.dumps(
                {
                    "featured": (
                        result.featured_rejected_load.model_dump(mode="json")
                        if result.featured_rejected_load
                        else None
                    ),
                    "top_rejected": [
                        item.model_dump(mode="json")
                        for item in result.top_rejected_loads
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nSaved → {audit_path}")
        print(f"Saved → {ranked_path}")
        print(f"Saved → {rejected_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
