"""Unit tests for prompt templating."""

import pytest

from src.utils.prompts import (
    MissingPromptVariableError,
    PromptTemplate,
    extract_variables,
    render_template,
)


def test_extract_variables_finds_double_brace_placeholders():
    template = "Hello {{name}}, extract {{downstream_fields}}."
    assert extract_variables(template) == {"name", "downstream_fields"}


def test_render_template_substitutes_variables():
    rendered = render_template(
        "Fields: {{downstream_fields}}.",
        {"downstream_fields": "rate, equipment"},
    )
    assert rendered == "Fields: rate, equipment."


def test_render_template_raises_on_missing_variables():
    with pytest.raises(MissingPromptVariableError, match="downstream_fields"):
        render_template("Use {{downstream_fields}}", {})


def test_render_template_allows_missing_when_not_strict():
    rendered = render_template(
        "Use {{downstream_fields}}",
        {},
        strict=False,
    )
    assert rendered == "Use {{downstream_fields}}"


def test_prompt_template_from_string_and_render():
    template = PromptTemplate.from_string("Task: {{task_name}}")
    assert template.render({"task_name": "organize"}) == "Task: organize"
