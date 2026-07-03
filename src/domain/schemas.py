"""Pydantic schemas for pipeline I/O."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.enums import (
    EligibilityStatus,
    EvidenceCategory,
    EvidenceClassification,
    RuleCheckStatus,
    Speaker,
)
from src.domain.evidence_normalizers import normalize_speaker
from src.domain.field_value_coercion import coerce_section_field_values

T = TypeVar("T")


class EvidenceItem(BaseModel):
    """Single organized quote from the conversation organizer."""

    speaker: Speaker = Speaker.UNKNOWN
    quote: str
    category: EvidenceCategory
    classification: EvidenceClassification = EvidenceClassification.EXPLICIT
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("speaker", mode="before")
    @classmethod
    def _coerce_speaker(cls, value: Speaker | str | None) -> Speaker:
        return normalize_speaker(value)


class ConversationEvidence(BaseModel):
    """Stage 1 output — organized semantic evidence, not a final profile."""

    locations: list[EvidenceItem] = Field(default_factory=list)
    equipment: list[EvidenceItem] = Field(default_factory=list)
    constraints: list[EvidenceItem] = Field(default_factory=list)
    preferences: list[EvidenceItem] = Field(default_factory=list)
    financial: list[EvidenceItem] = Field(default_factory=list)
    operations: list[EvidenceItem] = Field(default_factory=list)
    availability: list[EvidenceItem] = Field(default_factory=list)
    other: list[EvidenceItem] = Field(default_factory=list)


class FieldValue(BaseModel, Generic[T]):
    """A profile field with provenance metadata."""

    value: T
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: str | None = None
    reasoning_notes: str | None = None


class LocationRef(BaseModel):
    """Structured location before geocoding."""

    city: str
    state: str | None = None
    country: str = "USA"


class ResolvedLocation(LocationRef):
    """Location with coordinates after geocoding."""

    lat: float
    lon: float


class DriverRequiredFields(BaseModel):
    """Part A required assignment fields.

    ``minimum_rate_per_mile`` and ``weight_capacity`` may be null when the
    driver did not state them. Downstream rules must skip filtering on null
    fields rather than assume defaults.
    """

    current_location: FieldValue[str] | None = None
    current_latitude: FieldValue[float] | None = None
    current_longitude: FieldValue[float] | None = None
    home_base: FieldValue[str] | None = None
    home_latitude: FieldValue[float] | None = None
    home_longitude: FieldValue[float] | None = None
    minimum_rate_per_mile: FieldValue[float] | None = None
    equipment_types: FieldValue[list[str]] | None = None
    weight_capacity: FieldValue[float] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_field_values(cls, data: Any) -> Any:
        return coerce_section_field_values(data, cls)


class DriverPreferences(BaseModel):
    """Soft preferences and explicit no-go location policy.

    ``avoided_cities`` / ``avoided_regions`` are only for places the driver
  will not run at all. Dislikes that depend on rate belong in
    ``soft_preferences``.
    """

    preferred_regions: FieldValue[list[str]] | None = None
    avoided_regions: FieldValue[list[str]] | None = None
    preferred_cities: FieldValue[list[str]] | None = None
    avoided_cities: FieldValue[list[str]] | None = None
    preferred_lanes: FieldValue[list[str]] | None = None
    soft_preferences: FieldValue[list[str]] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_field_values(cls, data: Any) -> Any:
        return coerce_section_field_values(data, cls)


class DriverConstraints(BaseModel):
    """Hard constraints on acceptable loads."""

    hard_constraints: FieldValue[list[str]] | None = None
    requires_factorable_brokers: FieldValue[bool] | None = None
    negotiates_rates: FieldValue[bool] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_field_values(cls, data: Any) -> Any:
        return coerce_section_field_values(data, cls)


class DriverOperationalFields(BaseModel):
    """Equipment and work-related internal fields."""

    raw_equipment_description: FieldValue[str] | None = None
    canonical_equipment: FieldValue[list[str]] | None = None
    days_per_week: FieldValue[int] | None = None
    availability: FieldValue[str] | None = None
    schedule_flexibility: FieldValue[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_field_values(cls, data: Any) -> Any:
        return coerce_section_field_values(data, cls)


class DriverProfile(BaseModel):
    """Stage 2 output — structured driver profile with evidence."""

    required_fields: DriverRequiredFields = Field(default_factory=DriverRequiredFields)
    preferences: DriverPreferences = Field(default_factory=DriverPreferences)
    constraints: DriverConstraints = Field(default_factory=DriverConstraints)
    operational: DriverOperationalFields = Field(default_factory=DriverOperationalFields)
    metadata: dict[str, str] = Field(default_factory=dict)


class ResolvedDriverProfile(BaseModel):
    """Driver profile after location and equipment resolution."""

    profile: DriverProfile
    current_location: ResolvedLocation | None = None
    home_base: ResolvedLocation | None = None
    canonical_equipment: list[str] = Field(default_factory=list)


class Load(BaseModel):
    """Normalized freight load from the Excel dataset."""

    load_id: str
    origin_city: str
    origin_state: str | None = None
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    destination_city: str
    destination_state: str | None = None
    destination_latitude: float | None = None
    destination_longitude: float | None = None
    trailer: str
    price: float | None = None
    weight: float | None = None
    loaded_miles: float | None = None


class RuleCheck(BaseModel):
    """Outcome of one rule applied to a load."""

    rule: str
    status: RuleCheckStatus
    reason: str | None = None


class LoadAuditEntry(BaseModel):
    """Per-load audit trail row."""

    load_id: str
    trailer_check: RuleCheckStatus
    weight_check: RuleCheckStatus
    missing_data_check: RuleCheckStatus
    location_check: RuleCheckStatus | None = None
    rate_check: RuleCheckStatus | None = None
    eligible: EligibilityStatus
    reason: str
    deadhead_to_origin: float | None = None
    loaded_miles: float | None = None
    deadhead_home: float | None = None
    total_miles: float | None = None
    effective_rate: float | None = None
    rule_checks: list[RuleCheck] = Field(default_factory=list)


class RankedLoad(BaseModel):
    """Eligible load with distance and rate metrics for ranking."""

    load: Load
    audit: LoadAuditEntry
    rank: int | None = None


class MatchingResult(BaseModel):
    """Full matching pipeline output: audits, top picks, and rejected highlights."""

    audits: list[LoadAuditEntry]
    top_loads: list[RankedLoad] = Field(default_factory=list)
    top_rejected_loads: list[RankedLoad] = Field(default_factory=list)
    featured_rejected_load: RankedLoad | None = None
