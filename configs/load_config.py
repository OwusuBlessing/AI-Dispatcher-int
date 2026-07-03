"""Load ingest configuration loaded from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from configs.settings import CONFIGS_DIR

LOADS_CONFIG_PATH = CONFIGS_DIR / "loads.yaml"
EQUIPMENT_CONFIG_PATH = CONFIGS_DIR / "equipment.yaml"

LOAD_FIELDS = (
    "load_id",
    "origin_city",
    "origin_state",
    "origin_latitude",
    "origin_longitude",
    "destination_city",
    "destination_state",
    "destination_latitude",
    "destination_longitude",
    "trailer",
    "weight",
    "price",
    "loaded_miles",
)


@dataclass(frozen=True)
class LoadsIngestConfig:
    """Column mapping and normalization settings for load spreadsheets."""

    sheet_name: str = "Loads"
    column_aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    missing_values: frozenset[str] = frozenset({"MISSING", "N/A", "NA", ""})
    id_field: str = "load_id"
    title_case_cities: bool = True
    parse_city_state_from_location: bool = True

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> LoadsIngestConfig:
        config_path = Path(path) if path else LOADS_CONFIG_PATH
        raw = _read_yaml(config_path)

        column_aliases = {
            field_name: tuple(aliases)
            for field_name, aliases in raw.get("columns", {}).items()
        }
        missing_values = frozenset(
            str(value) for value in raw.get("missing_values", [])
        )
        normalization = raw.get("normalization", {})

        return cls(
            sheet_name=str(raw.get("sheet_name", "Loads")),
            column_aliases=column_aliases,
            missing_values=missing_values,
            id_field=str(raw.get("id_field", "load_id")),
            title_case_cities=bool(normalization.get("title_case_cities", True)),
            parse_city_state_from_location=bool(
                normalization.get("parse_city_state_from_location", True)
            ),
        )

    def resolve_header_map(self, headers: list[str]) -> dict[str, str]:
        """Map logical fields to the actual header names present in a workbook."""
        normalized_headers = {header.lower(): header for header in headers if header}
        resolved: dict[str, str] = {}

        for field_name, aliases in self.column_aliases.items():
            for alias in aliases:
                actual = normalized_headers.get(alias.lower())
                if actual is not None:
                    resolved[field_name] = actual
                    break

        return resolved

    def require_mapped_fields(self, header_map: dict[str, str]) -> None:
        required = ("load_id", "origin_city", "trailer")
        missing = [field for field in required if field not in header_map]
        if missing:
            raise ValueError(
                "Loads spreadsheet is missing required columns for: "
                + ", ".join(missing)
            )


@dataclass(frozen=True)
class EquipmentAliasConfig:
    """Trailer label aliases and load compatibility rules."""

    alias_to_canonical: dict[str, str]
    compatibility: dict[str, frozenset[str]]

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> EquipmentAliasConfig:
        config_path = Path(path) if path else EQUIPMENT_CONFIG_PATH
        raw = _read_yaml(config_path)
        alias_to_canonical: dict[str, str] = {}

        for canonical, aliases in raw.get("canonical_aliases", {}).items():
            canonical_key = str(canonical).strip().lower()
            alias_to_canonical[canonical_key] = canonical_key
            for alias in aliases:
                alias_to_canonical[str(alias).strip().lower()] = canonical_key

        compatibility: dict[str, frozenset[str]] = {}
        for driver_type, accepted_loads in raw.get("compatibility", {}).items():
            driver_key = str(driver_type).strip().lower()
            compatibility[driver_key] = frozenset(
                str(load_type).strip().lower() for load_type in accepted_loads
            )

        return cls(
            alias_to_canonical=alias_to_canonical,
            compatibility=compatibility,
        )

    def canonicalize(self, value: str) -> str | None:
        return self.alias_to_canonical.get(value.strip().lower())

    def accepts_load(self, driver_equipment: str, load_trailer: str) -> bool:
        """Return whether a driver equipment type can haul the load trailer type."""
        driver_type = self.canonicalize(driver_equipment) or driver_equipment.lower()
        load_type = self.canonicalize(load_trailer) or load_trailer.lower()
        accepted = self.compatibility.get(driver_type, frozenset({driver_type}))
        return load_type in accepted


def get_value(row: dict[str, Any], header_map: dict[str, str], field: str) -> Any:
    """Read a logical field from a raw row using the resolved header map."""
    header = header_map.get(field)
    if header is None:
        return None
    return row.get(header)


@lru_cache(maxsize=1)
def get_loads_ingest_config() -> LoadsIngestConfig:
    return LoadsIngestConfig.from_yaml()


@lru_cache(maxsize=1)
def get_equipment_alias_config() -> EquipmentAliasConfig:
    return EquipmentAliasConfig.from_yaml()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in config file: {path}")
    return data
