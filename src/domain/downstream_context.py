"""Downstream extraction context shared between pipeline agents."""

from __future__ import annotations

DOWNSTREAM_REQUIRED_FIELDS: tuple[str, ...] = (
    "current location",
    "current latitude",
    "current longitude",
    "home base",
    "home latitude",
    "home longitude",
    "minimum rate per mile",
    "equipment types",
    "weight capacity",
)

DOWNSTREAM_PREFERENCE_FIELDS: tuple[str, ...] = (
    "preferred regions",
    "avoided regions",
    "preferred cities",
    "avoided cities",
    "preferred lanes",
    "soft preferences",
)

DOWNSTREAM_CONSTRAINT_FIELDS: tuple[str, ...] = (
    "hard constraints",
    "requires factorable brokers",
    "negotiates rates",
)

DOWNSTREAM_OPERATIONAL_FIELDS: tuple[str, ...] = (
    "raw equipment description",
    "canonical equipment",
    "days per week",
    "availability",
    "schedule flexibility",
)

# field name → (listen_for, bucket, notes)
DOWNSTREAM_CAPTURE_GUIDE: tuple[tuple[str, str, str, str], ...] = (
    (
        "current location",
        "locations",
        "where the truck is right now, sitting in, currently in, headed to",
        "Capture even if home base is also mentioned — do not pick one; quote both. Preserve city and state names exactly as spoken.",
    ),
    (
        "home base",
        "locations",
        "home, based out of, usually run from, home terminal",
        "Keep separate from current-location quotes when both appear. Preserve city and state names exactly as spoken.",
    ),
    (
        "minimum rate per mile",
        "financial",
        "$/mile, per mile, rate floor, won't haul under, need at least",
        "Capture the exact pay language.",
    ),
    (
        "equipment types",
        "equipment",
        "dry van, reefer, flatbed, stepdeck, trailer type, 53-foot, truck type",
        "Quote equipment mentions verbatim.",
    ),
    (
        "weight capacity",
        "equipment",
        "pounds, lbs, weight limit, haul up to, capacity",
        "Often appears in the same sentence as equipment — still capture it.",
    ),
    (
        "preferred lanes / regions / cities",
        "preferences",
        "like running, prefer, favorite lanes, want to run",
        "Soft preference — not an absolute refusal.",
    ),
    (
        "avoided lanes / regions / cities",
        "preferences",
        "try to stay out of, don't like, dislike, traffic, prefer not",
        "Soft dislike only. Use constraints only when the driver states they will not go or run freight there at all.",
    ),
    (
        "hard constraints",
        "constraints",
        "won't go, never go, do not run there, refuse, no exceptions, under no circumstances",
        "Absolute location or business limits only — not mere dislike.",
    ),
    (
        "requires factorable brokers",
        "constraints",
        "factorable, factoring, quick pay, broker payment terms",
        "Broker/payment requirements are constraints.",
    ),
    (
        "negotiates rates",
        "operations",
        "negotiate, haggle, counter offer, work the rate",
        "How they handle rate discussions.",
    ),
    (
        "days per week",
        "availability",
        "days a week, run Mon–Fri, weekends off",
        "Schedule frequency.",
    ),
    (
        "availability / schedule flexibility",
        "availability",
        "available, pickup window, flexible, when can you load",
        "When/how often they can run.",
    ),
    (
        "raw equipment description",
        "equipment",
        "full equipment phrase as spoken",
        "Keep the raw wording — do not normalize trailer names.",
    ),
    (
        "soft preferences",
        "preferences",
        "rather, prefer, ideally, if possible",
        "Non-hard likes/dislikes.",
    ),
)


def _format_bullets(fields: tuple[str, ...]) -> str:
    return "\n".join(f"- {field}" for field in fields)


def _format_capture_guide() -> str:
    lines = [
        "Use this checklist so the Profile Extractor has every quote it needs.",
        "When you hear language like the signals below, capture the verbatim quote in the bucket shown.",
        "",
        "| Downstream field | Bucket | Listen for | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for field, bucket, listen_for, notes in DOWNSTREAM_CAPTURE_GUIDE:
        lines.append(f"| {field} | `{bucket}` | {listen_for} | {notes} |")
    lines.extend(
        [
            "",
            "Coverage rule: if a quote could help any row above, include it.",
            "Do not skip a quote because you are unsure which downstream field it maps to.",
            "Prefer splitting combined statements into separate evidence items when they mention different themes.",
            "Place each quote in exactly ONE bucket — choose the best fit.",
        ]
    )
    return "\n".join(lines)


def organizer_prompt_variables() -> dict[str, str]:
    """Runtime variables for the conversation organizer system prompt."""
    return {
        "downstream_agent_name": "Profile Extractor",
        "downstream_extraction_guide": _format_capture_guide(),
        "downstream_required_fields": _format_bullets(DOWNSTREAM_REQUIRED_FIELDS),
        "downstream_preference_fields": _format_bullets(DOWNSTREAM_PREFERENCE_FIELDS),
        "downstream_constraint_fields": _format_bullets(DOWNSTREAM_CONSTRAINT_FIELDS),
        "downstream_operational_fields": _format_bullets(DOWNSTREAM_OPERATIONAL_FIELDS),
    }


def profile_extractor_prompt_variables() -> dict[str, str]:
    """Runtime variables for the profile extractor system prompt."""
    return {
        "required_fields_list": _format_bullets(DOWNSTREAM_REQUIRED_FIELDS),
        "preference_fields_list": _format_bullets(DOWNSTREAM_PREFERENCE_FIELDS),
        "constraint_fields_list": _format_bullets(DOWNSTREAM_CONSTRAINT_FIELDS),
        "operational_fields_list": _format_bullets(DOWNSTREAM_OPERATIONAL_FIELDS),
        "field_value_instructions": (
            "Every populated field must use the FieldValue shape: "
            "`value`, `confidence` (0-1), `evidence` (supporting quote from organizer), "
            "and optional `reasoning_notes`. "
            "Use null for missing fields — never invent numbers or defaults."
        ),
        "location_format_instructions": (
            "**Location fields (`current_location`, `home_base`) — mandatory format:**\n"
            "- Value must be exactly `\"City, ST\"` with a two-letter US state code "
            "(e.g. `\"Dallas, TX\"`, `\"San Antonio, TX\"`, `\"Buckeye, AZ\"`).\n"
            "- Resolve vague area text to one city before returning (e.g. "
            "`\"Buckeye area west of Phoenix\"` → `\"Buckeye, AZ\"`).\n"
            "- Do not put regions, lanes, or landmark-only text in these fields.\n"
            "- If you cannot produce a single `\"City, ST\"` without guessing, set the field to `null`."
        ),
    }
