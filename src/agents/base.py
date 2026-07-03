"""Base agent abstractions shared by all LLM agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Generic, Sequence, TypeVar

from pydantic import BaseModel

from configs.agent_llm_config import AgentName, create_agent_llm
from src.providers.llm.base import BaseLLMProvider, MessageInput
from src.providers.llm.factory import create_llm_provider
from src.utils.prompts import PromptTemplate

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")


@dataclass
class AgentTask:
    """Runtime input for an agent invocation."""

    content: str
    history: Sequence[MessageInput] | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC, Generic[R]):
    """Common LLM agent interface: task in, typed result out."""

    prompt_file: ClassVar[str]
    agent_name: ClassVar[AgentName | None] = None
    default_variables: ClassVar[dict[str, Any]] = {}

    def __init__(
        self,
        llm: BaseLLMProvider | None = None,
        *,
        prompt_template: PromptTemplate | None = None,
        prompt_file: str | None = None,
        default_variables: dict[str, Any] | None = None,
    ) -> None:
        self.llm = llm or (
            create_agent_llm(self.agent_name)
            if self.agent_name is not None
            else create_llm_provider()
        )
        resolved_prompt_file = prompt_file or self.prompt_file
        self.prompt_template = prompt_template or PromptTemplate.from_file(
            resolved_prompt_file
        )
        self.default_variables = {
            **self.default_variables,
            **(default_variables or {}),
        }

    def merge_variables(self, task: AgentTask) -> dict[str, Any]:
        """Merge agent defaults with per-task prompt variables."""
        return {**self.default_variables, **task.variables}

    def render_system_prompt(self, task: AgentTask) -> str:
        """Render the system prompt with runtime variables."""
        return self.prompt_template.render(self.merge_variables(task))

    def render_task_prompt(self, task: AgentTask) -> str:
        """Render the user/task prompt."""
        return task.content.strip()

    def validate_task(self, task: AgentTask) -> None:
        if not task.content or not task.content.strip():
            raise ValueError("task.content must not be empty")

    def complete_text(self, task: AgentTask, **overrides: Any) -> str:
        """Run a text completion for the given task."""
        self.validate_task(task)
        return self.llm.complete(
            self.render_task_prompt(task),
            system_prompt=self.render_system_prompt(task),
            history=task.history,
            **overrides,
        )

    def complete_structured(
        self,
        schema: type[T],
        task: AgentTask,
        **overrides: Any,
    ) -> T:
        """Run a structured completion for the given task."""
        self.validate_task(task)
        return self.llm.complete_structured(
            schema,
            prompt=self.render_task_prompt(task),
            system_prompt=self.render_system_prompt(task),
            history=task.history,
            **overrides,
        )

    @abstractmethod
    def run(self, task: AgentTask) -> R:
        """Execute the agent against a task."""
