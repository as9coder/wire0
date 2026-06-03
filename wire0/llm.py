"""OpenRouter chat + tool loop."""
from __future__ import annotations

import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import httpx

from wire0.cache import build_request, cache_stats
from wire0.config import DEFAULT_MODEL, get_api_key
from wire0.tools import SCHEMAS, execute
from wire0.workspace import context_block

API = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM = """You are Wire0 — a minimal, highly competent coding agent.

## Workspace (IMPORTANT)
You are given the active workspace path and a file listing (names only) in each request.
- Work inside that workspace. Use relative paths from its root.
- The listing shows what exists — use read_file/grep for contents, not the listing.
- Stay in-workspace by default; outside paths are possible but avoid unless necessary.

## Parallelism (CRITICAL — always do this)
- Issue MULTIPLE tool_calls in EVERY turn when work is independent. Never one-at-a-time if you can batch.
- Within each tool, pass ARRAYS of paths/files/patches — never loop one path per call.
- Example good turn: grep + list_dir + read_file(paths=[a,b,c]) — all in ONE response.
- Example bad turn: three separate read_file calls each with one path.

## Tool guide (order of preference)
1. **grep** — ALWAYS search first to locate symbols, imports, definitions. Batch paths=[dir1,dir2,...]. Use include="*.py" to filter.
2. **list_dir** — Orient in unfamiliar areas. Batch paths=[...] for multiple dirs.
3. **read_file** — Read only what you need. Batch paths=[file1,file2,...] in ONE call. Use offset/limit for large files.
4. **patch_file** — PREFERRED for all edits. Batch patches=[{path,old,new},...] for multiple edits at once. old must be unique in file.
5. **write_file** — New files ONLY. Batch files=[{path,content},...]. Never rewrite whole files when patch_file works.
6. **delete_path** — Remove files/dirs. Batch paths=[...].
7. **shell_run** — ONE foreground session for ALL sync work (tests, build, git, install). NEVER call multiple shell_run in parallel. Batch: commands=["npm install","npm test"]. Returns full merged transcript. NOT for servers.
8. **bg_shell** — SEPARATE tool. ONLY for dev servers, docker, watch mode — anything long-running/detached. bg_shell list BEFORE start. Never duplicate servers. Never use shell_run for servers.

## Shell rules (STRICT)
- shell_run and bg_shell are DIFFERENT tools — never substitute one for the other
- Max ONE shell_run per turn — batch with commands=["a","b","c"]
- If a command is running, shell_run with no commands to refresh transcript
- Servers/watchers → bg_shell start ONLY
- Sync commands → shell_run ONLY
- If shell_run says still running → do NOT call shell_run again; use bg_shell for servers or wait

## Workflow
grep → read_file (batched) → patch_file (batched) → shell_run (verify) OR bg_shell start (servers)
Inspect before editing. Verify after editing. Be direct."""


def _headers(session_id: str) -> dict[str, str]:
    key = get_api_key()
    if not key:
        raise RuntimeError("No API key — run /key in the CLI to set your OpenRouter key")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/wire0",
        "X-Title": "Wire0",
        "x-session-id": session_id,
    }


def _run_tool(
    tc: dict[str, Any],
    on_tool: Callable[[str, str], None] | None,
    on_tool_result: Callable[[str, str], None] | None,
) -> dict[str, str]:
    fn = tc["function"]
    name, args = fn["name"], fn["arguments"]
    if on_tool:
        on_tool(name, args)
    result = execute(name, args)
    if on_tool_result:
        on_tool_result(name, result)
    return {"role": "tool", "tool_call_id": tc["id"], "content": result}


def chat(
    messages: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
    session_id: str | None = None,
    on_token: Callable[[str], None] | None = None,
    on_tool: Callable[[str, str], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    on_cache: Callable[[dict[str, int]], None] | None = None,
    on_wait: Callable[[], None] | None = None,
    cancel: threading.Event | None = None,
) -> list[dict[str, Any]]:
    """Run agent loop until model stops calling tools. Returns updated messages."""
    sid = session_id or str(uuid.uuid4())

    def _check() -> None:
        if cancel and cancel.is_set():
            raise KeyboardInterrupt

    while True:
        _check()
        if on_wait:
            on_wait()
        body = build_request(model, SYSTEM, context_block(), messages, SCHEMAS, sid)
        assistant: dict[str, Any] = {"role": "assistant", "content": "", "tool_calls": []}
        tc_buf: dict[int, dict[str, str]] = {}
        usage: dict[str, Any] | None = None

        with httpx.stream("POST", API, headers=_headers(sid), json=body, timeout=None) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                _check()
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)
                if u := chunk.get("usage"):
                    usage = u
                delta = chunk["choices"][0].get("delta", {})
                if tok := delta.get("content"):
                    assistant["content"] += tok
                    if on_token:
                        on_token(tok)
                for tc in delta.get("tool_calls") or []:
                    i = tc.get("index", 0)
                    if i not in tc_buf:
                        tc_buf[i] = {"id": "", "name": "", "arguments": ""}
                    if tc.get("id"):
                        tc_buf[i]["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        tc_buf[i]["name"] = fn["name"]
                    if fn.get("arguments"):
                        tc_buf[i]["arguments"] += fn["arguments"]

        if on_cache:
            on_cache(cache_stats(usage))

        if tc_buf:
            assistant["tool_calls"] = [
                {
                    "id": tc_buf[i]["id"],
                    "type": "function",
                    "function": {"name": tc_buf[i]["name"], "arguments": tc_buf[i]["arguments"]},
                }
                for i in sorted(tc_buf)
            ]
        messages.append({k: v for k, v in assistant.items() if v or k == "content"})

        if not assistant.get("tool_calls"):
            break

        _check()
        calls = assistant["tool_calls"]
        workers = min(len(calls), 8)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            tool_msgs = list(pool.map(lambda tc: _run_tool(tc, on_tool, on_tool_result), calls))
        messages.extend(tool_msgs)

    return messages
