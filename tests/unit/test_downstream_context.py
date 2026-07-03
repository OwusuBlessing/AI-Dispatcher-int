"""Unit tests for downstream extraction context."""

from src.domain.downstream_context import (
    DOWNSTREAM_REQUIRED_FIELDS,
    organizer_prompt_variables,
)


def test_organizer_prompt_variables_include_all_downstream_groups():
    variables = organizer_prompt_variables()

    assert set(variables) == {
        "downstream_agent_name",
        "downstream_extraction_guide",
        "downstream_required_fields",
        "downstream_preference_fields",
        "downstream_constraint_fields",
        "downstream_operational_fields",
    }


def test_extraction_guide_includes_capture_table():
    variables = organizer_prompt_variables()
    guide = variables["downstream_extraction_guide"]

    assert "Capture checklist" in guide or "Listen for" in guide
    assert "current location" in guide
    assert "`locations`" in guide
    assert "minimum rate per mile" in guide
    assert "`financial`" in guide


def test_profile_extractor_prompt_variables_include_field_lists():
    from src.domain.downstream_context import profile_extractor_prompt_variables

    variables = profile_extractor_prompt_variables()
    assert "required_fields_list" in variables
    assert "current location" in variables["required_fields_list"]
    assert "FieldValue" in variables["field_value_instructions"]
    assert "location_format_instructions" in variables
    assert "City, ST" in variables["location_format_instructions"]


def test_required_fields_are_documented_in_organizer_variables():
    variables = organizer_prompt_variables()
    rendered = variables["downstream_required_fields"]

    for field in DOWNSTREAM_REQUIRED_FIELDS:
        assert field in rendered
