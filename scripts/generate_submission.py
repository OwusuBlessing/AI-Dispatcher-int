#!/usr/bin/env python3
"""Generate submission artifacts (alias for create_submission.py)."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent / "create_submission.py"),
        run_name="__main__",
    )
