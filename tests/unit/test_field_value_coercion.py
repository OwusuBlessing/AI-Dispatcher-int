"""FieldValue coercion unit tests."""

from src.domain.schemas import DriverConstraints, DriverProfile, FieldValue


def test_driver_constraints_wraps_bare_boolean():
    constraints = DriverConstraints.model_validate({"negotiates_rates": True})

    assert constraints.negotiates_rates is not None
    assert constraints.negotiates_rates.value is True
    assert constraints.negotiates_rates.confidence == 1.0


def test_driver_profile_wraps_bare_list_field():
    profile = DriverProfile.model_validate(
        {
            "required_fields": {
                "equipment_types": ["hotshot", "gooseneck"],
            }
        }
    )

    assert profile.required_fields.equipment_types is not None
    assert profile.required_fields.equipment_types.value == ["hotshot", "gooseneck"]


def test_field_value_dict_passthrough():
    constraints = DriverConstraints.model_validate(
        {
            "negotiates_rates": {
                "value": False,
                "confidence": 0.9,
                "evidence": "Driver said rates are firm.",
            }
        }
    )

    assert constraints.negotiates_rates == FieldValue(
        value=False,
        confidence=0.9,
        evidence="Driver said rates are firm.",
    )
