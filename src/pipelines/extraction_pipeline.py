"""Stages 1–3: conversation → driver profile → geocoded coordinates."""

from __future__ import annotations

from src.agents import AgentTask, ConversationOrganizer, ProfileExtractor
from src.domain.schemas import ConversationEvidence, DriverProfile, ResolvedDriverProfile
from src.providers.llm.base import BaseLLMProvider
from src.services.geocoder import GeocoderService


class ExtractionPipeline:
    """Run conversation understanding and location resolution."""

    def __init__(
        self,
        *,
        organizer: ConversationOrganizer | None = None,
        extractor: ProfileExtractor | None = None,
        geocoder: GeocoderService | None = None,
        llm: BaseLLMProvider | None = None,
    ) -> None:
        """Build the pipeline.

        When ``llm`` is passed, both agents share that provider (useful in tests).
        Otherwise each agent uses its entry in ``configs/agent_llm_config.py``.
        """
        if llm is not None:
            self.organizer = organizer or ConversationOrganizer(llm=llm)
            self.extractor = extractor or ProfileExtractor(llm=llm)
        else:
            self.organizer = organizer or ConversationOrganizer()
            self.extractor = extractor or ProfileExtractor()
        self.geocoder = geocoder or GeocoderService.from_settings()

    def run(self, transcript: str) -> ResolvedDriverProfile:
        """Execute Stages 1–3 on a raw transcript."""
        transcript = transcript.strip()
        if not transcript:
            raise ValueError("transcript must not be empty")

        evidence = self.organize(transcript)
        profile = self.extract(evidence)
        return self.geocoder.resolve_profile(profile)

    def organize(self, transcript: str) -> ConversationEvidence:
        """Stage 1 — organize transcript into evidence buckets."""
        return self.organizer.run(AgentTask(content=transcript))

    def extract(self, evidence: ConversationEvidence) -> DriverProfile:
        """Stage 2 — infer structured driver profile from evidence."""
        return self.extractor.extract(evidence)

    def resolve_locations(self, profile: DriverProfile) -> ResolvedDriverProfile:
        """Stage 3 — geocode current/home locations."""
        return self.geocoder.resolve_profile(profile)
