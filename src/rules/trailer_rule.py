"""Equipment / trailer compatibility rule."""

from __future__ import annotations

from src.domain.enums import RuleCheckStatus
from src.domain.schemas import RuleCheck
from src.rules.base_rule import RuleContext
from src.services.equipment_service import EquipmentCompatibilityService

RULE_NAME = "trailer"


def evaluate_trailer(
    driver_equipment: list[str],
    load_trailer: str,
    *,
    equipment_service: EquipmentCompatibilityService | None = None,
) -> RuleCheck:
    """Check whether the driver's equipment can haul the load trailer type."""
    service = equipment_service or EquipmentCompatibilityService()
    result = service.evaluate(driver_equipment, load_trailer)
    status = RuleCheckStatus.PASS if result.compatible else RuleCheckStatus.FAIL
    return RuleCheck(rule=RULE_NAME, status=status, reason=result.reason)


class TrailerRule:
    """Rule engine adapter for trailer compatibility checks."""

    name = RULE_NAME

    def __init__(
        self,
        equipment_service: EquipmentCompatibilityService | None = None,
    ) -> None:
        self.equipment_service = equipment_service or EquipmentCompatibilityService()

    def evaluate(self, context: RuleContext) -> RuleCheck:
        return evaluate_trailer(
            context.driver_equipment,
            context.load.trailer,
            equipment_service=self.equipment_service,
        )
