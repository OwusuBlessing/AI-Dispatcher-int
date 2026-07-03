"""Unit tests for the profile extractor agent."""

from unittest.mock import MagicMock

import pytest

from src.agents.base import AgentTask
from src.agents.profile_extractor import (
    ProfileExtractor,
    format_evidence_input,
    normalize_profile,
)
from src.domain.downstream_context import profile_extractor_prompt_variables
from src.domain.enums import EvidenceCategory, Speaker
from src.domain.schemas import (
    ConversationEvidence,
    DriverPreferences,
    DriverProfile,
    DriverOperationalFields,
    DriverRequiredFields,
    EvidenceItem,
    FieldValue,
)
from src.utils.prompts import PromptTemplate

SAMPLE_EVIDENCE = ConversationEvidence(
    locations=[
        EvidenceItem(
            speaker=Speaker.DRIVER,
            quote="I'm sitting in Dallas right now.",
            category=EvidenceCategory.LOCATION,
        )
    ],
    financial=[
        EvidenceItem(
            speaker=Speaker.DRIVER,
            quote="As long as it's above $2 a mile I'm good.",
            category=EvidenceCategory.FINANCIAL,
        )
    ],
    equipment=[
        EvidenceItem(
            speaker=Speaker.DRIVER,
            quote="I've got a 53-foot dry van. I can haul up to about 45,000 pounds.",
            category=EvidenceCategory.EQUIPMENT,
        )
    ],
)

INLINE_PROMPT = """Extract profile.

Required:
{{required_fields_list}}

{{field_value_instructions}}
"""

DEFAULT_VARS = profile_extractor_prompt_variables()


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def extractor(mock_llm):
    return ProfileExtractor(
        llm=mock_llm,
        prompt_template=PromptTemplate.from_string(INLINE_PROMPT),
        default_variables=DEFAULT_VARS,
    )


def test_format_evidence_input_serializes_json():
    payload = format_evidence_input(SAMPLE_EVIDENCE)
    assert '"locations"' in payload
    assert "Dallas" in payload


def test_run_calls_structured_completion_with_evidence_json(extractor, mock_llm):
    expected = DriverProfile(
        required_fields=DriverRequiredFields(
            current_location=FieldValue(
                value="Dallas, TX",
                confidence=0.9,
                evidence="I'm sitting in Dallas right now.",
            ),
            minimum_rate_per_mile=FieldValue(value=2.0, confidence=0.95),
        )
    )
    mock_llm.complete_structured.return_value = expected

    result = extractor.extract(SAMPLE_EVIDENCE)

    assert result.required_fields.current_location is not None
    assert result.required_fields.current_location.value == "Dallas, TX"
    kwargs = mock_llm.complete_structured.call_args.kwargs
    assert "Dallas" in kwargs["prompt"]
    assert "minimum rate per mile" in kwargs["system_prompt"]


def test_run_supports_runtime_prompt_variables(extractor, mock_llm):
    mock_llm.complete_structured.return_value = DriverProfile()
    task = AgentTask(
        content=format_evidence_input(SAMPLE_EVIDENCE),
        variables={"required_fields_list": "- custom field"},
    )

    extractor.run(task)

    assert "custom field" in mock_llm.complete_structured.call_args.kwargs["system_prompt"]


def test_normalize_profile_clears_coordinates():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            current_location=FieldValue(value="Dallas, TX"),
            current_latitude=FieldValue(value=32.0),
            home_longitude=FieldValue(value=-96.0),
        )
    )

    normalized = normalize_profile(profile)

    assert normalized.required_fields.current_latitude is None
    assert normalized.required_fields.home_longitude is None
    assert normalized.required_fields.current_location is not None


def test_normalize_profile_clears_weight_without_explicit_number():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            weight_capacity=FieldValue(
                value=45000.0,
                confidence=0.8,
                evidence="Standard legal weight, you know how it is",
                reasoning_notes="Assumed standard legal weight.",
            )
        )
    )

    normalized = normalize_profile(profile)

    assert normalized.required_fields.weight_capacity is None


def test_normalize_profile_keeps_weight_with_explicit_number():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            weight_capacity=FieldValue(
                value=45000.0,
                confidence=1.0,
                evidence="I can haul up to about 45,000 pounds",
            )
        )
    )

    normalized = normalize_profile(profile)

    assert normalized.required_fields.weight_capacity is not None
    assert normalized.required_fields.weight_capacity.value == 45000.0


def test_normalize_profile_aligns_equipment_types_to_canonical():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            equipment_types=FieldValue(value=["flatbed", "dry"]),
        ),
        operational=DriverOperationalFields(
            canonical_equipment=FieldValue(
                value=["flatbed"],
                confidence=1.0,
                evidence="48 foot flatbed",
            )
        ),
    )

    normalized = normalize_profile(profile)

    assert normalized.required_fields.equipment_types is not None
    assert normalized.required_fields.equipment_types.value == ["flatbed"]


def test_normalize_profile_caps_confidence_on_inferred_notes():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            home_base=FieldValue(
                value="Houston area",
                confidence=1.0,
                reasoning_notes="Inferred from usually in that area.",
            )
        )
    )

    normalized = normalize_profile(profile)

    assert normalized.required_fields.home_base is not None
    assert normalized.required_fields.home_base.confidence <= 0.7
    assert "City, ST" in (normalized.required_fields.home_base.reasoning_notes or "")


def test_normalize_profile_uppercases_state_in_city_st_format():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            current_location=FieldValue(value="dallas, tx", confidence=0.9),
        )
    )

    normalized = normalize_profile(profile)

    assert normalized.required_fields.current_location is not None
    assert normalized.required_fields.current_location.value == "dallas, TX"


def test_normalize_profile_preserves_valid_city_st_format():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            home_base=FieldValue(value="Albuquerque, NM", confidence=0.95),
        )
    )

    normalized = normalize_profile(profile)

    assert normalized.required_fields.home_base is not None
    assert normalized.required_fields.home_base.value == "Albuquerque, NM"
    assert normalized.required_fields.home_base.confidence == 0.95


def test_normalize_profile_moves_soft_avoids_to_soft_preferences():
    profile = DriverProfile(
        preferences=DriverPreferences(
            avoided_cities=FieldValue(
                value=["Example City, TX"],
                evidence="I don't like running through Example City because of traffic.",
                reasoning_notes="Soft dislike due to traffic, not a hard refusal.",
            ),
        ),
    )

    normalized = normalize_profile(profile)

    assert normalized.preferences.avoided_cities is None
    assert normalized.preferences.soft_preferences is not None
    assert any(
        "prefers to avoid" in item.lower()
        for item in normalized.preferences.soft_preferences.value
    )


def test_normalize_profile_keeps_hard_avoided_cities():
    profile = DriverProfile(
        preferences=DriverPreferences(
            avoided_cities=FieldValue(
                value=["Example City, TX"],
                evidence="I will not go to Example City at all.",
                reasoning_notes="Explicit no-go policy.",
            ),
        ),
    )

    normalized = normalize_profile(profile)

    assert normalized.preferences.avoided_cities is not None
    assert normalized.preferences.avoided_cities.value == ["Example City, TX"]


def test_extract_rejects_empty_task_content(extractor):
    with pytest.raises(ValueError, match="task.content must not be empty"):
        extractor.run(AgentTask(content="   "))
