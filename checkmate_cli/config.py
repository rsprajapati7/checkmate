"""
CheckMate CLI — User Configuration Manager.

Stores user-level config at ~/.checkmate/config.json
Supports: api_url, api_key
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR  = Path.home() / ".checkmate"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load config from disk. Returns empty dict if not found or corrupted."""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_config(config: dict) -> None:
    """Save config to disk."""
    _ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_config_value(key: str) -> Optional[str]:
    """Get a specific config value."""
    return load_config().get(key)


def set_config_value(key: str, value: str) -> None:
    """Set a specific config value."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


def get_config_path() -> Path:
    """Return the path to the config file (for display purposes)."""
    return CONFIG_FILE


VALID_KEYS = {"api_url", "api_key"}
