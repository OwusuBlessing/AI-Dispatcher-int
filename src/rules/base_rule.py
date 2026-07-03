"""Base rule interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.schemas import DriverProfile, Load, RuleCheck


@dataclass
class RuleContext:
    """Inputs shared by deterministic load-matching rules."""

    profile: DriverProfile
    load: Load
    driver_equipment: list[str]
    effective_rate: float | None = None


class BaseRule(ABC):
    """A single business rule that may return no result when it does not apply."""

    name: str

    @abstractmethod
    def evaluate(self, context: RuleContext) -> RuleCheck | None:
        """Return a check result, or None when this rule should be skipped."""
