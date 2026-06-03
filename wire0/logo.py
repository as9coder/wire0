"""Wire0 ASCII wordmark — shared by TUI and plain CLI."""
from __future__ import annotations

from rich.text import Text

ORANGE = "#d4845c"


def logo_text(style: str | None = None) -> Text:
    """Wire0 wordmark with wire connectors."""
    bold = style or f"bold {ORANGE}"
    wire = f"dim {ORANGE}"
    out = Text()

    out.append("    ●────────────────────●\n", style=wire)
    out.append("           ╭─────────╮\n", style=wire)
    out.append("       ●───│ ", style=wire)
    out.append("Wire0", style=bold)
    out.append(" │───●\n", style=wire)
    out.append("           ╰─────────╯\n", style=wire)
    out.append("    ●────────────────────●", style=wire)
    return out
