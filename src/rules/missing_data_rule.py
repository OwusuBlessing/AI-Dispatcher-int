"""Missing data rejection rule."""

from __future__ import annotations

from src.domain.enums import RuleCheckStatus
from src.domain.schemas import Load, RuleCheck

RULE_NAME = "missing_data"


def evaluate_missing_data(load: Load) -> RuleCheck:
    """Reject loads missing required destination or price."""
    missing_fields: list[str] = []

    if not load.destination_city or not load.destination_city.strip():
        missing_fields.append("destination")
    if load.price is None or load.price <= 0:
        missing_fields.append("price")

    if missing_fields:
        readable = " and ".join(missing_fields)
        return RuleCheck(
            rule=RULE_NAME,
            status=RuleCheckStatus.FAIL,
            reason=f"Missing required load data: {readable}",
        )

    return RuleCheck(
        rule=RULE_NAME,
        status=RuleCheckStatus.PASS,
        reason="Load has a destination and price.",
    )
