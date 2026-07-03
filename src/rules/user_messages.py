"""Human-friendly audit summaries built from rule check outcomes."""

from __future__ import annotations

from src.domain.enums import EligibilityStatus, RuleCheckStatus
from src.domain.schemas import RuleCheck

_ACCEPT_SUMMARY = (
    "Recommended — this load passes equipment, data quality, location policy, "
    "and pay checks."
)


def friendly_rule_failure(check: RuleCheck) -> str:
    """Turn a failed rule check into plain language."""
    reason = check.reason or "A requirement was not met."
    if check.rule == "missing_data":
        return f"Load data is incomplete ({reason.lower()}), so it cannot be ranked fairly."
    if check.rule == "trailer":
        return reason.replace("Trailer mismatch:", "Equipment mismatch:")
    if check.rule == "weight":
        return f"Load weight exceeds what the driver can haul ({reason.lower()})."
    if check.rule == "minimum_rate":
        return f"Pay is too low for this driver ({reason.lower()})."
    if check.rule == "location":
        return reason
    return reason


def build_eligibility_reason(
    checks: list[RuleCheck],
    eligible: EligibilityStatus,
) -> str:
    """Compose the top-level audit reason shown in reports."""
    if eligible == EligibilityStatus.ACCEPT:
        return _ACCEPT_SUMMARY

    failures = [check for check in checks if check.status == RuleCheckStatus.FAIL]
    if not failures:
        return "Not recommended — one or more checks did not pass."

    parts = [friendly_rule_failure(check) for check in failures]
    if len(parts) == 1:
        return f"Not recommended — {parts[0]}"
    return "Not recommended — " + " ".join(parts)
