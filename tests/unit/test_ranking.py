"""Ranking service unit tests."""

from __future__ import annotations

from src.domain.enums import EligibilityStatus, RuleCheckStatus
from src.domain.schemas import Load, LoadAuditEntry
from src.services.ranking_service import rank_eligible_loads, rank_rejected_high_paying_loads


def _audit(
    load_id: str,
    *,
    eligible: EligibilityStatus,
    effective_rate: float | None,
) -> LoadAuditEntry:
    return LoadAuditEntry(
        load_id=load_id,
        trailer_check=RuleCheckStatus.PASS,
        weight_check=RuleCheckStatus.PASS,
        missing_data_check=RuleCheckStatus.PASS,
        eligible=eligible,
        reason="test",
        effective_rate=effective_rate,
    )


def _load(load_id: str) -> Load:
    return Load(
        load_id=load_id,
        origin_city="A",
        destination_city="B",
        trailer="hotshot",
        price=1000.0,
    )


def test_rank_eligible_loads_orders_by_effective_rate_desc():
    loads = [_load("L02"), _load("L03"), _load("L08")]
    audits = [
        _audit("L02", eligible=EligibilityStatus.ACCEPT, effective_rate=2.5),
        _audit("L03", eligible=EligibilityStatus.ACCEPT, effective_rate=3.1),
        _audit("L08", eligible=EligibilityStatus.ACCEPT, effective_rate=2.8),
    ]

    ranked = rank_eligible_loads(loads, audits, top_n=3)

    assert [item.load.load_id for item in ranked] == ["L03", "L08", "L02"]
    assert [item.rank for item in ranked] == [1, 2, 3]


def test_rank_eligible_loads_skips_rejected_and_missing_rate():
    loads = [_load("L01"), _load("L02")]
    audits = [
        _audit("L01", eligible=EligibilityStatus.REJECT, effective_rate=5.0),
        _audit("L02", eligible=EligibilityStatus.ACCEPT, effective_rate=None),
    ]

    ranked = rank_eligible_loads(loads, audits, top_n=3)

    assert ranked == []


def test_rank_rejected_high_paying_loads_orders_by_price_desc():
    loads = [
        Load(
            load_id="L01",
            origin_city="A",
            destination_city="B",
            trailer="van",
            price=620.0,
        ),
        Load(
            load_id="L04",
            origin_city="C",
            destination_city="D",
            trailer="van",
            price=1500.0,
        ),
        Load(
            load_id="L07",
            origin_city="E",
            destination_city="F",
            trailer="hotshot",
            price=1100.0,
        ),
    ]
    audits = [
        _audit("L01", eligible=EligibilityStatus.REJECT, effective_rate=None),
        _audit("L04", eligible=EligibilityStatus.REJECT, effective_rate=None),
        _audit("L07", eligible=EligibilityStatus.REJECT, effective_rate=None),
    ]

    ranked = rank_rejected_high_paying_loads(loads, audits, top_n=3)

    assert [item.load.load_id for item in ranked] == ["L04", "L07", "L01"]
    assert [item.rank for item in ranked] == [1, 2, 3]


def test_rank_rejected_high_paying_loads_skips_missing_price():
    loads = [
        Load(
            load_id="L06",
            origin_city="A",
            destination_city="B",
            trailer="van",
            price=None,
        )
    ]
    audits = [_audit("L06", eligible=EligibilityStatus.REJECT, effective_rate=None)]

    ranked = rank_rejected_high_paying_loads(loads, audits, top_n=3)

    assert ranked == []
