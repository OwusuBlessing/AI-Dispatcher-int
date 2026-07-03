"""Coerce raw LLM scalars into FieldValue wrappers before validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def coerce_field_value(value: Any) -> Any:
    """Wrap bare LLM values as FieldValue-compatible dicts."""
    if value is None:
        return None
    if (
        isinstance(value, BaseModel)
        and "value" in type(value).model_fields
        and "confidence" in type(value).model_fields
    ):
        return value
    if isinstance(value, dict):
        if "value" in value:
            return value
        return None
    return {"value": value, "confidence": 1.0}


def coerce_section_field_values(data: Any, model_cls: type[BaseModel]) -> Any:
    """Coerce every field on a driver profile section model."""
    if not isinstance(data, dict):
        return data

    coerced = dict(data)
    for field_name in model_cls.model_fields:
        if field_name in coerced:
            coerced[field_name] = coerce_field_value(coerced[field_name])
    return coerced
