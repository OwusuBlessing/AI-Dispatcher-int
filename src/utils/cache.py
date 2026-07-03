"""File-based cache utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonFileCache:
    """Simple JSON object cache persisted to disk."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._data is not None:
            return self._data

        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
            return self._data

        self._data = {}
        return self._data

    def get(self, key: str) -> Any | None:
        return self._load().get(key)

    def set(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = value
        self._persist(data)

    def _persist(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._data = data
