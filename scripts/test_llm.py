#!/usr/bin/env python3
"""Manual LLM smoke test — edit the inputs below and run:

    python scripts/test_llm.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

# Ensure project root is on sys.path when run as a script.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.enums import LLMProvider
from src.providers.llm import create_llm_provider

# =============================================================================
# CONFIG — edit these values
# =============================================================================

PROVIDER = LLMProvider.GROQ
MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.0
MAX_TOKENS = 1024
TIMEOUT = 60.0
MAX_RETRIES = 2

# Optional Groq-specific extras (see LangChain ChatGroq docs)
EXTRA: dict = {
  #   "reasoning_format": "parsed",
}

SYSTEM_PROMPT = (
    "You are a freight dispatcher assistant. "
    "Answer clearly and keep responses short."
)

HISTORY: list[tuple[str, str] | dict[str, str]] = [
    ("human", "I'm usually in Dallas but I'm heading to Houston tomorrow."),
    ("assistant", "Got it — current area Dallas, planning Houston tomorrow."),
]

PROMPT = "Summarize my location situation in one sentence."

STRUCTURED_SYSTEM_PROMPT = (
    "Extract driver profile fields from the conversation. "
    "Return only the structured fields requested."
)

STRUCTURED_PROMPT = (
    "Driver said: 'I'm in Dallas with a dry van. I won't take anything under $2/mile.'"
)

RUN_TEXT_COMPLETION = True
RUN_STRUCTURED_COMPLETION = True


# =============================================================================
# STRUCTURED OUTPUT SCHEMA
# =============================================================================


class DriverProfileSnippet(BaseModel):
    """Small schema for structured completion smoke test."""

    current_city: str = Field(description="Driver's current city")
    equipment: str = Field(description="Trailer or equipment type")
    minimum_rate_per_mile: float = Field(description="Minimum acceptable rate per mile")


# =============================================================================
# TEST RUNNER
# =============================================================================


def main() -> None:
    llm = create_llm_provider(
        PROVIDER,
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        timeout=TIMEOUT,
        max_retries=MAX_RETRIES,
        extra=EXTRA,
    )

    print("=" * 72)
    print("LLM smoke test")
    print(f"Provider : {PROVIDER.value}")
    print(f"Model    : {MODEL}")
    print(f"Temp     : {TEMPERATURE}")
    print(f"Max tok  : {MAX_TOKENS}")
    print("=" * 72)

    if RUN_TEXT_COMPLETION:
        print("\n--- Text completion ---")
        print(f"System : {SYSTEM_PROMPT}")
        print(f"History: {len(HISTORY)} message(s)")
        print(f"Prompt : {PROMPT}")

        text = llm.complete(
            PROMPT,
            system_prompt=SYSTEM_PROMPT,
            history=HISTORY,
        )
        print("\nResponse:")
        print(text)

    if RUN_STRUCTURED_COMPLETION:
        print("\n--- Structured completion ---")
        print(f"System : {STRUCTURED_SYSTEM_PROMPT}")
        print(f"Prompt : {STRUCTURED_PROMPT}")

        structured = llm.complete_structured(
            DriverProfileSnippet,
            prompt=STRUCTURED_PROMPT,
            system_prompt=STRUCTURED_SYSTEM_PROMPT,
        )
        print("\nParsed object:")
        print(structured.model_dump_json(indent=2))

        print("\nAs dict:")
        print(json.dumps(structured.model_dump(), indent=2))

    print("\nDone.")


if __name__ == "__main__":
    main()
