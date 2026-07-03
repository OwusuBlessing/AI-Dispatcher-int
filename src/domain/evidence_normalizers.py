"""Normalize LLM output variants before strict schema validation."""

from __future__ import annotations

from src.domain.enums import Speaker

_SPEAKER_ALIASES: dict[str, Speaker] = {
    "driver": Speaker.DRIVER,
    "dr": Speaker.DRIVER,
    "dispatcher": Speaker.DISPATCHER,
    "dispatch": Speaker.DISPATCHER,
    "disp": Speaker.DISPATCHER,
    "broker": Speaker.DISPATCHER,
    "agent": Speaker.DISPATCHER,
    "unknown": Speaker.UNKNOWN,
}


def normalize_speaker(value: Speaker | str | None) -> Speaker:
    """Map common LLM speaker variants to the canonical enum."""
    if isinstance(value, Speaker):
        return value
    if value is None:
        return Speaker.UNKNOWN

    key = str(value).strip().lower()
    if key in _SPEAKER_ALIASES:
        return _SPEAKER_ALIASES[key]

    for speaker in Speaker:
        if key == speaker.value.lower():
            return speaker

    return Speaker.UNKNOWN
