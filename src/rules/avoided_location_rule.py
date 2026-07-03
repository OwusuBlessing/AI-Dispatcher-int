"""Reject loads that touch a driver's explicit no-go locations."""

from __future__ import annotations

from src.domain.enums import RuleCheckStatus
from src.domain.schemas import DriverProfile, Load, RuleCheck
from src.services.location_service import find_blocked_load_stops

RULE_NAME = "location"


def evaluate_avoided_locations(profile: DriverProfile, load: Load) -> RuleCheck:
    """Fail when pickup or delivery matches a hard no-go city/region."""
    blocked = find_blocked_load_stops(profile, load)
    if not blocked:
        return RuleCheck(
            rule=RULE_NAME,
            status=RuleCheckStatus.PASS,
            reason="Load does not touch any driver no-go locations.",
        )

    details = "; ".join(
        f"{role} at {place}" for role, place in blocked
    )
    return RuleCheck(
        rule=RULE_NAME,
        status=RuleCheckStatus.FAIL,
        reason=(
            "Driver does not run freight involving "
            f"{details}. This is a stated no-go policy."
        ),
    )
