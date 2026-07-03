"""Rule engine unit tests."""

from src.domain.schemas import (
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
    Load,
)
from src.rules.base_rule import RuleContext
from src.rules.rate_rule import MinimumRateRule, evaluate_minimum_rate
from src.domain.enums import RuleCheckStatus


def _profile_with_minimum(rate: float | None) -> DriverProfile:
    minimum = (
        FieldValue(value=rate, evidence=f"At least ${rate} per mile")
        if rate is not None
        else None
    )
    return DriverProfile(
        required_fields=DriverRequiredFields(minimum_rate_per_mile=minimum)
    )


def _sample_load() -> Load:
    return Load(
        load_id="L01",
        origin_city="Dallas",
        origin_state="TX",
        destination_city="Houston",
        destination_state="TX",
        trailer="flatbed",
        price=2000.0,
        loaded_miles=200.0,
    )


def test_minimum_rate_rule_skipped_when_profile_minimum_is_null():
    profile = _profile_with_minimum(None)

    result = evaluate_minimum_rate(profile, effective_rate=1.5)

    assert result is None


def test_minimum_rate_rule_passes_when_effective_rate_meets_minimum():
    profile = _profile_with_minimum(2.0)

    result = evaluate_minimum_rate(profile, effective_rate=2.5)

    assert result is not None
    assert result.status == RuleCheckStatus.PASS
    assert result.rule == "minimum_rate"


def test_minimum_rate_rule_fails_when_effective_rate_below_minimum():
    profile = _profile_with_minimum(2.0)

    result = evaluate_minimum_rate(profile, effective_rate=1.75)

    assert result is not None
    assert result.status == RuleCheckStatus.FAIL


def test_minimum_rate_rule_adapter_skips_when_null():
    rule = MinimumRateRule()
    context = RuleContext(
        profile=_profile_with_minimum(None),
        load=_sample_load(),
        driver_equipment=["van"],
        effective_rate=1.25,
    )

    assert rule.evaluate(context) is None


def test_minimum_rate_rule_adapter_evaluates_when_minimum_present():
    rule = MinimumRateRule()
    context = RuleContext(
        profile=_profile_with_minimum(2.0),
        load=_sample_load(),
        driver_equipment=["van"],
        effective_rate=2.0,
    )

    result = rule.evaluate(context)

    assert result is not None
    assert result.status == RuleCheckStatus.PASS
