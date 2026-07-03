"""Business rule configuration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from configs.settings import CONFIGS_DIR

RULES_CONFIG_PATH = CONFIGS_DIR / "rules.yaml"


@dataclass(frozen=True)
class RulesConfig:
    """Feature flags for deterministic load-matching rules."""

    missing_data_enabled: bool = True
    equipment_enabled: bool = True
    weight_enabled: bool = True
    rate_enabled: bool = True
    location_enabled: bool = True
    skip_rate_when_minimum_null: bool = True

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> RulesConfig:
        config_path = Path(path) if path else RULES_CONFIG_PATH
        raw = _read_yaml(config_path)
        rate = raw.get("rate", {})
        location = raw.get("location", {})

        return cls(
            missing_data_enabled=_section_enabled(raw.get("missing_data", {})),
            equipment_enabled=_section_enabled(raw.get("equipment", {})),
            weight_enabled=_section_enabled(raw.get("weight", {})),
            rate_enabled=_section_enabled(rate),
            location_enabled=_section_enabled(location),
            skip_rate_when_minimum_null=bool(rate.get("skip_when_minimum_rate_null", True)),
        )


def _section_enabled(section: dict[str, Any]) -> bool:
    if not section:
        return True
    return bool(section.get("enabled", True))


@lru_cache(maxsize=1)
def get_rules_config() -> RulesConfig:
    return RulesConfig.from_yaml()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in config file: {path}")
    return data
