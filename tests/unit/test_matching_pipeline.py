"""Rule engine and matching pipeline unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.enums import EligibilityStatus, RuleCheckStatus
from src.domain.schemas import (
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
    Load,
    ResolvedDriverProfile,
)
from src.pipelines.matching_pipeline import MatchingPipeline
from src.rules.engine import RuleEngine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOADS_FILE = PROJECT_ROOT / "data/raw/loads.xlsx"
RESOLVED_PROFILE_FILE = (
    PROJECT_ROOT / "src/outputs/resolved_driver_profile_conversation.json"
)


@pytest.fixture
def hotshot_driver() -> ResolvedDriverProfile:
    return ResolvedDriverProfile(
        profile=DriverProfile(
            required_fields=DriverRequiredFields(
                minimum_rate_per_mile=FieldValue(value=2.0),
                weight_capacity=FieldValue(value=15000.0),
            ),
        ),
        canonical_equipment=["hotshot", "gooseneck"],
    )


def test_rule_engine_rejects_missing_destination(hotshot_driver):
    load = Load(
        load_id="L07",
        origin_city="Tulsa",
        destination_city="",
        trailer="hotshot",
        price=1100.0,
        weight=13400.0,
    )

    audit = RuleEngine().evaluate(hotshot_driver, load)

    assert audit.eligible == EligibilityStatus.REJECT
    assert audit.missing_data_check == RuleCheckStatus.FAIL


def test_rule_engine_rejects_hard_no_go_location(hotshot_driver):
    hotshot_driver.profile.preferences.avoided_cities = FieldValue(
        value=["Houston, TX"],
        evidence="I do not run loads involving Houston at all.",
    )
    load = Load(
        load_id="L02",
        origin_city="Houston",
        destination_city="Laredo",
        trailer="hotshot",
        price=1600.0,
        weight=11500.0,
    )

    audit = RuleEngine().evaluate(hotshot_driver, load)

    assert audit.eligible == EligibilityStatus.REJECT
    assert audit.location_check == RuleCheckStatus.FAIL
    assert "Houston" in audit.reason


def test_rule_engine_accepts_compatible_hotshot_load(hotshot_driver):
    load = Load(
        load_id="L02",
        origin_city="Houston",
        destination_city="Laredo",
        trailer="hotshot",
        price=1600.0,
        weight=11500.0,
    )

    audit = RuleEngine().evaluate(hotshot_driver, load)

    assert audit.eligible == EligibilityStatus.ACCEPT
    assert audit.trailer_check == RuleCheckStatus.PASS


def test_rule_engine_rejects_van_load_for_hotshot_driver(hotshot_driver):
    load = Load(
        load_id="L01",
        origin_city="Fort Worth",
        destination_city="Oklahoma City",
        trailer="van",
        price=620.0,
        weight=42000.0,
    )

    audit = RuleEngine().evaluate(hotshot_driver, load)

    assert audit.eligible == EligibilityStatus.REJECT
    assert audit.trailer_check == RuleCheckStatus.FAIL


def test_rule_engine_rejects_overweight_load(hotshot_driver):
    load = Load(
        load_id="L01",
        origin_city="Fort Worth",
        destination_city="Oklahoma City",
        trailer="hotshot",
        price=1600.0,
        weight=20000.0,
    )

    audit = RuleEngine().evaluate(hotshot_driver, load)

    assert audit.eligible == EligibilityStatus.REJECT
    assert audit.weight_check == RuleCheckStatus.FAIL


def test_rule_engine_skips_rate_check_without_effective_rate(hotshot_driver):
    load = Load(
        load_id="L02",
        origin_city="Houston",
        destination_city="Laredo",
        trailer="hotshot",
        price=1600.0,
    )

    audit = RuleEngine().evaluate(hotshot_driver, load)

    assert audit.rate_check is None


def test_rule_engine_applies_minimum_rate_when_effective_rate_provided(hotshot_driver):
    load = Load(
        load_id="L02",
        origin_city="Houston",
        destination_city="Laredo",
        trailer="hotshot",
        price=1600.0,
    )

    audit = RuleEngine().evaluate(hotshot_driver, load, effective_rate=1.5)

    assert audit.rate_check == RuleCheckStatus.FAIL


@pytest.mark.skipif(
    not LOADS_FILE.exists() or not RESOLVED_PROFILE_FILE.exists(),
    reason="assignment artifacts missing",
)
def test_matching_pipeline_on_assignment_files():
    driver = ResolvedDriverProfile.model_validate_json(
        RESOLVED_PROFILE_FILE.read_text(encoding="utf-8")
    )
    pipeline = MatchingPipeline()

    report, result = pipeline.run_from_files(driver, LOADS_FILE)

    assert len(report.loads) == 8
    assert len(result.audits) == 8

    eligible = [audit for audit in result.audits if audit.eligible == EligibilityStatus.ACCEPT]
    rejected = [audit for audit in result.audits if audit.eligible == EligibilityStatus.REJECT]

    assert len(eligible) + len(rejected) == 8
    assert any(audit.load_id == "L07" for audit in rejected)
    assert any(audit.load_id == "L06" for audit in rejected)

    for audit in eligible:
        assert audit.total_miles is not None
        assert audit.effective_rate is not None

    assert len(result.top_loads) <= 3
    if result.top_loads:
        rates = [item.audit.effective_rate for item in result.top_loads]
        assert rates == sorted(rates, reverse=True)

    assert len(result.top_rejected_loads) <= 3
    if result.top_rejected_loads:
        prices = [item.load.price for item in result.top_rejected_loads]
        assert prices == sorted(prices, reverse=True)
        assert result.featured_rejected_load is not None
        assert result.featured_rejected_load.load.load_id == result.top_rejected_loads[0].load.load_id
        assert result.featured_rejected_load.rank == 1
