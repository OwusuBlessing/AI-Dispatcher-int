"""Equipment compatibility unit tests."""

from configs.load_config import EquipmentAliasConfig
from src.services.equipment_service import (
    EquipmentCompatibilityService,
    resolve_driver_equipment,
)
from src.domain.schemas import (
    DriverOperationalFields,
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
    ResolvedDriverProfile,
)


def test_hotshot_driver_can_haul_gooseneck_load():
    service = EquipmentCompatibilityService()
    result = service.evaluate(["hotshot"], "gooseneck")

    assert result.compatible is True
    assert result.method.value == "compatibility_matrix"


def test_van_driver_cannot_haul_hotshot_load():
    service = EquipmentCompatibilityService()
    result = service.evaluate(["van"], "hotshot")

    assert result.compatible is False


def test_exact_match_when_driver_and_load_types_match():
    service = EquipmentCompatibilityService()
    result = service.evaluate(["flatbed"], "flatbed")

    assert result.compatible is True
    assert result.method.value == "exact"


def test_resolve_driver_equipment_prefers_resolved_canonical_list():
    profile = ResolvedDriverProfile(
        profile=DriverProfile(),
        canonical_equipment=["hotshot", "gooseneck"],
    )

    assert resolve_driver_equipment(profile) == ["hotshot", "gooseneck"]


def test_resolve_driver_equipment_falls_back_to_profile_fields():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            equipment_types=FieldValue(value=["van"]),
        ),
        operational=DriverOperationalFields(),
    )

    assert resolve_driver_equipment(profile) == ["van"]


def test_custom_compatibility_matrix_from_config():
    config = EquipmentAliasConfig(
        alias_to_canonical={"van": "van", "reefer": "reefer"},
        compatibility={"van": frozenset({"van", "reefer"})},
    )
    service = EquipmentCompatibilityService(equipment_config=config)

    assert service.evaluate(["van"], "reefer").compatible is True
