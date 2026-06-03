"""Local config — API key stored in ~/.wire0/config.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".wire0"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_api_key() -> str:
    if k := os.environ.get("OPENROUTER_API_KEY", "").strip():
        return k
    if not CONFIG_FILE.exists():
        return ""
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return str(data.get("openrouter_api_key", "")).strip()
    except (json.JSONDecodeError, OSError):
        return ""


def set_api_key(key: str) -> None:
    key = key.strip()
    if not key:
        raise ValueError("API key cannot be empty")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[str, str] = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    data["openrouter_api_key"] = key
    CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
    os.environ["OPENROUTER_API_KEY"] = key


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "••••••••"
    return f"{key[:4]}…{key[-4:]}"
