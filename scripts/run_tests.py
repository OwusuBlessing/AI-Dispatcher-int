#!/usr/bin/env python3
"""Run the test suite."""

import subprocess
import sys


def main() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        check=False,
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
