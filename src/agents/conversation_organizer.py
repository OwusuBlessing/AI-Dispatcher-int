"""Stage 1 — Conversation Organizer Agent."""

from __future__ import annotations

from typing import Any, ClassVar

from src.agents.base import AgentTask, BaseAgent
from src.domain.downstream_context import organizer_prompt_variables
from src.domain.evidence_normalizers import normalize_speaker
from src.domain.schemas import ConversationEvidence
from src.providers.llm.base import MessageInput

DEFAULT_PROMPT_FILE = "conversation_organizer.md"


class ConversationOrganizer(BaseAgent[ConversationEvidence]):
    """Organize a raw transcript into bucketed conversation evidence."""

    prompt_file = DEFAULT_PROMPT_FILE
    agent_name = "conversation_organizer"
    default_variables: ClassVar[dict[str, Any]] = organizer_prompt_variables()

    def run(self, task: AgentTask) -> ConversationEvidence:
        evidence = self.complete_structured(ConversationEvidence, task)
        return normalize_evidence(evidence)

    def organize(
        self,
        transcript: str,
        *,
        history: list[MessageInput] | None = None,
        variables: dict[str, Any] | None = None,
        **prompt_variables: Any,
    ) -> ConversationEvidence:
        """Convenience wrapper for transcript-only calls."""
        merged_variables = {**(variables or {}), **prompt_variables}
        task = AgentTask(
            content=transcript,
            history=history,
            variables=merged_variables,
        )
        return self.run(task)


def normalize_evidence(evidence: ConversationEvidence) -> ConversationEvidence:
    """Strip quotes and drop empty evidence items."""
    bucket_specs = [
        ("locations", evidence.locations),
        ("equipment", evidence.equipment),
        ("constraints", evidence.constraints),
        ("preferences", evidence.preferences),
        ("financial", evidence.financial),
        ("operations", evidence.operations),
        ("availability", evidence.availability),
        ("other", evidence.other),
    ]

    normalized_buckets: dict[str, list] = {name: [] for name, _ in bucket_specs}

    for bucket_name, items in bucket_specs:
        for item in items:
            quote = item.quote.strip()
            if not quote:
                continue
            item.quote = quote
            item.speaker = normalize_speaker(item.speaker)
            normalized_buckets[bucket_name].append(item)

    return ConversationEvidence(**normalized_buckets)
