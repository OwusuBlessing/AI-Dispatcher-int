"""Stage 9 — Effective rate calculator."""

from __future__ import annotations


def calculate_effective_rate(
    price: float | None,
    total_miles: float | None,
) -> float | None:
    """Return price divided by total trip miles, or None when not computable."""
    if price is None or total_miles is None or total_miles <= 0:
        return None
    return price / total_miles
