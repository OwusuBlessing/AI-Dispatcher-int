"""Stages 5–10: loads → eligibility audit → distance → rate → ranking."""

from __future__ import annotations

from pathlib import Path

from src.domain.enums import EligibilityStatus
from src.domain.schemas import (
    Load,
    LoadAuditEntry,
    MatchingResult,
    ResolvedDriverProfile,
)
from src.rules.engine import RuleEngine
from src.services.distance_service import LoadDistanceMetrics, compute_load_distances
from src.services.load_normalizer import LoadNormalizationReport, load_and_normalize_loads
from src.services.ranking_service import rank_eligible_loads, rank_rejected_high_paying_loads
from src.services.rate_calculator import calculate_effective_rate


class MatchingPipeline:
    """Normalize loads, evaluate eligibility, compute rates, and rank top picks."""

    def __init__(self, *, rule_engine: RuleEngine | None = None) -> None:
        self.rule_engine = rule_engine or RuleEngine()

    def run(
        self,
        driver: ResolvedDriverProfile,
        loads: list[Load],
        *,
        top_n: int = 3,
    ) -> MatchingResult:
        """Evaluate all loads and return audits plus top-ranked eligible loads."""
        audits = [self._evaluate_load(driver, load) for load in loads]
        top_loads = rank_eligible_loads(loads, audits, top_n=top_n)
        top_rejected = rank_rejected_high_paying_loads(loads, audits, top_n=top_n)
        featured_rejected = top_rejected[0] if top_rejected else None
        return MatchingResult(
            audits=audits,
            top_loads=top_loads,
            top_rejected_loads=top_rejected,
            featured_rejected_load=featured_rejected,
        )

    def run_from_files(
        self,
        driver: ResolvedDriverProfile,
        loads_path: Path | str,
        *,
        top_n: int = 3,
    ) -> tuple[LoadNormalizationReport, MatchingResult]:
        """Load/normalize spreadsheet rows, then run the full matching pipeline."""
        report = load_and_normalize_loads(loads_path)
        result = self.run(driver, report.loads, top_n=top_n)
        return report, result

    def _evaluate_load(
        self,
        driver: ResolvedDriverProfile,
        load: Load,
    ) -> LoadAuditEntry:
        """Two-phase evaluation: eligibility rules, then distance/rate for survivors."""
        preliminary = self.rule_engine.evaluate(
            driver,
            load,
            include_rate=False,
        )
        if preliminary.eligible == EligibilityStatus.REJECT:
            return _enrich_rejected_with_metrics(driver, load, preliminary)

        metrics = compute_load_distances(driver, load)
        effective_rate = calculate_effective_rate(load.price, metrics.total_miles)
        audit = self.rule_engine.evaluate(
            driver,
            load,
            effective_rate=effective_rate,
        )
        return _enrich_audit(audit, metrics, effective_rate)


def _enrich_audit(
    audit: LoadAuditEntry,
    metrics: LoadDistanceMetrics,
    effective_rate: float | None,
) -> LoadAuditEntry:
    return audit.model_copy(
        update={
            "deadhead_to_origin": metrics.deadhead_to_origin,
            "loaded_miles": metrics.loaded_miles,
            "deadhead_home": metrics.deadhead_home,
            "total_miles": metrics.total_miles,
            "effective_rate": effective_rate,
        }
    )


def _enrich_rejected_with_metrics(
    driver: ResolvedDriverProfile,
    load: Load,
    audit: LoadAuditEntry,
) -> LoadAuditEntry:
    """Attach distance/rate context to rejected loads when coordinates allow."""
    if load.price is None:
        return audit
    metrics = compute_load_distances(driver, load)
    effective_rate = calculate_effective_rate(load.price, metrics.total_miles)
    return _enrich_audit(audit, metrics, effective_rate)
