"""OpenRouter context window — model limit + live prompt token count."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from wire0.cache import build_request
from wire0.config import get_api_key
from wire0.llm import API, SYSTEM, _headers
from wire0.tools import SCHEMAS
from wire0.workspace import context_block

MODELS_API = "https://openrouter.ai/api/v1/models"
_model_cache: dict[str, dict[str, Any]] = {}


@dataclass
class ContextInfo:
    model: str
    model_name: str | None
    prompt_tokens: int
    cached_tokens: int
    context_limit: int | None

    @property
    def fill_ratio(self) -> float | None:
        if not self.context_limit or self.context_limit <= 0:
            return None
        return min(self.prompt_tokens / self.context_limit, 1.0)


def _load_models() -> dict[str, dict[str, Any]]:
    global _model_cache
    if _model_cache:
        return _model_cache
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if key := get_api_key():
        headers["Authorization"] = f"Bearer {key}"
    r = httpx.get(MODELS_API, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json().get("data") or []
    _model_cache = {m["id"]: m for m in data if m.get("id")}
    return _model_cache


def _context_limit(meta: dict[str, Any]) -> int | None:
    limit = meta.get("context_length")
    if isinstance(limit, int) and limit > 0:
        return limit
    top = meta.get("top_provider") or {}
    limit = top.get("context_length")
    if isinstance(limit, int) and limit > 0:
        return limit
    return None


def fetch_context_info(
    model: str,
    messages: list[dict[str, Any]],
    session_id: str,
) -> ContextInfo:
    """Fetch context limit from OpenRouter models API and prompt tokens via usage probe."""
    models = _load_models()
    meta = models.get(model) or {}
    if not meta and model.endswith(":free"):
        meta = models.get(model[: -len(":free")]) or {}
    limit = _context_limit(meta) if meta else None
    model_name = meta.get("name") if meta else None

    body = build_request(model, SYSTEM, context_block(), messages, SCHEMAS, session_id)
    body["stream"] = False
    body["max_tokens"] = 1
    body.pop("stream_options", None)

    r = httpx.post(API, headers=_headers(session_id), json=body, timeout=60)
    r.raise_for_status()
    usage = r.json().get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}

    return ContextInfo(
        model=model,
        model_name=model_name,
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        cached_tokens=int(details.get("cached_tokens") or 0),
        context_limit=limit,
    )


def clear_model_cache() -> None:
    global _model_cache
    _model_cache = {}
