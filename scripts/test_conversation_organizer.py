#!/usr/bin/env python3
"""Manual smoke test for the Conversation Organizer agent.

Setup:
    pip install -e ".[ai]"
    cp .env.example .env   # set GROQ_API_KEY (or change PROVIDER below)

Run:
    python scripts/test_conversation_organizer.py

Edit the CONFIG section below to change provider, transcript, or prompt variables.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import AgentTask, ConversationOrganizer
from src.domain.enums import LLMProvider
from src.providers.llm import create_llm_provider

# =============================================================================
# CONFIG — edit these values
# =============================================================================

PROVIDER = LLMProvider.GROQ
MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.0
MAX_TOKENS = 4096

# Inline transcript (used unless TRANSCRIPT_FILE is set and exists)
TRANSCRIPT = """
Dispatcher: Good morning, this is Mike from ABC Logistics. How's it going out there?
Driver: Hey Mike, doing alright. I'm usually in that Houston area but I'm sitting in Dallas right now.
Dispatcher: Got it. What are you running?
Driver: I've got a 53-foot dry van. I can haul up to about 45,000 pounds.
Dispatcher: Any lanes you like or want to avoid?
Driver: I like Texas to Georgia lanes. I try to stay out of the Northeast.
Dispatcher: What's your rate expectation?
Driver: As long as it's above $2 a mile I'm good. I only work with factorable brokers.
Dispatcher: When are you available?
Driver: I run about 5 days a week, pretty flexible on pickup windows.
"""

# Set to a file path to load transcript from disk instead of TRANSCRIPT above
TRANSCRIPT_FILE: Path | None = None  # PROJECT_ROOT / "data/raw/conversation.txt"

# Optional: override any {{placeholder}} in prompts/conversation_organizer.md
# See defaults in src/domain/downstream_context.py
PROMPT_VARIABLES: dict[str, str] = {}

# Print the fully rendered system prompt before calling the LLM
SHOW_SYSTEM_PROMPT = True

# Optional: save JSON output to this path
OUTPUT_FILE: Path | None = None  # PROJECT_ROOT / "src/outputs/conversation_evidence.json"


def main() -> None:
    transcript = TRANSCRIPT.strip()
    if TRANSCRIPT_FILE and TRANSCRIPT_FILE.exists():
        transcript = TRANSCRIPT_FILE.read_text(encoding="utf-8").strip()
        print(f"Loaded transcript from: {TRANSCRIPT_FILE}")

    if not transcript:
        raise SystemExit("Transcript is empty. Set TRANSCRIPT or TRANSCRIPT_FILE.")

    llm = create_llm_provider(
        PROVIDER,
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    organizer = ConversationOrganizer(llm=llm)
    task = AgentTask(content=transcript, variables=PROMPT_VARIABLES)

    print("=" * 72)
    print("Conversation Organizer smoke test")
    print(f"Provider : {PROVIDER.value}")
    print(f"Model    : {MODEL}")
    print("=" * 72)
    print("\n--- Transcript ---")
    print(transcript)

    if SHOW_SYSTEM_PROMPT:
        print("\n--- Rendered system prompt ---")
        print(organizer.render_system_prompt(task))

    print("\n--- Running organizer ---")
    evidence = organizer.run(task)

    payload = evidence.model_dump(mode="json")
    print("\n--- Organized evidence ---")
    print(json.dumps(payload, indent=2))

    print("\n--- Bucket counts ---")
    for bucket in (
        "locations",
        "equipment",
        "constraints",
        "preferences",
        "financial",
        "operations",
        "availability",
        "other",
    ):
        items = getattr(evidence, bucket)
        print(f"{bucket:14} {len(items)}")

    if OUTPUT_FILE:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nSaved output to: {OUTPUT_FILE}")

    print("\nDone.")


if __name__ == "__main__":
    main()
