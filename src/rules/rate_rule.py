"""Minimum effective rate rule.

When ``minimum_rate_per_mile`` is null on the driver profile, this rule is
skipped — loads are not filtered or rejected on rate.
"""

from __future__ import annotations

from src.domain.enums import RuleCheckStatus
from src.domain.schemas import DriverProfile, RuleCheck
from src.rules.base_rule import RuleContext

RULE_NAME = "minimum_rate"


def evaluate_minimum_rate(
    profile: DriverProfile,
    effective_rate: float,
) -> RuleCheck | None:
    """Compare effective rate to the driver's stated minimum, if any."""
    minimum_field = profile.required_fields.minimum_rate_per_mile
    if minimum_field is None:
        return None

    minimum = minimum_field.value
    if effective_rate >= minimum:
        return RuleCheck(
            rule=RULE_NAME,
            status=RuleCheckStatus.PASS,
            reason=(
                f"Effective rate ${effective_rate:.2f}/mi meets minimum "
                f"${minimum:.2f}/mi"
            ),
        )

    return RuleCheck(
        rule=RULE_NAME,
        status=RuleCheckStatus.FAIL,
        reason=(
            f"Effective rate ${effective_rate:.2f}/mi below minimum "
            f"${minimum:.2f}/mi"
        ),
    )


class MinimumRateRule:
    """Rule engine adapter for minimum effective rate checks."""

    name = RULE_NAME

    def evaluate(self, context: RuleContext) -> RuleCheck | None:
        if context.effective_rate is None:
            return None

        return evaluate_minimum_rate(context.profile, context.effective_rate)
