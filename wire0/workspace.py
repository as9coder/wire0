"""Workspace context — path + file listing (names only)."""
from __future__ import annotations

import os
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".cursor",
    "dist",
    "build",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

SKIP_SUFFIXES = (".egg-info", ".pyc", ".pyo")


def get_root() -> Path:
    from wire0.tools import ROOT

    return ROOT


def _skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".") and name not in {".env.example"}


def file_tree(root: Path | None = None, max_entries: int = 800) -> str:
    """Compact workspace listing — paths/names only, no file contents."""
    root = (root or get_root()).resolve()
    lines: list[str] = [f"Workspace: {root}", "Files (use read_file for contents):"]
    count = 0
    truncated = False

    def walk(dirpath: Path, prefix: str) -> None:
        nonlocal count, truncated
        if truncated:
            return
        try:
            entries = sorted(dirpath.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        for entry in entries:
            if truncated:
                return
            name = entry.name
            if entry.is_dir():
                if _skip_dir(name):
                    continue
                rel = entry.relative_to(root).as_posix()
                lines.append(f"{prefix}[d] {rel}/")
                count += 1
                if count >= max_entries:
                    truncated = True
                    return
                walk(entry, prefix + "  ")
            else:
                if name.endswith(SKIP_SUFFIXES):
                    continue
                rel = entry.relative_to(root).as_posix()
                lines.append(f"{prefix}[f] {rel}")
                count += 1
                if count >= max_entries:
                    truncated = True
                    return

    walk(root, "")
    if truncated:
        lines.append(f"… ({max_entries}+ entries; use list_dir/grep to explore further)")
    elif count == 0:
        lines.append("(empty workspace)")
    return "\n".join(lines)


def context_block() -> str:
    """System appendix: where we are and what's here."""
    root = get_root()
    return (
        f"## Active workspace\n"
        f"Path: `{root}`\n"
        f"Work here. Tool paths are relative to this root unless absolute.\n"
        f"Prefer staying in this workspace; outside paths are allowed when needed.\n\n"
        f"{file_tree(root)}"
    )
