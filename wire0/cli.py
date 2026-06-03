"""Minimal clean TUI for Wire0."""
from __future__ import annotations

import json
import signal
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from rich.console import Console

from wire0 import __version__
from wire0.config import get_api_key, get_model, mask_key, set_api_key, set_model
from wire0.context import clear_model_cache, fetch_context_info
from wire0.llm import chat
from wire0.spinner import Indicator
from wire0.tools import set_root

try:
    from wire0 import tui_experimental as _tui
except ImportError:
    _tui = None  # type: ignore[assignment]

from wire0.logo import ORANGE, logo_text


class UI:
    def __init__(self, model: str, cwd: Path) -> None:
        self.console = Console(highlight=False, soft_wrap=True)
        self.model = model
        self.cwd = cwd
        self.messages: list[dict[str, Any]] = []
        self.session_id = str(uuid.uuid4())
        self.streaming = False
        self.spin = Indicator()
        self._cancel = threading.Event()
        self._busy = False
        hist = Path.home() / ".wire0_history"
        self.session = PromptSession(history=FileHistory(str(hist)))
        self._secret = PromptSession()
        signal.signal(signal.SIGINT, self._sigint)

    def _sigint(self, signum: int, frame: object) -> None:
        if self._busy:
            self._cancel.set()
            raise KeyboardInterrupt
        raise KeyboardInterrupt

    def _end_stream(self) -> None:
        if self.streaming:
            self.console.print()
            self.streaming = False

    def _short_args(self, args: str, n: int = 72) -> str:
        try:
            s = json.dumps(json.loads(args), separators=(",", ":"))
        except json.JSONDecodeError:
            s = args
        return s if len(s) <= n else s[: n - 1] + "…"

    def _short_result(self, text: str, n: int = 100) -> str:
        line = text.split("\n", 1)[0].strip()
        return line if len(line) <= n else line[: n - 1] + "…"

    def _wait(self) -> None:
        self._end_stream()
        self.spin.resume("Thinking")

    def _token(self, tok: str) -> None:
        if not self.streaming:
            self.spin.pause()
            self.console.print()
            self.streaming = True
        self.console.print(tok, end="")

    def _finish_assistant(self) -> None:
        self._end_stream()

    def _tool(self, name: str, args: str) -> None:
        self._end_stream()
        self.spin.set(f"Working · {name}")
        self.console.print(f"  [bold]· {name}[/bold]  {self._short_args(args)}")

    def _tool_result(self, name: str, result: str) -> None:
        err = result.startswith("Error")
        if err:
            self.console.print(f"  [red]→ {self._short_result(result)}[/red]")
        else:
            self.console.print(f"  → {self._short_result(result)}")
        self.spin.set("Thinking")

    def _cache(self, stats: dict[str, int]) -> None:
        c, p, w = stats["cached"], stats["prompt"], stats["written"]
        if c:
            self.console.print(f"  [dim]cache {c}/{p} tok[/dim]")
        elif w:
            self.console.print(f"  [dim]cache write {w} tok[/dim]")

    def _error(self, msg: str) -> None:
        self.spin.stop()
        self._end_stream()
        self.console.print(f"[red]error[/]  {msg}")

    def _trim_incomplete(self) -> None:
        while self.messages:
            role = self.messages[-1].get("role")
            if role == "tool":
                self.messages.pop()
            elif role == "assistant":
                self.messages.pop()
            else:
                break

    def _interrupted(self) -> None:
        self.console.print()
        self.console.print(f"  [bold {ORANGE}]Agent Interrupted[/bold {ORANGE}]")
        self.console.print()

    def _farewell(self) -> None:
        self.console.print()
        self.console.print(f"  [{ORANGE}]■[/]  [bold]Wire0[/bold] [dim]closed[/dim]")
        self.console.print()

    def _prompt_key(self, inline: str = "", tui: bool = False) -> bool:
        key = inline.strip()
        if not key:
            p = _tui.key_prompt_html() if tui and _tui else "<style fg='#888'>key</style> "
            key = self._secret.prompt(HTML(p), is_password=True).strip()
        if not key:
            return False
        set_api_key(key)
        self.console.print(f"[dim]saved {mask_key(key)}[/dim]")
        return True

    def _ensure_key(self, tui: bool = False) -> bool:
        if get_api_key():
            return True
        if not tui:
            self.console.print("[yellow]no api key[/yellow]  [dim]/key[/dim]")
        return self._prompt_key(tui=tui)

    def _show_context(self) -> None:
        if not self._ensure_key():
            return

        self.console.print("[dim]context[/dim]  fetching from OpenRouter…")
        try:
            info = fetch_context_info(self.model, self.messages, self.session_id)
        except Exception as e:
            self._error(str(e))
            return

        title = info.model_name or info.model
        self.console.print(f"[dim]context[/dim]  [bold]{title}[/bold]")
        self.console.print(f"  [dim]{info.model}[/dim]")

        if info.context_limit:
            ratio = info.fill_ratio or 0
            width = 24
            filled = int(ratio * width)
            bar = f"[{ORANGE}]{'█' * filled}[/][dim]{'░' * (width - filled)}[/]"
            pct = int(ratio * 100)
            color = ORANGE if pct < 75 else ("#d4a05c" if pct < 90 else "#c45c5c")
            self.console.print(
                f"  {bar}  [{color}]{info.prompt_tokens:,}[/] / {info.context_limit:,}  ({pct}%)"
            )
        else:
            self.console.print(f"  [bold]{info.prompt_tokens:,}[/] [dim]prompt tokens[/dim]")
            self.console.print("  [dim]context limit unavailable for this model[/dim]")

        if info.cached_tokens:
            self.console.print(f"  [dim]cached {info.cached_tokens:,} tok[/dim]")
        self.console.print(f"  [dim]{len(self.messages)} message(s) in session[/dim]")

    def run_turn(self, user_text: str) -> None:
        if not self._ensure_key():
            return
        self.messages.append({"role": "user", "content": user_text})
        self._cancel.clear()
        self._busy = True
        self.spin.start("Thinking")
        try:
            self.messages = chat(
                self.messages,
                model=self.model,
                session_id=self.session_id,
                on_token=self._token,
                on_tool=self._tool,
                on_tool_result=self._tool_result,
                on_cache=self._cache,
                on_wait=self._wait,
                cancel=self._cancel,
            )
            self._finish_assistant()
        except KeyboardInterrupt:
            self._cancel.set()
            self._trim_incomplete()
            self._finish_assistant()
            self._interrupted()
        except Exception as e:
            self._finish_assistant()
            self._error(str(e))
        finally:
            self._busy = False
            self.spin.stop()

    def repl(self) -> None:
        use_tui = _tui is not None and _tui.enabled()
        if use_tui:
            _tui.show_welcome(self.console, __version__, self.model, self.cwd)
            if not get_api_key():
                self.console.print("[dim]openrouter key[/dim]")
                self._ensure_key(tui=True)
            _tui.footer(self.console)
            prompt_html = HTML(_tui.input_prompt_html())
        else:
            self.console.print(logo_text())
            self.console.print(f"[dim]v{__version__} · {self.model}[/dim]")
            self.console.print(f"[dim]{self.cwd}[/dim]")
            self.console.print("[dim]/key · /model · /context · /clear · /exit[/dim]\n")
            if not get_api_key():
                self._ensure_key()
            prompt_html = HTML("<style fg='#6b7280'>❯</style> ")
        while True:
            try:
                text = self.session.prompt(prompt_html).strip()
            except (EOFError, KeyboardInterrupt):
                self._farewell()
                break
            if not text:
                continue
            if text in ("/exit", "/quit", "exit", "quit"):
                self._farewell()
                break
            if text == "/clear":
                self.messages.clear()
                self.session_id = str(uuid.uuid4())
                self.console.print("[dim]cleared[/dim]")
                continue
            if text == "/key" or text.startswith("/key "):
                self._prompt_key(text[4:].strip() if text.startswith("/key ") else "", tui=use_tui)
                continue
            if text == "/model" or text.startswith("/model "):
                arg = text[6:].strip() if text.startswith("/model ") else ""
                if not arg:
                    self.console.print(f"[dim]model[/dim]  {self.model}")
                    continue
                set_model(arg)
                self.model = get_model()
                self.session_id = str(uuid.uuid4())
                clear_model_cache()
                self.console.print(f"[dim]model[/dim]  {self.model}")
                continue
            if text in ("/context", "/ctx"):
                self._show_context()
                continue
            self.run_turn(text)


def main() -> None:
    cwd = Path.cwd()
    args = [a for a in sys.argv[1:] if a != "--plain"]
    if args and not args[0].startswith("-"):
        cwd = Path(args[0]).resolve()
    set_root(cwd)
    model = get_model()
    UI(model=model, cwd=cwd).repl()


if __name__ == "__main__":
    main()
