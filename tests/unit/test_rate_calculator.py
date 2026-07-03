"""Effective rate calculator unit tests."""

from __future__ import annotations

from src.services.rate_calculator import calculate_effective_rate


def test_calculate_effective_rate_basic():
    assert calculate_effective_rate(2000.0, 1000.0) == 2.0


def test_calculate_effective_rate_returns_none_for_missing_inputs():
    assert calculate_effective_rate(None, 100.0) is None
    assert calculate_effective_rate(100.0, None) is None


def test_calculate_effective_rate_returns_none_for_zero_miles():
    assert calculate_effective_rate(100.0, 0.0) is None
    assert calculate_effective_rate(100.0, -5.0) is None
