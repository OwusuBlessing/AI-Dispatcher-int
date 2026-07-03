"""Stage 4 — deterministic equipment compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from configs.load_config import EquipmentAliasConfig, get_equipment_alias_config
from src.domain.schemas import DriverProfile, ResolvedDriverProfile


class CompatibilityMethod(StrEnum):
    """How compatibility was decided."""

    EXACT = "exact"
    SYNONYM = "synonym"
    COMPATIBILITY_MATRIX = "compatibility_matrix"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EquipmentCompatibilityResult:
    """Outcome of equipment compatibility resolution."""

    compatible: bool
    method: CompatibilityMethod
    driver_equipment: tuple[str, ...]
    load_trailer: str
    reason: str


def resolve_driver_equipment(
    driver: DriverProfile | ResolvedDriverProfile,
) -> list[str]:
    """Collect canonical driver equipment types from a profile."""
    if isinstance(driver, ResolvedDriverProfile):
        if driver.canonical_equipment:
            return list(driver.canonical_equipment)

        profile = driver.profile
    else:
        profile = driver

    required = profile.required_fields
    operational = profile.operational

    if operational.canonical_equipment is not None and operational.canonical_equipment.value:
        return list(operational.canonical_equipment.value)
    if required.equipment_types is not None and required.equipment_types.value:
        return list(required.equipment_types.value)
    return []


class EquipmentCompatibilityService:
    """Resolve whether driver equipment can haul a load trailer type."""

    def __init__(self, equipment_config: EquipmentAliasConfig | None = None) -> None:
        self.equipment_config = equipment_config or get_equipment_alias_config()

    def evaluate(
        self,
        driver_equipment: list[str],
        load_trailer: str,
    ) -> EquipmentCompatibilityResult:
        canonical_load = self.equipment_config.canonicalize(load_trailer)
        if canonical_load is None:
            return EquipmentCompatibilityResult(
                compatible=False,
                method=CompatibilityMethod.UNKNOWN,
                driver_equipment=tuple(driver_equipment),
                load_trailer=load_trailer,
                reason=f"Unknown load trailer type '{load_trailer}'",
            )

        if not driver_equipment:
            return EquipmentCompatibilityResult(
                compatible=False,
                method=CompatibilityMethod.UNKNOWN,
                driver_equipment=tuple(),
                load_trailer=canonical_load,
                reason="Driver equipment is not specified",
            )

        canonical_driver_types: list[str] = []
        for equipment in driver_equipment:
            canonical_driver = self.equipment_config.canonicalize(equipment)
            if canonical_driver is None:
                return EquipmentCompatibilityResult(
                    compatible=False,
                    method=CompatibilityMethod.UNKNOWN,
                    driver_equipment=tuple(driver_equipment),
                    load_trailer=canonical_load,
                    reason=f"Unknown driver equipment type '{equipment}'",
                )
            canonical_driver_types.append(canonical_driver)

        for driver_type in canonical_driver_types:
            if driver_type == canonical_load:
                return EquipmentCompatibilityResult(
                    compatible=True,
                    method=CompatibilityMethod.EXACT,
                    driver_equipment=tuple(canonical_driver_types),
                    load_trailer=canonical_load,
                    reason=(
                        f"Exact match: driver '{driver_type}' accepts load "
                        f"'{canonical_load}'"
                    ),
                )

        for driver_type in canonical_driver_types:
            if self.equipment_config.accepts_load(driver_type, canonical_load):
                return EquipmentCompatibilityResult(
                    compatible=True,
                    method=CompatibilityMethod.COMPATIBILITY_MATRIX,
                    driver_equipment=tuple(canonical_driver_types),
                    load_trailer=canonical_load,
                    reason=(
                        f"Compatibility match: driver '{driver_type}' can haul "
                        f"load '{canonical_load}'"
                    ),
                )

        driver_label = ", ".join(sorted(set(canonical_driver_types)))
        return EquipmentCompatibilityResult(
            compatible=False,
            method=CompatibilityMethod.COMPATIBILITY_MATRIX,
            driver_equipment=tuple(canonical_driver_types),
            load_trailer=canonical_load,
            reason=(
                f"Equipment mismatch: this driver runs {driver_label}, "
                f"which cannot haul a {canonical_load} load."
            ),
        )
