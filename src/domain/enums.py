"""Domain enums."""

from enum import StrEnum


class LLMProvider(StrEnum):
    """Supported LLM provider backends."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    GOOGLE = "google"


class Speaker(StrEnum):
    """Conversation participant."""

    DRIVER = "Driver"
    DISPATCHER = "Dispatcher"
    UNKNOWN = "Unknown"


class EvidenceClassification(StrEnum):
    """Whether evidence was stated explicitly or inferred."""

    EXPLICIT = "Explicit"
    IMPLICIT = "Implicit"


class EvidenceCategory(StrEnum):
    """High-level evidence bucket from the conversation organizer."""

    LOCATION = "Location"
    EQUIPMENT = "Equipment"
    CONSTRAINT = "Constraint"
    PREFERENCE = "Preference"
    FINANCIAL = "Financial"
    OPERATIONS = "Operations"
    AVAILABILITY = "Availability"
    OTHER = "Other"


class RuleCheckStatus(StrEnum):
    """Result of a single deterministic rule check."""

    PASS = "PASS"
    FAIL = "FAIL"


class EligibilityStatus(StrEnum):
    """Final eligibility decision for a load."""

    ACCEPT = "Accept"
    REJECT = "Reject"
