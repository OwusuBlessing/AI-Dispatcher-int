"""Unit tests for base agent abstractions."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from src.agents.base import AgentTask, BaseAgent
from src.utils.prompts import PromptTemplate


class SampleOutput(BaseModel):
    answer: str


class SampleAgent(BaseAgent[SampleOutput]):
    prompt_file = "conversation_organizer.md"

    def run(self, task: AgentTask) -> SampleOutput:
        return self.complete_structured(SampleOutput, task)


@pytest.fixture
def mock_llm():
    return MagicMock()


def test_agent_task_carries_content_history_and_variables():
    task = AgentTask(
        content="Driver: Hello",
        history=[("human", "prior")],
        variables={"downstream_fields": "rate"},
    )
    assert task.content.startswith("Driver")
    assert task.variables["downstream_fields"] == "rate"


def test_base_agent_merges_default_and_task_variables(mock_llm):
    template = PromptTemplate.from_string(
        "System uses {{downstream_fields}} and {{extra_hint}}."
    )
    agent = SampleAgent(
        llm=mock_llm,
        prompt_template=template,
        default_variables={"downstream_fields": "rate, equipment"},
    )
    task = AgentTask(content="hello", variables={"extra_hint": "be concise"})

    rendered = agent.render_system_prompt(task)

    assert "rate, equipment" in rendered
    assert "be concise" in rendered


def test_base_agent_complete_text_passes_rendered_prompts(mock_llm):
    template = PromptTemplate.from_string("Rules for {{downstream_fields}}")
    mock_llm.complete.return_value = "ok"
    agent = SampleAgent(
        llm=mock_llm,
        prompt_template=template,
        default_variables={"downstream_fields": "locations"},
    )
    task = AgentTask(content=" transcript ")

    result = agent.complete_text(task)

    assert result == "ok"
    mock_llm.complete.assert_called_once_with(
        "transcript",
        system_prompt="Rules for locations",
        history=None,
    )


def test_base_agent_validate_task_rejects_empty_content(mock_llm):
    template = PromptTemplate.from_string("System")
    agent = SampleAgent(llm=mock_llm, prompt_template=template)

    with pytest.raises(ValueError, match="task.content must not be empty"):
        agent.complete_text(AgentTask(content="   "))
