"""OpenRouter prompt caching — stable prefix, session stickiness, any model."""
from __future__ import annotations

import copy
import os
from typing import Any

# 1h TTL: fewer re-writes in long agent sessions (Anthropic/Gemini/Alibaba explicit)
CACHE: dict[str, str] = {"type": "ephemeral", "ttl": "1h"}


def cache_ttl() -> dict[str, str]:
    ttl = os.environ.get("WIRE0_CACHE_TTL", "1h")
    return {"type": "ephemeral", "ttl": ttl} if ttl else {"type": "ephemeral"}


def cached_system(instructions: str, workspace: str = "") -> dict[str, Any]:
    """Instructions cached; workspace listing refreshed each request."""
    parts: list[dict[str, Any]] = [
        {"type": "text", "text": instructions, "cache_control": cache_ttl()},
    ]
    if workspace:
        parts.append({"type": "text", "text": workspace})
    return {"role": "system", "content": parts}


def cached_tools(schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tool defs with cache breakpoint on last tool (OpenRouter tool caching)."""
    tools = copy.deepcopy(schemas)
    if tools:
        tools[-1]["cache_control"] = cache_ttl()
    return tools


def build_request(
    model: str,
    system: str,
    workspace: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    session_id: str,
) -> dict[str, Any]:
    """Build body optimized for cache hits on any OpenRouter model."""
    return {
        "model": model,
        "messages": [cached_system(system, workspace), *messages],
        "tools": cached_tools(tools),
        "cache_control": cache_ttl(),
        "session_id": session_id,
        "parallel_tool_calls": True,
        "stream": True,
        "stream_options": {"include_usage": True},
    }


def cache_stats(usage: dict[str, Any] | None) -> dict[str, int]:
    """Extract cache metrics from OpenRouter usage object."""
    if not usage:
        return {"prompt": 0, "cached": 0, "written": 0}
    details = usage.get("prompt_tokens_details") or {}
    return {
        "prompt": usage.get("prompt_tokens", 0),
        "cached": details.get("cached_tokens", 0),
        "written": details.get("cache_write_tokens", 0),
    }
