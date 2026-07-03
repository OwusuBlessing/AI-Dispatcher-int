"""Weight capacity rule.

When ``weight_capacity`` is null on the driver profile, this rule is not used
to reject loads.
"""

from __future__ import annotations

from src.domain.enums import RuleCheckStatus
from src.domain.schemas import DriverProfile, Load, RuleCheck
from src.rules.base_rule import RuleContext

RULE_NAME = "weight"


def evaluate_weight(
    profile: DriverProfile,
    load: Load,
) -> RuleCheck | None:
    """Compare load weight to the driver's stated capacity, if any."""
    capacity_field = profile.required_fields.weight_capacity
    if capacity_field is None:
        return None

    if load.weight is None:
        return RuleCheck(
            rule=RULE_NAME,
            status=RuleCheckStatus.PASS,
            reason="Load weight not specified — capacity check not applied",
        )

    capacity = capacity_field.value
    if load.weight <= capacity:
        return RuleCheck(
            rule=RULE_NAME,
            status=RuleCheckStatus.PASS,
            reason=(
                f"Load weight {load.weight:,.0f} lbs is within capacity "
                f"{capacity:,.0f} lbs"
            ),
        )

    return RuleCheck(
        rule=RULE_NAME,
        status=RuleCheckStatus.FAIL,
        reason=(
            f"Load weight {load.weight:,.0f} lbs exceeds capacity "
            f"{capacity:,.0f} lbs"
        ),
    )


class WeightRule:
    """Rule engine adapter for weight capacity checks."""

    name = RULE_NAME

    def evaluate(self, context: RuleContext) -> RuleCheck | None:
        return evaluate_weight(context.profile, context.load)
