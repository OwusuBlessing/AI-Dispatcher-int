"""Stage 4 — Equipment Matcher Agent (LLM fallback only)."""

from __future__ import annotations

from dataclasses import dataclass

from src.services.equipment_service import (
    CompatibilityMethod,
    EquipmentCompatibilityResult,
    EquipmentCompatibilityService,
)


@dataclass(frozen=True)
class LLMCompatibilityDecision:
    """LLM fallback response for ambiguous equipment compatibility."""

    compatible: bool
    reason: str


class EquipmentMatcherAgent:
    """Optional LLM fallback when deterministic compatibility is inconclusive.

    The default pipeline uses :class:`EquipmentCompatibilityService` only.
    Inject this agent later when you want semantic compatibility beyond the
    YAML compatibility matrix.
    """

    def __init__(
        self,
        *,
        equipment_service: EquipmentCompatibilityService | None = None,
        llm=None,
    ) -> None:
        self.equipment_service = equipment_service or EquipmentCompatibilityService()
        self.llm = llm

    def evaluate(
        self,
        driver_equipment: list[str],
        load_trailer: str,
    ) -> EquipmentCompatibilityResult:
        """Resolve compatibility, optionally consulting an LLM on unknown types."""
        result = self.equipment_service.evaluate(driver_equipment, load_trailer)
        if result.method != CompatibilityMethod.UNKNOWN or self.llm is None:
            return result

        llm_decision = self._ask_llm(driver_equipment, load_trailer, result.reason)
        return EquipmentCompatibilityResult(
            compatible=llm_decision.compatible,
            method=CompatibilityMethod.UNKNOWN,
            driver_equipment=tuple(driver_equipment),
            load_trailer=load_trailer,
            reason=llm_decision.reason,
        )

    def _ask_llm(
        self,
        driver_equipment: list[str],
        load_trailer: str,
        prior_reason: str,
    ) -> LLMCompatibilityDecision:
        raise NotImplementedError(
            "LLM equipment fallback is not implemented yet. "
            f"Prior deterministic result: {prior_reason}"
        )
