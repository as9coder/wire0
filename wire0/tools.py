"""Minimal tool implementations — batch paths + grep."""
from __future__ import annotations

import json
import os
import re
import shutil
from fnmatch import fnmatch
from pathlib import Path

from wire0.bg_shell import bg_shell as _bg_shell
from wire0.shell import run_shell

ROOT = Path.cwd()


def _resolve(p: str) -> tuple[Path, str | None]:
    """Resolve path from workspace root; soft warn if outside workspace."""
    raw = Path(p).expanduser()
    path = (ROOT / raw).resolve() if not raw.is_absolute() else raw.resolve()
    warn = None
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        warn = f"Note: outside workspace ({ROOT.resolve()})"
    return path, warn


def _paths(val: str | list[str] | None, default: str = ".") -> list[str]:
    if val is None:
        return [default]
    if isinstance(val, str):
        return [val]
    return list(val) if val else [default]


def _section(label: str, body: str) -> str:
    return f"=== {label} ===\n{body}"


def list_dir(paths: str | list[str] | None = None) -> str:
    out: list[str] = []
    for path in _paths(paths):
        try:
            p, warn = _resolve(path)
            if not p.is_dir():
                out.append(_section(path, f"Error: not a directory"))
                continue
            lines = []
            for e in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                tag = "d" if e.is_dir() else "f"
                lines.append(f"[{tag}] {e.name}")
            body = "\n".join(lines) or "(empty)"
            if warn:
                body = f"{warn}\n{body}"
            out.append(_section(path, body))
        except Exception as e:
            out.append(_section(path, f"Error: {e}"))
    return "\n\n".join(out)


def read_file(
    paths: str | list[str],
    offset: int = 1,
    limit: int = 500,
) -> str:
    out: list[str] = []
    for path in _paths(paths):
        try:
            p, warn = _resolve(path)
            if not p.is_file():
                out.append(_section(path, "Error: not a file"))
                continue
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(0, offset - 1)
            chunk = lines[start : start + limit]
            body = "\n".join(f"{start + i + 1:4}| {ln}" for i, ln in enumerate(chunk))
            if warn:
                body = f"{warn}\n{body}"
            out.append(_section(path, body))
        except Exception as e:
            out.append(_section(path, f"Error: {e}"))
    return "\n\n".join(out)


def write_file(path: str | None = None, content: str | None = None, files: list[dict] | None = None) -> str:
    items = files or ([{"path": path, "content": content}] if path is not None else [])
    if not items:
        return "Error: provide path+content or files=[{path,content},...]"
    out: list[str] = []
    for item in items:
        p, c = item.get("path"), item.get("content", "")
        if not p:
            out.append("Error: missing path in files entry")
            continue
        try:
            fp, warn = _resolve(p)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(c, encoding="utf-8")
            msg = f"Wrote {p} ({len(c)} bytes)"
            if warn:
                msg = f"{warn}\n{msg}"
            out.append(msg)
        except Exception as e:
            out.append(f"Error writing {p}: {e}")
    return "\n".join(out)


def delete_path(paths: str | list[str]) -> str:
    out: list[str] = []
    for path in _paths(paths):
        try:
            p, warn = _resolve(path)
            if not p.exists():
                out.append(f"Error: not found: {path}")
                continue
            if p.is_dir():
                shutil.rmtree(p)
                msg = f"Deleted directory {path}"
            else:
                p.unlink()
                msg = f"Deleted file {path}"
            if warn:
                msg = f"{warn}\n{msg}"
            out.append(msg)
        except Exception as e:
            out.append(f"Error deleting {path}: {e}")
    return "\n".join(out)


def patch_file(
    path: str | None = None,
    old: str | None = None,
    new: str | None = None,
    patches: list[dict] | None = None,
) -> str:
    items = patches or ([{"path": path, "old": old, "new": new}] if path else [])
    if not items:
        return "Error: provide path+old+new or patches=[{path,old,new},...]"
    out: list[str] = []
    for item in items:
        p, o, n = item.get("path"), item.get("old"), item.get("new", "")
        try:
            fp, warn = _resolve(p)
            if not fp.is_file():
                out.append(f"Error: not a file: {p}")
                continue
            text = fp.read_text(encoding="utf-8")
            if o not in text:
                out.append(f"Error: old_string not found in {p}")
                continue
            count = text.count(o)
            if count > 1:
                out.append(f"Error: old_string appears {count} times in {p} — must be unique")
                continue
            fp.write_text(text.replace(o, n, 1), encoding="utf-8")
            msg = f"Patched {p}"
            if warn:
                msg = f"{warn}\n{msg}"
            out.append(msg)
        except Exception as e:
            out.append(f"Error patching {p}: {e}")
    return "\n".join(out)


