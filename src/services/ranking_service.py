"""Stage 10 — Ranking engine."""

from __future__ import annotations

from src.domain.enums import EligibilityStatus
from src.domain.schemas import Load, LoadAuditEntry, RankedLoad


def rank_eligible_loads(
    loads: list[Load],
    audits: list[LoadAuditEntry],
    *,
    top_n: int = 3,
) -> list[RankedLoad]:
    """Rank eligible loads by effective rate (descending) and assign ranks 1..top_n."""
    audit_by_id = {audit.load_id: audit for audit in audits}
    candidates: list[RankedLoad] = []

    for load in loads:
        audit = audit_by_id.get(load.load_id)
        if audit is None:
            continue
        if audit.eligible != EligibilityStatus.ACCEPT:
            continue
        if audit.effective_rate is None:
            continue
        candidates.append(RankedLoad(load=load, audit=audit))

    candidates.sort(key=lambda item: item.audit.effective_rate or 0.0, reverse=True)

    ranked: list[RankedLoad] = []
    for index, candidate in enumerate(candidates[:top_n], start=1):
        ranked.append(candidate.model_copy(update={"rank": index}))
    return ranked


def rank_rejected_high_paying_loads(
    loads: list[Load],
    audits: list[LoadAuditEntry],
    *,
    top_n: int = 3,
) -> list[RankedLoad]:
    """Rank rejected loads by flat price (descending) for the audit highlight table."""
    audit_by_id = {audit.load_id: audit for audit in audits}
    candidates: list[RankedLoad] = []

    for load in loads:
        audit = audit_by_id.get(load.load_id)
        if audit is None:
            continue
        if audit.eligible != EligibilityStatus.REJECT:
            continue
        if load.price is None:
            continue
        candidates.append(RankedLoad(load=load, audit=audit))

    candidates.sort(key=lambda item: item.load.price or 0.0, reverse=True)

    ranked: list[RankedLoad] = []
    for index, candidate in enumerate(candidates[:top_n], start=1):
        ranked.append(candidate.model_copy(update={"rank": index}))
    return ranked
