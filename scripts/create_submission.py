#!/usr/bin/env python3
"""Generate submission artifacts from conversation + loads.

    python scripts/create_submission.py
    python scripts/create_submission.py \\
        --conversation data/raw/conversation.txt \\
        --loads data/raw/loads.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from configs.settings import OUTPUT_DIR, PROJECT_ROOT, RAW_DATA_DIR
from src.pipelines.submission_pipeline import SubmissionPipeline
from src.services.submission_formatter import (
    format_audit_table,
    format_profile_table,
    format_top_loads_table,
)

DEFAULT_CONVERSATION = RAW_DATA_DIR / "conversation.txt"
DEFAULT_LOADS = RAW_DATA_DIR / "loads.xlsx"


def _print_section(title: str, body: str) -> None:
    print(f"\n{'=' * 72}")
    print(title)
    print("=" * 72)
    print(body)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run extraction + matching and write submission deliverables.",
    )
    parser.add_argument(
        "--conversation",
        type=Path,
        default=DEFAULT_CONVERSATION,
        help=f"Path to transcript (default: {DEFAULT_CONVERSATION})",
    )
    parser.add_argument(
        "--loads",
        type=Path,
        default=DEFAULT_LOADS,
        help=f"Path to loads spreadsheet (default: {DEFAULT_LOADS})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory for JSON + submission.md (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--readme",
        type=Path,
        default=PROJECT_ROOT / "README.md",
        help="Path for generated README (default: project README.md)",
    )
    args = parser.parse_args()

    print("AI Dispatcher — submission pipeline")
    print(f"Conversation : {args.conversation}")
    print(f"Loads        : {args.loads}")
    print(f"Output dir   : {args.output_dir}")

    pipeline = SubmissionPipeline()
    result = pipeline.run(
        args.conversation,
        args.loads,
        output_dir=args.output_dir,
        readme_path=args.readme,
    )

    _print_section("Driver Profile", format_profile_table(result.driver))
    _print_section("Load Audit", format_audit_table(result.matching.audits))
    _print_section("Top 3 Loads", format_top_loads_table(result.matching))

    print(f"\n{'=' * 72}")
    print("Artifacts written")
    print("=" * 72)
    print(f"  Submission : {result.submission_path}")
    print(f"  README     : {result.readme_path}")
    print(f"  Profile    : {result.profile_json_path}")
    print(f"  Audit JSON : {result.audit_json_path}")
    print(f"  Top loads  : {result.top_loads_json_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
