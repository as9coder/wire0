"""Status line — braille spinner + cycling dots."""
from __future__ import annotations

import sys
import threading
import time

_ORANGE = "\033[38;2;212;132;92m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Indicator:
    def __init__(self) -> None:
        self._msg = "Thinking"
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._pause.set()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _clear(self) -> None:
        sys.stdout.write("\r" + " " * 48 + "\r")
        sys.stdout.flush()

    def start(self, msg: str = "Thinking") -> None:
        self.stop()
        with self._lock:
            self._msg = msg
        self._stop.clear()
        self._pause.clear()
        sys.stdout.write(_HIDE_CURSOR)
        sys.stdout.flush()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set(self, msg: str) -> None:
        with self._lock:
            self._msg = msg
        if self._pause.is_set() and not self._stop.is_set():
            self._pause.clear()

    def pause(self) -> None:
        self._pause.set()
        self._clear()

    def resume(self, msg: str = "Thinking") -> None:
        with self._lock:
            self._msg = msg
        self._pause.clear()

    def stop(self) -> None:
        self._stop.set()
        self._pause.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        self._clear()
        sys.stdout.write(_SHOW_CURSOR)
        sys.stdout.flush()

    def _loop(self) -> None:
        spin_i = 0
        dot_i = 0
        last_dot_tick = time.monotonic()
        while not self._stop.is_set():
            if not self._pause.is_set():
                now = time.monotonic()
                if now - last_dot_tick >= 0.45:
                    dot_i = (dot_i + 1) % 3
                    last_dot_tick = now
                with self._lock:
                    msg = self._msg
                f = _FRAMES[spin_i % len(_FRAMES)]
                dots = "." * (dot_i + 1)
                # fixed width so cursor never jumps
                line = f"  {_ORANGE}{f}{_RESET} {_DIM}{msg}{dots:<3}{_RESET}"
                sys.stdout.write("\r" + line)
                sys.stdout.flush()
                spin_i += 1
            time.sleep(0.14)
