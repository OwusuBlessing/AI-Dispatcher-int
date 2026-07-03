"""Stage 5 — Load dataset normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from configs.load_config import (
    EquipmentAliasConfig,
    LoadsIngestConfig,
    get_equipment_alias_config,
    get_loads_ingest_config,
    get_value,
)
from src.domain.schemas import Load
from src.services.load_reader import read_load_rows

CITY_STATE_PATTERN = re.compile(r"^(.+),\s*([A-Za-z]{2})$")


@dataclass
class LoadNormalizationReport:
    """Summary of load normalization results."""

    loads: list[Load] = field(default_factory=list)
    skipped_rows: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    header_map: dict[str, str] = field(default_factory=dict)


def load_and_normalize_loads(
    path: Path | str,
    *,
    loads_config: LoadsIngestConfig | None = None,
    equipment_config: EquipmentAliasConfig | None = None,
) -> LoadNormalizationReport:
    """Read and normalize every load row from Excel."""
    ingest_config = loads_config or get_loads_ingest_config()
    equipment = equipment_config or get_equipment_alias_config()
    report = LoadNormalizationReport()

    raw_rows, header_map = read_load_rows(path, config=ingest_config)
    report.header_map = header_map

    for raw_row in raw_rows:
        source_row = raw_row.get("_source_row", "?")
        try:
            load = normalize_load_row(
                raw_row,
                header_map=header_map,
                loads_config=ingest_config,
                equipment_config=equipment,
            )
        except ValueError as exc:
            report.skipped_rows.append(f"row {source_row}: {exc}")
            continue

        if not load.origin_city:
            report.skipped_rows.append(f"row {source_row}: missing origin")
            continue

        if not load.destination_city:
            report.warnings.append(
                f"{load.load_id}: missing destination — will fail missing-data rule"
            )
        if load.price is None:
            report.warnings.append(
                f"{load.load_id}: missing price — will fail missing-data rule"
            )

        report.loads.append(load)

    return report


def normalize_load_row(
    raw_row: dict[str, Any],
    *,
    header_map: dict[str, str],
    loads_config: LoadsIngestConfig,
    equipment_config: EquipmentAliasConfig,
) -> Load:
    """Normalize one Excel row into a Load model."""
    load_id = _require_text(
        _clean_text(
            get_value(raw_row, header_map, "load_id"),
            loads_config,
        ),
        field_name="load_id",
    )

    origin_city, origin_state = _normalize_location_fields(
        city_value=get_value(raw_row, header_map, "origin_city"),
        state_value=get_value(raw_row, header_map, "origin_state"),
        loads_config=loads_config,
    )
    destination_city, destination_state = _normalize_location_fields(
        city_value=get_value(raw_row, header_map, "destination_city"),
        state_value=get_value(raw_row, header_map, "destination_state"),
        loads_config=loads_config,
    )

    trailer = normalize_trailer(
        get_value(raw_row, header_map, "trailer"),
        equipment_config=equipment_config,
    )

    return Load(
        load_id=load_id,
        origin_city=origin_city,
        origin_state=origin_state,
        origin_latitude=_normalize_optional_float(
            get_value(raw_row, header_map, "origin_latitude"),
            loads_config,
        ),
        origin_longitude=_normalize_optional_float(
            get_value(raw_row, header_map, "origin_longitude"),
            loads_config,
        ),
        destination_city=destination_city,
        destination_state=destination_state,
        destination_latitude=_normalize_optional_float(
            get_value(raw_row, header_map, "destination_latitude"),
            loads_config,
        ),
        destination_longitude=_normalize_optional_float(
            get_value(raw_row, header_map, "destination_longitude"),
            loads_config,
        ),
        trailer=trailer,
        price=_normalize_optional_float(
            get_value(raw_row, header_map, "price"),
            loads_config,
        ),
        weight=_normalize_optional_float(
            get_value(raw_row, header_map, "weight"),
            loads_config,
        ),
        loaded_miles=_normalize_optional_float(
            get_value(raw_row, header_map, "loaded_miles"),
            loads_config,
        ),
    )


def _normalize_location_fields(
    *,
    city_value: Any,
    state_value: Any,
    loads_config: LoadsIngestConfig,
) -> tuple[str, str | None]:
    city_text = _clean_text(city_value, loads_config)
    state_text = _clean_text(state_value, loads_config)

    if state_text:
        return _format_city(city_text, loads_config), state_text.upper()

    if loads_config.parse_city_state_from_location and city_text:
        match = CITY_STATE_PATTERN.match(city_text)
        if match:
            city, state = match.groups()
            return _format_city(city.strip(), loads_config), state.upper()

    return _format_city(city_text, loads_config), None


def _format_city(city_text: str, loads_config: LoadsIngestConfig) -> str:
    if not city_text:
        return ""
    if not loads_config.title_case_cities:
        return city_text
    return " ".join(part.capitalize() for part in city_text.split())


def normalize_city_name(
    value: Any,
    *,
    loads_config: LoadsIngestConfig | None = None,
) -> str:
    """Normalize city text using ingest missing-value rules."""
    config = loads_config or get_loads_ingest_config()
    return _format_city(_clean_text(value, config), config)


def normalize_trailer(
    value: Any,
    *,
    equipment_config: EquipmentAliasConfig | None = None,
) -> str:
    """Map trailer labels to canonical equipment types via config aliases."""
    equipment = equipment_config or get_equipment_alias_config()
    text = _require_text(value, field_name="trailer")
    canonical = equipment.canonicalize(text)
    if canonical is None:
        raise ValueError(f"unsupported trailer type '{text}'")
    return canonical


def _clean_text(value: Any, config: LoadsIngestConfig) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.casefold() in {item.casefold() for item in config.missing_values}:
        return ""
    return text


def _require_text(value: Any, *, field_name: str) -> str:
    if value is None:
        raise ValueError(f"missing {field_name}")
    text = str(value).strip()
    if not text:
        raise ValueError(f"missing {field_name}")
    return text


def _normalize_optional_float(
    value: Any,
    config: LoadsIngestConfig,
) -> float | None:
    if _clean_text(value, config) == "":
        return None
    if value is None or value == "":
        return None
    return float(value)
