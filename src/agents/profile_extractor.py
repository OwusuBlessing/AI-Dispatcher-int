"""Stage 2 — Driver Profile Extraction Agent."""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar, Iterator

from src.agents.base import AgentTask, BaseAgent
from src.domain.downstream_context import profile_extractor_prompt_variables
from src.domain.schemas import (
    ConversationEvidence,
    DriverOperationalFields,
    DriverPreferences,
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
)

DEFAULT_PROMPT_FILE = "profile_extractor.md"

INFERENCE_KEYWORDS = (
    "assumed",
    "assume",
    "infer",
    "inferred",
    "inference",
    "probably",
    "likely",
    "guess",
    "maybe",
    "ambiguous",
    "unclear",
    "not explicit",
)
MAX_INFERRED_CONFIDENCE = 0.85
MAX_AMBIGUOUS_CONFIDENCE = 0.7
CITY_STATE_PATTERN = re.compile(r"^[^,]+,\s*[A-Z]{2}$")
GEOCODER_FORMAT_NOTE = "Expected geocoder format 'City, ST' (two-letter state)."

SOFT_DISLIKE_HINTS = (
    "don't like",
    "do not like",
    "dislike",
    "traffic",
    "try to stay out",
    "rather not",
    "prefer not",
    "not a hard",
    "soft",
    "depends on the rate",
    "if the rate",
    "when the rate",
    "if the pay",
    "if it's worth",
    "skip loads",
)
HARD_REFUSAL_HINTS = (
    "won't go",
    "will not go",
    "don't go",
    "do not go",
    "never go",
    "won't run",
    "will not run",
    "don't run",
    "do not run",
    "refuse to",
    "under no circumstances",
    "not going there",
    "no-go policy",
    "will not travel",
)


class ProfileExtractor(BaseAgent[DriverProfile]):
    """Infer a structured driver profile from conversation evidence."""

    prompt_file = DEFAULT_PROMPT_FILE
    agent_name = "profile_extractor"
    default_variables: ClassVar[dict[str, Any]] = profile_extractor_prompt_variables()

    def run(self, task: AgentTask) -> DriverProfile:
        profile = self.complete_structured(DriverProfile, task)
        return normalize_profile(profile)

    def extract(
        self,
        evidence: ConversationEvidence,
        *,
        variables: dict[str, Any] | None = None,
        **prompt_variables: Any,
    ) -> DriverProfile:
        """Convenience wrapper for evidence-only calls."""
        merged_variables = {**(variables or {}), **prompt_variables}
        task = AgentTask(
            content=format_evidence_input(evidence),
            variables=merged_variables,
        )
        return self.run(task)


def format_evidence_input(evidence: ConversationEvidence) -> str:
    """Serialize conversation evidence as the extractor task payload."""
    return json.dumps(evidence.model_dump(mode="json"), indent=2)


def normalize_profile(profile: DriverProfile) -> DriverProfile:
    """Apply deterministic post-processing before downstream resolution."""
    required = profile.required_fields
    required.current_latitude = None
    required.current_longitude = None
    required.home_latitude = None
    required.home_longitude = None

    required.weight_capacity = _sanitize_weight_capacity(required.weight_capacity)
    _align_equipment_types(required, profile.operational)
    required.current_location = _normalize_location_field(required.current_location)
    required.home_base = _normalize_location_field(required.home_base)
    _normalize_location_preferences(profile)

    for field_value in _iter_field_values(profile):
        _calibrate_confidence(field_value)

    return profile


def _iter_field_values(profile: DriverProfile) -> Iterator[FieldValue[Any]]:
    sections = (
        profile.required_fields,
        profile.preferences,
        profile.constraints,
        profile.operational,
    )
    for section in sections:
        for field_name in section.__class__.model_fields:
            value = getattr(section, field_name)
            if isinstance(value, FieldValue):
                yield value


