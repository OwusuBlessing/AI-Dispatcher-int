#!/usr/bin/env python3
"""Manual smoke test: Conversation Organizer → Profile Extractor.

    python scripts/test_profile_extractor.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from configs.agent_llm_config import get_agent_llm_config
from src.agents import AgentTask, ConversationOrganizer, ProfileExtractor

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

TRANSCRIPT_FILE: Path | None = PROJECT_ROOT / "data/raw/conversation.txt"
USE_HARD_CONVERSATION = False  # uses data/raw/conversation_hard.txt when True
HARD_TRANSCRIPT_FILE = PROJECT_ROOT / "data/raw/conversation_hard.txt"
EVIDENCE_FILE: Path | None = None  # skip organizer if JSON evidence provided
SHOW_SYSTEM_PROMPTS = False
OUTPUT_DIR: Path | None = PROJECT_ROOT / "src/outputs"


def main() -> None:
    organizer_cfg = get_agent_llm_config("conversation_organizer")
    extractor_cfg = get_agent_llm_config("profile_extractor")
    organizer = ConversationOrganizer()
    extractor = ProfileExtractor()

    transcript = TRANSCRIPT.strip()
    if USE_HARD_CONVERSATION and HARD_TRANSCRIPT_FILE.exists():
        transcript = HARD_TRANSCRIPT_FILE.read_text(encoding="utf-8").strip()
        print(f"\nUsing HARD conversation: {HARD_TRANSCRIPT_FILE.name}")
    elif TRANSCRIPT_FILE and TRANSCRIPT_FILE.exists():
        transcript = TRANSCRIPT_FILE.read_text(encoding="utf-8").strip()
        print(f"\nLoaded transcript from: {TRANSCRIPT_FILE}")

    print("=" * 72)
    print("Profile Extractor smoke test (Stage 1 → Stage 2)")
    print(
        "Organizer: "
        f"{organizer_cfg.provider.value if organizer_cfg.provider else 'env default'} "
        f"/ {organizer_cfg.model or 'provider default'}"
    )
    print(
        "Extractor: "
        f"{extractor_cfg.provider.value if extractor_cfg.provider else 'env default'} "
        f"/ {extractor_cfg.model or 'provider default'}"
    )
    print("=" * 72)

    if EVIDENCE_FILE and EVIDENCE_FILE.exists():
        from src.domain.schemas import ConversationEvidence

        evidence = ConversationEvidence.model_validate_json(
            EVIDENCE_FILE.read_text(encoding="utf-8")
        )
        print(f"\nLoaded evidence from: {EVIDENCE_FILE}")
    else:
        print("\n--- Stage 1: Conversation Organizer ---")
        evidence = organizer.run(AgentTask(content=transcript))
        print(json.dumps(evidence.model_dump(mode="json"), indent=2))

    print("\n--- Stage 2: Profile Extractor ---")
    if SHOW_SYSTEM_PROMPTS:
        from src.agents.profile_extractor import format_evidence_input

        task = AgentTask(content=format_evidence_input(evidence))
        print("\n[System prompt]")
        print(extractor.render_system_prompt(task))

    profile = extractor.extract(evidence)
    profile_json = json.dumps(profile.model_dump(mode="json"), indent=2)
    print(profile_json)

    if OUTPUT_DIR:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if USE_HARD_CONVERSATION:
            suffix = "hard_claude_sonnet_4_6"
        elif TRANSCRIPT_FILE:
            suffix = TRANSCRIPT_FILE.stem
        else:
            suffix = "default"
        evidence_path = OUTPUT_DIR / f"conversation_evidence_{suffix}.json"
        profile_path = OUTPUT_DIR / f"driver_profile_{suffix}.json"
        evidence_path.write_text(
            json.dumps(evidence.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        profile_path.write_text(profile_json, encoding="utf-8")
        print(f"\nSaved evidence → {evidence_path}")
        print(f"Saved profile  → {profile_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
