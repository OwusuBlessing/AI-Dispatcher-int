"""Submission formatter unit tests."""

from __future__ import annotations

from src.domain.enums import EligibilityStatus, RuleCheckStatus
from src.domain.schemas import (
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
    Load,
    LoadAuditEntry,
    MatchingResult,
    RankedLoad,
    ResolvedDriverProfile,
)
from src.services.submission_formatter import (
    README_MAX_WORDS,
    format_audit_table,
    format_profile_table,
    format_submission_document,
    format_top_loads_table,
    generate_readme,
)


def test_generate_readme_within_word_limit():
    readme = generate_readme()
    assert len(readme.split()) <= README_MAX_WORDS
    assert "Pipeline flow" in readme
    assert "conversation.txt" in readme
    assert "submission.md" in readme


def test_format_profile_table_renders_part_a_fields():
    driver = ResolvedDriverProfile(
        profile=DriverProfile(
            required_fields=DriverRequiredFields(
                current_location=FieldValue(value="Dallas, TX", confidence=0.98),
                current_latitude=FieldValue(value=32.7762719, confidence=0.98),
                current_longitude=FieldValue(value=-96.7968559, confidence=0.98),
                home_latitude=FieldValue(value=29.4246002, confidence=0.97),
                home_longitude=FieldValue(value=-98.4951405, confidence=0.97),
                minimum_rate_per_mile=FieldValue(value=2.0, confidence=1.0),
                equipment_types=FieldValue(
                    value=["hotshot", "gooseneck"],
                    confidence=1.0,
                ),
            ),
        ),
        canonical_equipment=["hotshot", "gooseneck"],
    )

    table = format_profile_table(driver)

    assert "| Current Location | Dallas, TX | 0.98 |" in table
    assert "| Current Latitude | 32.7763 | 0.98 |" in table
    assert "| Current Longitude | -96.7969 | 0.98 |" in table
    assert "| Home Latitude | 29.4246 | 0.97 |" in table
    assert "| Home Longitude | -98.4951 | 0.97 |" in table
    assert "| Minimum Rate ($/mi) | 2 | 1.00 |" in table
    assert "| Canonical Equipment | hotshot, gooseneck | — |" in table


def test_format_audit_table_includes_rule_outcomes():
    audits = [
        LoadAuditEntry(
            load_id="L01",
            trailer_check=RuleCheckStatus.FAIL,
            weight_check=RuleCheckStatus.PASS,
            missing_data_check=RuleCheckStatus.PASS,
            location_check=RuleCheckStatus.PASS,
            eligible=EligibilityStatus.REJECT,
            reason="Not recommended — Equipment mismatch: this driver runs hotshot, which cannot haul a van load.",
            effective_rate=0.97,
            total_miles=640.0,
        )
    ]

    table = format_audit_table(audits)

    assert "| Location |" in table
    assert "Equipment mismatch" in table


def test_format_submission_document_combines_sections():
    driver = ResolvedDriverProfile(profile=DriverProfile())
    matching = MatchingResult(
        audits=[],
        top_loads=[
            RankedLoad(
                rank=1,
                load=Load(
                    load_id="L03",
                    origin_city="Austin",
                    destination_city="Corpus Christi",
                    trailer="gooseneck",
                    price=1500.0,
                ),
                audit=LoadAuditEntry(
                    load_id="L03",
                    trailer_check=RuleCheckStatus.PASS,
                    weight_check=RuleCheckStatus.PASS,
                    missing_data_check=RuleCheckStatus.PASS,
                    location_check=RuleCheckStatus.PASS,
                    eligible=EligibilityStatus.ACCEPT,
                    reason="Recommended — this load passes equipment, data quality, location policy, and pay checks.",
                    effective_rate=3.1,
                    total_miles=484.0,
                ),
            )
        ],
    )

    doc = format_submission_document(driver, matching)

    assert "# AI Dispatcher — Submission" in doc
    assert "## Driver Profile (Part A)" in doc
    assert "## Load Audit" in doc
    assert "## Top 3 Recommended Loads" in doc
    assert "L03" in doc
