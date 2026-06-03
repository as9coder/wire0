"""Experimental welcome screen — opt out: WIRE0_TUI=0 or wire0 --plain"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from wire0.logo import ORANGE, logo_text

DIM = "#737373"


def show_welcome(console: Console, version: str, model: str, cwd: Path) -> None:
    info = Text()
    info.append(f"{model}\n", style=DIM)
    info.append(str(cwd), style=DIM)

    body = Group(Align.center(logo_text()), Align.center(info))
    console.print()
    console.print(
        Panel(
            body,
            title=f"[dim]v{version}[/dim]",
            border_style=ORANGE,
            padding=(1, 3),
            width=min(max(console.width - 4, 52), 68),
        )
    )
    console.print()


def footer(console: Console) -> None:
    console.print(Rule(style=DIM))
    console.print(f"[dim]/key · /model · /context · /clear · /exit[/dim]")


def key_prompt_html() -> str:
    return f"<style fg='{ORANGE}'>key</style> "


def input_prompt_html() -> str:
    return f"<style fg='{ORANGE}'>❯</style> "


def enabled() -> bool:
    if "--plain" in sys.argv:
        return False
    return os.environ.get("WIRE0_TUI", "1") != "0"
