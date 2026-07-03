"""Format submission deliverables: profile table, audit table, and README."""

from __future__ import annotations

from typing import Any

from src.domain.schemas import FieldValue, LoadAuditEntry, MatchingResult, ResolvedDriverProfile

README_MAX_WORDS = 200

_PROFILE_ROWS: tuple[tuple[str, str], ...] = (
    ("Current Location", "current_location"),
    ("Current Latitude", "current_latitude"),
    ("Current Longitude", "current_longitude"),
    ("Home Base", "home_base"),
    ("Home Latitude", "home_latitude"),
    ("Home Longitude", "home_longitude"),
    ("Minimum Rate ($/mi)", "minimum_rate_per_mile"),
    ("Equipment Types", "equipment_types"),
    ("Weight Capacity (lbs)", "weight_capacity"),
)


def _format_field_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if value == int(value):
            return f"{int(value):,}"
        return f"{value:,.2f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "—"
    return str(value)


def _field_row(
    label: str,
    field: FieldValue[Any] | None,
) -> tuple[str, str, str]:
    if field is None or field.value is None:
        return label, "—", "—"
    return label, _format_field_value(field.value), f"{field.confidence:.2f}"


def format_profile_table(driver: ResolvedDriverProfile) -> str:
    """Render Part A driver profile as a markdown table."""
    required = driver.profile.required_fields
    rows = [
        _field_row(label, getattr(required, attr))
        for label, attr in _PROFILE_ROWS
    ]

    if driver.canonical_equipment:
        rows.append(
            (
                "Canonical Equipment",
                ", ".join(driver.canonical_equipment),
                "—",
            )
        )

    lines = [
        "## Driver Profile (Part A)",
        "",
        "| Field | Value | Confidence |",
        "| --- | --- | --- |",
    ]
    for label, value, confidence in rows:
        lines.append(f"| {label} | {value} | {confidence} |")
    return "\n".join(lines)


def _check_status(value: str | None) -> str:
    return value or "—"


def format_audit_table(audits: list[LoadAuditEntry]) -> str:
    """Render per-load eligibility audit as a markdown table."""
    lines = [
        "## Load Audit",
        "",
        "| Load | Trailer | Location | Weight | Missing | Rate | Eligible | $/mi | Miles | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for audit in audits:
        rate = f"${audit.effective_rate:.2f}" if audit.effective_rate is not None else "—"
        miles = f"{audit.total_miles:.0f}" if audit.total_miles is not None else "—"
        reason = audit.reason.replace("|", "/")
        lines.append(
            "| {load} | {trailer} | {location} | {weight} | {missing} | {rate_check} | {eligible} | "
            "{eff_rate} | {miles} | {reason} |".format(
                load=audit.load_id,
                trailer=audit.trailer_check.value,
                location=_check_status(
                    audit.location_check.value if audit.location_check else None
                ),
                weight=audit.weight_check.value,
                missing=audit.missing_data_check.value,
                rate_check=_check_status(
                    audit.rate_check.value if audit.rate_check else None
                ),
                eligible=audit.eligible.value,
                eff_rate=rate,
                miles=miles,
                reason=reason,
            )
        )
    return "\n".join(lines)


def format_top_loads_table(matching: MatchingResult) -> str:
    """Render ranked eligible loads."""
    if not matching.top_loads:
        return "## Top 3 Recommended Loads\n\n_No eligible loads with computable effective rates._"

    lines = [
        "## Top 3 Recommended Loads",
        "",
        "| Rank | Load | Route | Price | $/mi | Total mi |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in matching.top_loads:
        load = item.load
        audit = item.audit
        route = f"{load.origin_city} → {load.destination_city or '?'}"
        price = f"${load.price:,.0f}" if load.price is not None else "—"
        eff = (
            f"${audit.effective_rate:.2f}"
            if audit.effective_rate is not None
            else "—"
        )
        miles = f"{audit.total_miles:.0f}" if audit.total_miles is not None else "—"
        lines.append(
            f"| {item.rank} | {load.load_id} | {route} | {price} | {eff} | {miles} |"
        )
    return "\n".join(lines)


def format_submission_document(
    driver: ResolvedDriverProfile,
    matching: MatchingResult,
) -> str:
    """Assemble the full submission markdown report."""
    sections = [
        "# AI Dispatcher — Submission",
        "",
        format_profile_table(driver),
        "",
        format_audit_table(matching.audits),
        "",
        format_top_loads_table(matching),
    ]
    return "\n".join(sections)


def generate_readme() -> str:
    """Return the assignment README (≤200 words)."""
    text = """# AI Dispatcher

Freight matching for owner-operators: LLMs interpret language; Python enforces business rules.

## Pipeline flow

```
conversation.txt → Organizer (LLM) → Extractor (LLM) → Geocoder → Resolved Driver Profile
loads.xlsx       → Load Normalizer  → Rule Engine      → Distance & Rate → Top 3 + Audit → submission.md
```

## Profile extraction

Two LLM stages organize the transcript into evidence, then build a profile with confidence and quotes. Locations use `City, ST` + Nominatim geocoding (never LLM coordinates). Post-processing canonicalizes equipment and clears unstated fields.

## Incomplete rows

Config-driven Excel mapping (`configs/loads.yaml`). Blank rows are skipped; rows missing destination or price are still audited and rejected with a recorded reason.

## Assumptions

Trailer, weight, missing-data, and min-rate rules run in Python. Null `minimum_rate_per_mile` or `weight_capacity` skips that filter. Effective rate = price ÷ total trip miles (Haversine).

## Rejected high-paying load

**L05** (Waco → San Antonio, $640) has an effective rate of **$2.514/mi** — above the driver's $2/mi floor — but requires **flatbed**. This driver runs **hotshot/gooseneck** only, so it fails the equipment rule and is excluded before ranking.

## Run

```bash
pip install -e ".[dev,ai]"
cp .env.example .env
python scripts/create_submission.py
```

Agent models are configured in `configs/agent_llm_config.py`.
"""
    word_count = len(text.split())
    if word_count > README_MAX_WORDS:
        raise ValueError(f"README exceeds {README_MAX_WORDS} words ({word_count})")
    return text
