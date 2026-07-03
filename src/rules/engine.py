"""Stage 6 — Business rule engine."""

from __future__ import annotations

from configs.rules_config import RulesConfig, get_rules_config
from src.domain.enums import EligibilityStatus, RuleCheckStatus
from src.domain.schemas import DriverProfile, Load, LoadAuditEntry, ResolvedDriverProfile, RuleCheck
from src.rules.avoided_location_rule import evaluate_avoided_locations
from src.rules.base_rule import RuleContext
from src.rules.missing_data_rule import evaluate_missing_data
from src.rules.rate_rule import evaluate_minimum_rate
from src.rules.trailer_rule import TrailerRule
from src.rules.user_messages import build_eligibility_reason
from src.rules.weight_rule import evaluate_weight
from src.services.equipment_service import resolve_driver_equipment


class RuleEngine:
    """Apply deterministic eligibility rules to a driver/load pair."""

    def __init__(
        self,
        *,
        rules_config: RulesConfig | None = None,
        trailer_rule: TrailerRule | None = None,
    ) -> None:
        self.rules_config = rules_config or get_rules_config()
        self.trailer_rule = trailer_rule or TrailerRule()

    def evaluate(
        self,
        driver: DriverProfile | ResolvedDriverProfile,
        load: Load,
        *,
        effective_rate: float | None = None,
        driver_equipment: list[str] | None = None,
        include_rate: bool = True,
    ) -> LoadAuditEntry:
        profile = driver.profile if isinstance(driver, ResolvedDriverProfile) else driver
        equipment = driver_equipment or resolve_driver_equipment(driver)

        context = RuleContext(
            profile=profile,
            load=load,
            driver_equipment=equipment,
            effective_rate=effective_rate,
        )

        checks: list[RuleCheck] = []
        failure_reasons: list[str] = []

        missing_check = self._evaluate_missing_data(context)
        checks.append(missing_check)
        if missing_check.status == RuleCheckStatus.FAIL:
            failure_reasons.append(missing_check.reason or "Missing required data")

        trailer_check = self._evaluate_trailer(context)
        checks.append(trailer_check)
        if trailer_check.status == RuleCheckStatus.FAIL:
            failure_reasons.append(trailer_check.reason or "Trailer mismatch")

        location_check = self._evaluate_location(context)
        if location_check is not None:
            checks.append(location_check)
            if location_check.status == RuleCheckStatus.FAIL:
                failure_reasons.append(location_check.reason or "Location policy conflict")

        weight_check = self._evaluate_weight(context)
        if weight_check is not None:
            checks.append(weight_check)
            if weight_check.status == RuleCheckStatus.FAIL:
                failure_reasons.append(weight_check.reason or "Weight exceeds capacity")

        rate_check = None
        if include_rate:
            rate_check = self._evaluate_rate(context)
            if rate_check is not None:
                checks.append(rate_check)
                if rate_check.status == RuleCheckStatus.FAIL:
                    failure_reasons.append(rate_check.reason or "Rate below minimum")

        eligible = (
            EligibilityStatus.ACCEPT
            if not failure_reasons
            else EligibilityStatus.REJECT
        )
        reason = build_eligibility_reason(checks, eligible)

        return LoadAuditEntry(
            load_id=load.load_id,
            trailer_check=trailer_check.status,
            weight_check=(
                weight_check.status
                if weight_check is not None
                else RuleCheckStatus.PASS
            ),
            missing_data_check=missing_check.status,
            location_check=(
                location_check.status
                if location_check is not None
                else RuleCheckStatus.PASS
            ),
            rate_check=rate_check.status if rate_check is not None else None,
            eligible=eligible,
            reason=reason,
            effective_rate=effective_rate,
            rule_checks=checks,
        )

    def evaluate_all(
        self,
        driver: DriverProfile | ResolvedDriverProfile,
        loads: list[Load],
        *,
        effective_rates: dict[str, float] | None = None,
        driver_equipment: list[str] | None = None,
    ) -> list[LoadAuditEntry]:
        """Evaluate every load and return audit entries in the same order."""
        rates = effective_rates or {}
        return [
            self.evaluate(
                driver,
                load,
                effective_rate=rates.get(load.load_id),
                driver_equipment=driver_equipment,
            )
            for load in loads
        ]

    def _evaluate_missing_data(self, context: RuleContext) -> RuleCheck:
        if not self.rules_config.missing_data_enabled:
            return RuleCheck(
                rule="missing_data",
                status=RuleCheckStatus.PASS,
                reason="Missing-data rule disabled",
            )
        return evaluate_missing_data(context.load)

    def _evaluate_trailer(self, context: RuleContext) -> RuleCheck:
        if not self.rules_config.equipment_enabled:
            return RuleCheck(
                rule="trailer",
                status=RuleCheckStatus.PASS,
                reason="Equipment rule disabled",
            )
        return self.trailer_rule.evaluate(context)

    def _evaluate_location(self, context: RuleContext) -> RuleCheck | None:
        if not self.rules_config.location_enabled:
            return None
        return evaluate_avoided_locations(context.profile, context.load)

    def _evaluate_weight(self, context: RuleContext) -> RuleCheck | None:
        if not self.rules_config.weight_enabled:
            return None
        return evaluate_weight(context.profile, context.load)

    def _evaluate_rate(self, context: RuleContext) -> RuleCheck | None:
        if not self.rules_config.rate_enabled:
            return None
        if context.effective_rate is None:
            return None
        if (
            self.rules_config.skip_rate_when_minimum_null
            and context.profile.required_fields.minimum_rate_per_mile is None
        ):
            return None
        return evaluate_minimum_rate(context.profile, context.effective_rate)
