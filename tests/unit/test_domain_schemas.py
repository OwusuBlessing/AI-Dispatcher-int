"""Unit tests for domain schemas."""

import pytest
from pydantic import ValidationError

from src.domain.enums import (
    EligibilityStatus,
    EvidenceCategory,
    EvidenceClassification,
    RuleCheckStatus,
    Speaker,
)
from src.domain.schemas import (
    ConversationEvidence,
    DriverProfile,
    DriverRequiredFields,
    EvidenceItem,
    FieldValue,
    Load,
    LoadAuditEntry,
    LocationRef,
    RankedLoad,
    ResolvedDriverProfile,
    ResolvedLocation,
    RuleCheck,
)


def test_evidence_item_accepts_valid_payload():
    item = EvidenceItem(
        speaker=Speaker.DRIVER,
        quote="I'm in Dallas.",
        category=EvidenceCategory.LOCATION,
        classification=EvidenceClassification.EXPLICIT,
        confidence=0.95,
    )
    assert item.quote == "I'm in Dallas."
    assert item.category == EvidenceCategory.LOCATION


def test_evidence_item_normalizes_dispatch_speaker_alias():
    item = EvidenceItem(
        speaker="Dispatch",
        quote="Where are you headed?",
        category=EvidenceCategory.OPERATIONS,
    )
    assert item.speaker == Speaker.DISPATCHER


def test_conversation_evidence_accepts_dispatch_speaker_alias():
    evidence = ConversationEvidence.model_validate(
        {
            "operations": [
                {
                    "speaker": "Dispatch",
                    "quote": "Any loads for tomorrow?",
                    "category": "Operations",
                }
            ]
        }
    )
    assert evidence.operations[0].speaker == Speaker.DISPATCHER


def test_evidence_item_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        EvidenceItem(
            quote="test",
            category=EvidenceCategory.OTHER,
            confidence=1.5,
        )


def test_conversation_evidence_groups_items_by_bucket():
    evidence = ConversationEvidence(
        locations=[
            EvidenceItem(
                speaker=Speaker.DRIVER,
                quote="I'm in Dallas.",
                category=EvidenceCategory.LOCATION,
            )
        ],
        financial=[
            EvidenceItem(
                speaker=Speaker.DRIVER,
                quote="Need at least $2/mile.",
                category=EvidenceCategory.FINANCIAL,
            )
        ],
    )
    assert len(evidence.locations) == 1
    assert len(evidence.financial) == 1
    assert evidence.equipment == []


def test_field_value_wraps_typed_value_with_provenance():
    field = FieldValue[float](
        value=2.0,
        confidence=0.98,
        evidence="As long as it's above $2/mile",
    )
    assert field.value == 2.0
    assert field.evidence is not None


def test_driver_profile_supports_required_assignment_fields():
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            minimum_rate_per_mile=FieldValue(
                value=2.0,
                evidence="$2/mile minimum",
            ),
            equipment_types=FieldValue(value=["dry van"]),
            weight_capacity=FieldValue(value=45000.0),
        )
    )
    assert profile.required_fields.minimum_rate_per_mile is not None
    assert profile.required_fields.minimum_rate_per_mile.value == 2.0
    assert profile.required_fields.equipment_types is not None


def test_resolved_driver_profile_combines_profile_and_coordinates():
    profile = DriverProfile()
    resolved = ResolvedDriverProfile(
        profile=profile,
        current_location=ResolvedLocation(
            city="Dallas",
            state="Texas",
            lat=32.7767,
            lon=-96.7970,
        ),
        canonical_equipment=["dry_van"],
    )
    assert resolved.current_location is not None
    assert resolved.current_location.lat == 32.7767
    assert resolved.canonical_equipment == ["dry_van"]


def test_load_schema_requires_core_fields():
    load = Load(
        load_id="L01",
        origin_city="Dallas",
        destination_city="Houston",
        trailer="Van",
        price=1200.0,
        weight=40000.0,
        loaded_miles=240.0,
    )
    assert load.load_id == "L01"
    assert load.loaded_miles == 240.0


def test_load_audit_entry_captures_rule_outcomes():
    audit = LoadAuditEntry(
        load_id="L01",
        trailer_check=RuleCheckStatus.PASS,
        weight_check=RuleCheckStatus.PASS,
        missing_data_check=RuleCheckStatus.PASS,
        rate_check=RuleCheckStatus.PASS,
        eligible=EligibilityStatus.ACCEPT,
        reason="—",
        effective_rate=2.5,
        rule_checks=[
            RuleCheck(rule="trailer", status=RuleCheckStatus.PASS),
        ],
    )
    assert audit.eligible == EligibilityStatus.ACCEPT
    assert audit.effective_rate == 2.5


def test_ranked_load_links_load_and_audit():
    load = Load(
        load_id="L02",
        origin_city="Dallas",
        destination_city="Atlanta",
        trailer="Van",
        price=2000.0,
    )
    audit = LoadAuditEntry(
        load_id="L02",
        trailer_check=RuleCheckStatus.PASS,
        weight_check=RuleCheckStatus.PASS,
        missing_data_check=RuleCheckStatus.PASS,
        eligible=EligibilityStatus.ACCEPT,
        reason="—",
        effective_rate=2.8,
    )
    ranked = RankedLoad(load=load, audit=audit, rank=1)
    assert ranked.rank == 1
    assert ranked.audit.effective_rate == 2.8


def test_location_ref_defaults_country_to_usa():
    location = LocationRef(city="Dallas", state="Texas")
    assert location.country == "USA"
