"""Unit tests for the conversation organizer agent."""

from unittest.mock import MagicMock

import pytest

from src.agents.base import AgentTask
from src.agents.conversation_organizer import ConversationOrganizer, normalize_evidence
from src.domain.downstream_context import organizer_prompt_variables
from src.domain.enums import EvidenceCategory, EvidenceClassification, Speaker
from src.domain.schemas import ConversationEvidence, EvidenceItem
from src.utils.prompts import PromptTemplate

DEFAULT_VARS = organizer_prompt_variables()


SAMPLE_TRANSCRIPT = """
Dispatcher: Hey, where are you running today?
Driver: I'm in Dallas with my dry van. I won't go under $2 a mile.
"""

INLINE_PROMPT = """Downstream agent: {{downstream_agent_name}}

{{downstream_extraction_guide}}

Required:
{{downstream_required_fields}}
"""


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def organizer(mock_llm):
    return ConversationOrganizer(
        llm=mock_llm,
        prompt_template=PromptTemplate.from_string(INLINE_PROMPT),
        default_variables=DEFAULT_VARS,
    )


def test_run_calls_structured_completion_with_rendered_prompts(organizer, mock_llm):
    expected = ConversationEvidence(
        locations=[
            EvidenceItem(
                speaker=Speaker.DRIVER,
                quote="I'm in Dallas with my dry van.",
                category=EvidenceCategory.LOCATION,
            )
        ]
    )
    mock_llm.complete_structured.return_value = expected

    task = AgentTask(content=SAMPLE_TRANSCRIPT)
    result = organizer.run(task)

    assert result == expected
    mock_llm.complete_structured.assert_called_once()
    kwargs = mock_llm.complete_structured.call_args.kwargs
    assert kwargs["prompt"] == SAMPLE_TRANSCRIPT.strip()
    assert "current location" in kwargs["system_prompt"]
    assert "Listen for" in kwargs["system_prompt"] or "Downstream field" in kwargs["system_prompt"]
    assert "Profile Extractor" in kwargs["system_prompt"]


def test_run_supports_runtime_prompt_variables(organizer, mock_llm):
    mock_llm.complete_structured.return_value = ConversationEvidence()
    custom_required = "- custom field alpha\n- custom field beta"
    task = AgentTask(
        content="Driver: Hello",
        variables={"downstream_required_fields": custom_required},
    )

    organizer.run(task)

    system_prompt = mock_llm.complete_structured.call_args.kwargs["system_prompt"]
    assert "custom field alpha" in system_prompt
    assert "preferred lanes" in system_prompt  # other defaults still present


def test_organize_wrapper_builds_task(organizer, mock_llm):
    mock_llm.complete_structured.return_value = ConversationEvidence()

    organizer.organize(
        SAMPLE_TRANSCRIPT,
        downstream_required_fields="- override field",
    )

    kwargs = mock_llm.complete_structured.call_args.kwargs
    assert kwargs["prompt"] == SAMPLE_TRANSCRIPT.strip()
    assert "override field" in kwargs["system_prompt"]


def test_run_rejects_empty_task_content(organizer):
    with pytest.raises(ValueError, match="task.content must not be empty"):
        organizer.run(AgentTask(content="   "))


def test_normalize_evidence_strips_quotes_and_drops_blanks():
    evidence = ConversationEvidence(
        locations=[
            EvidenceItem(
                speaker=Speaker.DRIVER,
                quote="  I'm in Dallas.  ",
                category=EvidenceCategory.LOCATION,
            ),
            EvidenceItem(
                speaker=Speaker.DRIVER,
                quote="   ",
                category=EvidenceCategory.LOCATION,
            ),
        ]
    )

    normalized = normalize_evidence(evidence)

    assert len(normalized.locations) == 1
    assert normalized.locations[0].quote == "I'm in Dallas."


def test_normalize_evidence_preserves_all_buckets():
    evidence = ConversationEvidence(
        financial=[
            EvidenceItem(
                speaker=Speaker.DRIVER,
                quote="Need $2/mile",
                category=EvidenceCategory.FINANCIAL,
                classification=EvidenceClassification.EXPLICIT,
            )
        ],
        equipment=[
            EvidenceItem(
                speaker=Speaker.DRIVER,
                quote="dry van",
                category=EvidenceCategory.EQUIPMENT,
            )
        ],
    )

    normalized = normalize_evidence(evidence)

    assert len(normalized.financial) == 1
    assert len(normalized.equipment) == 1
    assert normalized.constraints == []
