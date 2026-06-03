"""Foreground shell session — merged transcript, batch commands, one tool."""
from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass, field


@dataclass
class ShellResult:
    output: str
    running: bool


@dataclass
class _Entry:
    n: int
    command: str
    output: str
    exit_code: int | None = None
    running: bool = False


@dataclass
class _Session:
    entries: list[_Entry] = field(default_factory=list)
    pending_proc: subprocess.Popen[str] | None = None
    pending_entry: _Entry | None = None
    pending_buf: list[str] = field(default_factory=list)
    pending_thread: threading.Thread | None = None

    def _maybe_cd(self, cmd: str) -> None:
        c = cmd.strip()
        if c.startswith("cd ") and "&&" not in c and ";" not in c:
            target = c[3:].strip().strip('"').strip("'")
            if target:
                os.chdir(os.path.expanduser(target))

    def _transcript(self, extra: str = "") -> str:
        lines = [f"shell · cwd={os.getcwd()} · {len(self.entries)} command(s)"]
        for e in self.entries:
            st = "RUNNING" if e.running else f"exit {e.exit_code if e.exit_code is not None else 0}"
            lines.append(f"\n[{e.n}] $ {e.command}  [{st}]")
            lines.append(e.output.rstrip() or "(no output)")
        if self.pending_entry and self.pending_entry.running:
            lines.append("\n→ command still running — call shell_run with no commands to refresh, or use bg_shell for servers")
        if extra:
            lines.append(extra)
        return "\n".join(lines)

    def _drain(self, proc: subprocess.Popen[str], buf: list[str]) -> None:
        assert proc.stdout
        for chunk in iter(lambda: proc.stdout.read(4096), ""):
            if not chunk:
                break
            buf.append(chunk)

    def refresh(self) -> None:
        if not self.pending_proc or not self.pending_entry:
            return
        if self.pending_proc.poll() is not None:
            if self.pending_thread and self.pending_thread.is_alive():
                self.pending_thread.join(timeout=0.5)
            self.pending_entry.output = "".join(self.pending_buf).rstrip()
            self.pending_entry.exit_code = self.pending_proc.returncode
            self.pending_entry.running = False
            self.pending_proc = None
            self.pending_entry = None
            self.pending_buf.clear()

    def run(self, cmd: str, timeout_sec: float | None = None) -> bool:
        """Returns True if still running."""
        self.refresh()
        if self.pending_proc:
            return True
        self._maybe_cd(cmd)
        n = len(self.entries) + 1
        entry = _Entry(n=n, command=cmd, output="")
        self.entries.append(entry)

        if timeout_sec and timeout_sec > 0:
            proc = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.getcwd()
            )
            buf: list[str] = []
            t = threading.Thread(target=self._drain, args=(proc, buf), daemon=True)
            t.start()
            t.join(timeout_sec)
            if proc.poll() is None:
                entry.output = "".join(buf).rstrip()
                entry.running = True
                self.pending_proc = proc
                self.pending_entry = entry
                self.pending_buf = buf
                self.pending_thread = t
                return True
            t.join(timeout=0.5)
            entry.output = "".join(buf).rstrip()
            entry.exit_code = proc.returncode
            return False

        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        entry.output = (r.stdout or "") + (r.stderr or "")
        entry.exit_code = r.returncode
        return False


_session = _Session()
_lock = threading.Lock()


def run_shell(commands: str | list[str] | None, timeout_sec: float | None = None) -> ShellResult:
    with _lock:
        sess = _session
        sess.refresh()

        if commands is None:
            return ShellResult(sess._transcript(), sess.pending_proc is not None)

        cmds = [commands] if isinstance(commands, str) else list(commands)
        cmds = [c.strip() for c in cmds if c and c.strip()]
        if not cmds:
            return ShellResult(sess._transcript(), sess.pending_proc is not None)

        if sess.pending_proc:
            return ShellResult(
                sess._transcript("\n\nError: previous command still running — refresh with empty shell_run or use bg_shell"),
                True,
            )

        running = False
        for i, cmd in enumerate(cmds):
            t = timeout_sec if i == len(cmds) - 1 else None
            if sess.run(cmd, t):
                running = True
                break
        return ShellResult(sess._transcript(), running)
