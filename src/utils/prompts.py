"""Prompt loading and templating utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from configs.settings import PROMPTS_DIR

VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class MissingPromptVariableError(KeyError):
    """Raised when a required prompt variable is not supplied."""


def extract_variables(template: str) -> set[str]:
    """Return placeholder names declared as `{{variable}}` in a template."""
    return set(VARIABLE_PATTERN.findall(template))


def render_template(
    template: str,
    variables: Mapping[str, Any] | None = None,
    *,
    strict: bool = True,
) -> str:
    """Render `{{variable}}` placeholders in a prompt template."""
    variables = variables or {}
    required = extract_variables(template)
    missing = sorted(name for name in required if name not in variables)
    if strict and missing:
        raise MissingPromptVariableError(
            f"Missing prompt variables: {', '.join(missing)}"
        )

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            return match.group(0)
        return str(variables[name])

    return VARIABLE_PATTERN.sub(replace, template).strip()


@dataclass(frozen=True)
class PromptTemplate:
    """Loadable prompt template with runtime variable substitution."""

    name: str
    template: str

    @classmethod
    def from_file(
        cls,
        name: str,
        *,
        prompts_dir: Path | None = None,
    ) -> PromptTemplate:
        base_dir = prompts_dir or PROMPTS_DIR
        path = base_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return cls(name=name, template=path.read_text(encoding="utf-8"))

    @classmethod
    def from_string(cls, template: str, *, name: str = "inline") -> PromptTemplate:
        return cls(name=name, template=template)

    def variables(self) -> set[str]:
        return extract_variables(self.template)

    def render(
        self,
        variables: Mapping[str, Any] | None = None,
        *,
        strict: bool = True,
    ) -> str:
        return render_template(self.template, variables, strict=strict)


def load_prompt(name: str, *, prompts_dir: Path | None = None) -> str:
    """Load a prompt file without rendering variables."""
    return PromptTemplate.from_file(name, prompts_dir=prompts_dir).template
