"""Runtime configuration updated via /api/config (e.g. from Settings UI)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("arthur.ap.runtime_config")

# Defaults for parameters exposed via the config API
_DEFAULTS: dict[str, Any] = {
    "memory_similarity_threshold": 0.0,  # 0–1; min cosine similarity for memory vector search
}

_runtime: dict[str, Any] = {}
_config_path: Path | None = None


def set_config_path(path: Path | None) -> None:
    """Set path for persisting config (optional). If set, config is loaded/saved to this file."""
    global _config_path
    _config_path = path


def load_persisted() -> None:
    """Load config from file if path is set and file exists."""
    if _config_path is None or not _config_path.exists():
        return
    try:
        with _config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        _runtime.update(data)
        logger.info("Loaded runtime config from %s", _config_path)
    except Exception as e:
        logger.warning("Could not load runtime config from %s: %s", _config_path, e)


def _persist() -> None:
    if _config_path is None:
        return
    try:
        _config_path.parent.mkdir(parents=True, exist_ok=True)
        with _config_path.open("w", encoding="utf-8") as f:
            json.dump(_runtime, f, indent=2)
    except Exception as e:
        logger.warning("Could not persist runtime config to %s: %s", _config_path, e)


def get_config() -> dict[str, Any]:
    """Return current runtime config (defaults merged with overrides)."""
    out = dict(_DEFAULTS)
    out.update(_runtime)
    return out


def update_config(updates: dict[str, Any]) -> dict[str, Any]:
    """Apply partial updates and return full config. Persists if path is set."""
    for key, value in updates.items():
        if key not in _DEFAULTS:
            continue
        _runtime[key] = value
    _persist()
    return get_config()