def _has_explicit_numeric_weight(evidence: str | None) -> bool:
    if not evidence:
        return False
    lowered = evidence.lower()
    if not re.search(r"\d", evidence):
        return False
    vague_only = (
        "standard legal weight" in lowered
        or "legal weight" in lowered
        and not re.search(r"\d{2,}", evidence)
    )
    return not vague_only


def _sanitize_weight_capacity(
    weight: FieldValue[float] | None,
) -> FieldValue[float] | None:
    if weight is None:
        return None
    if not _has_explicit_numeric_weight(weight.evidence):
        return None
    return weight


def _align_equipment_types(
    required: DriverRequiredFields,
    operational: DriverOperationalFields,
) -> None:
    canonical = operational.canonical_equipment
    if canonical is None or not canonical.value:
        return

    required.equipment_types = FieldValue(
        value=list(canonical.value),
        confidence=canonical.confidence,
        evidence=canonical.evidence,
        reasoning_notes=(
            (canonical.reasoning_notes or "")
            + " equipment_types aligned to canonical_equipment during normalization."
        ).strip(),
    )


def _normalize_location_field(
    location: FieldValue[str] | None,
) -> FieldValue[str] | None:
    if location is None or not location.value:
        return location

    value = location.value.strip()
    if "," in value:
        city, state = value.rsplit(",", 1)
        value = f"{city.strip()}, {state.strip().upper()}"
    location.value = value

    if CITY_STATE_PATTERN.match(value):
        return location

    location.confidence = min(location.confidence, MAX_AMBIGUOUS_CONFIDENCE)
    if GEOCODER_FORMAT_NOTE not in (location.reasoning_notes or ""):
        location.reasoning_notes = (
            f"{location.reasoning_notes or ''} {GEOCODER_FORMAT_NOTE}"
        ).strip()
    return location


def _calibrate_confidence(field_value: FieldValue[Any]) -> None:
    notes = (field_value.reasoning_notes or "").lower()
    if any(keyword in notes for keyword in INFERENCE_KEYWORDS):
        field_value.confidence = min(field_value.confidence, MAX_INFERRED_CONFIDENCE)
    if "conflict" in notes or "contradict" in notes:
        field_value.confidence = min(field_value.confidence, MAX_AMBIGUOUS_CONFIDENCE)


def _field_support_text(field: FieldValue[Any]) -> str:
    return f"{field.evidence or ''} {field.reasoning_notes or ''}".lower()


def _avoid_list_is_hard_policy(field: FieldValue[list[str]]) -> bool:
    text = _field_support_text(field)
    if any(hint in text for hint in HARD_REFUSAL_HINTS):
        return True
    if any(hint in text for hint in SOFT_DISLIKE_HINTS):
        return False
    return False


def _append_soft_preference(
    preferences: DriverPreferences,
    message: str,
    *,
    evidence: str | None,
) -> None:
    existing = (
        list(preferences.soft_preferences.value)
        if preferences.soft_preferences and preferences.soft_preferences.value
        else []
    )
    if message not in existing:
        existing.append(message)
    preferences.soft_preferences = FieldValue(
        value=existing,
        confidence=0.9,
        evidence=evidence,
        reasoning_notes=(
            "Moved from avoided location fields during normalization because "
            "the driver expressed dislike, not a hard no-go policy."
        ),
    )


def _normalize_location_preferences(profile: DriverProfile) -> None:
    """Keep avoided_* only for explicit no-go policy; move dislikes to soft prefs."""
    preferences = profile.preferences
    for attr, label in (
        ("avoided_cities", "locations"),
        ("avoided_regions", "regions"),
    ):
        field: FieldValue[list[str]] | None = getattr(preferences, attr)
        if field is None or not field.value:
            continue
        if _avoid_list_is_hard_policy(field):
            continue

        places = ", ".join(field.value)
        _append_soft_preference(
            preferences,
            (
                f"Driver prefers to avoid these {label} when possible: {places}. "
                "This is not a hard no-go policy and may be overridden by rate."
            ),
            evidence=field.evidence,
        )
        setattr(preferences, attr, None)