def grep(
    pattern: str,
    paths: str | list[str] | None = None,
    include: str = "*",
    ignore_case: bool = False,
    max_results: int = 200,
) -> str:
    try:
        flags = re.IGNORECASE if ignore_case else 0
        rx = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: invalid pattern: {e}"

    hits: list[str] = []
    for root in _paths(paths):
        try:
            base, _ = _resolve(root)
            files: list[Path]
            if base.is_file():
                files = [base]
            elif base.is_dir():
                files = sorted(p for p in base.rglob("*") if p.is_file() and fnmatch(p.name, include))
            else:
                hits.append(_section(root, "Error: not found"))
                continue
            for fp in files:
                try:
                    rel = fp.relative_to(ROOT.resolve())
                except ValueError:
                    rel = fp
                try:
                    for i, line in enumerate(fp.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        if rx.search(line):
                            hits.append(f"{rel}:{i}: {line.rstrip()}")
                            if len(hits) >= max_results:
                                return "\n".join(hits) + f"\n… truncated at {max_results} matches"
                except OSError:
                    continue
        except Exception as e:
            hits.append(_section(root, f"Error: {e}"))
    return "\n".join(hits) if hits else "(no matches)"


def shell_run(commands: str | list[str] | None = None, command: str | None = None, timeout_sec: float | None = None) -> str:
    if commands is None and command is None:
        cmds = None  # refresh running job
    elif commands is not None:
        cmds = commands
    else:
        cmds = command
    r = run_shell(cmds, timeout_sec)
    return r.output


def bg_shell(action: str, command: str | None = None, job_id: str | None = None) -> str:
    return _bg_shell(action, command, job_id)


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search file contents by regex. USE FIRST to locate code. Pass multiple paths to search many dirs/files at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern"},
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files or dirs to search (prefer many at once)",
                    },
                    "include": {"type": "string", "description": "Filename glob, e.g. *.py (default *)"},
                    "ignore_case": {"type": "boolean"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List directory contents. Pass paths array to list many dirs in one call.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Directories to list (prefer batch)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read files with line numbers. ALWAYS batch multiple paths in one call.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to read (prefer many at once)",
                    },
                    "offset": {"type": "integer", "description": "Start line (1-based)"},
                    "limit": {"type": "integer", "description": "Max lines per file"},
                },
                "required": ["paths"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create/overwrite files. For new files only — use patch_file for edits. Batch via files array.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                            "required": ["path", "content"],
                        },
                        "description": "Multiple files to write at once (preferred)",
                    },
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_path",
            "description": "Delete files or directories. Pass paths array to delete many at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths to delete (prefer batch)",
                    },
                },
                "required": ["paths"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patch_file",
            "description": "Surgical edit — replace unique old_string with new_string. PREFERRED for edits. Batch via patches array.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "old": {"type": "string"},
                                "new": {"type": "string"},
                            },
                            "required": ["path", "old", "new"],
                        },
                        "description": "Multiple edits at once (preferred)",
                    },
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell_run",
            "description": "ONE foreground shell session. Returns FULL merged transcript. Batch commands=[...] in ONE call. Empty call refreshes running command. NOT for servers — use bg_shell.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Run sequentially in same session (PREFERRED — one call)",
                    },
                    "command": {"type": "string", "description": "Single command if not using commands array"},
                    "timeout_sec": {"type": "number", "description": "On last command only"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bg_shell",
            "description": "SEPARATE detached shell for servers/long-running tasks only. Survives CLI exit. start|output|list|kill. Check list before start to avoid duplicates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["start", "output", "list", "kill"]},
                    "command": {"type": "string", "description": "Required for start"},
                    "job_id": {"type": "string", "description": "Optional id; required for kill"},
                },
                "required": ["action"],
            },
        },
    },
]

_DISPATCH = {
    "grep": lambda a: grep(a["pattern"], a.get("paths"), a.get("include", "*"), a.get("ignore_case", False)),
    "list_dir": lambda a: list_dir(a.get("paths", ".")),
    "read_file": lambda a: read_file(a["paths"], a.get("offset", 1), a.get("limit", 500)),
    "write_file": lambda a: write_file(a.get("path"), a.get("content"), a.get("files")),
    "delete_path": lambda a: delete_path(a["paths"]),
    "patch_file": lambda a: patch_file(a.get("path"), a.get("old"), a.get("new"), a.get("patches")),
    "shell_run": lambda a: shell_run(a.get("commands"), a.get("command"), a.get("timeout_sec")),
    "bg_shell": lambda a: bg_shell(a["action"], a.get("command"), a.get("job_id")),
}


def execute(name: str, args_json: str) -> str:
    try:
        args = json.loads(args_json or "{}")
        fn = _DISPATCH.get(name)
        if not fn:
            return f"Error: unknown tool {name}"
        return fn(args)
    except Exception as e:
        return f"Error: {e}"


def set_root(path: str | Path) -> None:
    global ROOT
    ROOT = Path(path).resolve()
    os.chdir(ROOT)


def workspace_path() -> str:
    return str(ROOT.resolve())
