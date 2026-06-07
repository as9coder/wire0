"""Local config — API key stored in ~/.wire0/config.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".wire0"
CONFIG_FILE = CONFIG_DIR / "config.json"
LEGACY_FILE = Path.home() / ".agent0" / "config.json"
DEFAULT_MODEL = "openrouter/owl-alpha"


def _migrate_legacy() -> None:
    """One-time import from ~/.agent0/config.json if Wire0 config is missing."""
    if CONFIG_FILE.exists() or not LEGACY_FILE.exists():
        return
    try:
        data = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
        migrated = {k: str(v) for k, v in data.items() if v}
        if migrated:
            _save_config(migrated)
    except (json.JSONDecodeError, OSError):
        pass


def _load_config() -> dict[str, str]:
    _migrate_legacy()
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {k: str(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(data: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def get_api_key() -> str:
    if k := os.environ.get("OPENROUTER_API_KEY", "").strip():
        return k
    return _load_config().get("openrouter_api_key", "").strip()


def get_model() -> str:
    if m := os.environ.get("WIRE0_MODEL", "").strip():
        return m
    saved = _load_config().get("model", "").strip()
    return saved or DEFAULT_MODEL


def set_api_key(key: str) -> None:
    key = key.strip()
    if not key:
        raise ValueError("API key cannot be empty")
    data = _load_config()
    data["openrouter_api_key"] = key
    _save_config(data)
    os.environ["OPENROUTER_API_KEY"] = key


def set_model(model: str) -> None:
    model = model.strip()
    if not model:
        raise ValueError("Model id cannot be empty")
    data = _load_config()
    data["model"] = model
    _save_config(data)
    os.environ["WIRE0_MODEL"] = model


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "••••••••"
    return f"{key[:4]}…{key[-4:]}"
