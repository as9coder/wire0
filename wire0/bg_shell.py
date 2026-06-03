"""Background shells — detached, persistent, full output log, agent-only kill."""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

REGISTRY = Path.home() / ".wire0" / "background"
META_FILE = REGISTRY / "jobs.json"
_lock = __import__("threading").Lock()


def _load() -> dict[str, dict]:
    if not META_FILE.exists():
        return {}
    try:
        data = json.loads(META_FILE.read_text(encoding="utf-8"))
        return {j["id"]: j for j in data.get("jobs", [])}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(jobs: dict[str, dict]) -> None:
    REGISTRY.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps({"jobs": list(jobs.values())}, indent=2) + "\n", encoding="utf-8")


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
            return str(pid) in r.stdout
        os.kill(pid, 0)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _read_log(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _spawn(command: str, log_path: Path, cwd: str) -> subprocess.Popen:
    REGISTRY.mkdir(parents=True, exist_ok=True)
    log_f = open(log_path, "a", encoding="utf-8", errors="replace")
    log_f.write(f"\n--- started {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_f.flush()
    kw: dict = {
        "shell": True,
        "stdout": log_f,
        "stderr": subprocess.STDOUT,
        "cwd": cwd,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kw["start_new_session"] = True
    proc = subprocess.Popen(command, **kw)
    log_f.close()
    return proc


def start(command: str, job_id: str | None = None) -> str:
    if not command.strip():
        return "Error: command required"
    with _lock:
        jobs = _load()
        # avoid duplicate running commands
        for j in jobs.values():
            if _alive(j["pid"]) and j["command"].strip() == command.strip():
                return f"Already running as [{j['id']}]. Use bg_shell output job_id={j['id']}"
        jid = (job_id or uuid.uuid4().hex[:8]).strip()
        if jid in jobs and _alive(jobs[jid]["pid"]):
            return f"Error: job {jid} already running"
        cwd = os.getcwd()
        log_path = REGISTRY / f"{jid}.log"
        proc = _spawn(command, log_path, cwd)
        jobs[jid] = {
            "id": jid,
            "command": command,
            "pid": proc.pid,
            "log": str(log_path),
            "cwd": cwd,
            "started": time.time(),
        }
        _save(jobs)
        return (
            f"Started background job [{jid}] pid={proc.pid}\n"
            f"command: {command}\ncwd: {cwd}\n"
            f"Survives agent turns and CLI exit. bg_shell output anytime for full log."
        )


def _job_status(j: dict) -> str:
    running = _alive(j["pid"])
    log = _read_log(Path(j["log"])).rstrip()
    status = "RUNNING" if running else "EXITED"
    header = f"[{status}] job {j['id']} pid={j['pid']} — {j['command']}"
    meta = f"cwd: {j['cwd']}"
    body = log if log else "(no output yet)"
    return f"{header}\n{meta}\n--- full output ---\n{body}"


def output(job_id: str | None = None) -> str:
    with _lock:
        jobs = _load()
        if not jobs:
            return "(no background jobs)"
        if job_id:
            j = jobs.get(job_id)
            if not j:
                return f"Error: unknown job {job_id}"
            return _job_status(j)
        return "\n\n".join(_job_status(j) for j in jobs.values())


def list_jobs() -> str:
    with _lock:
        jobs = _load()
        if not jobs:
            return "(no background jobs)"
        lines = []
        for j in jobs.values():
            st = "running" if _alive(j["pid"]) else "exited"
            lines.append(f"  {j['id']}  [{st}]  pid={j['pid']}  {j['command']}")
        return "Background jobs:\n" + "\n".join(lines)


def kill(job_id: str | None = None) -> str:
    with _lock:
        jobs = _load()
        if not job_id:
            return "Error: job_id required"
        j = jobs.get(job_id)
        if not j:
            return f"Error: unknown job {job_id}"
        pid = j["pid"]
        if not _alive(pid):
            del jobs[job_id]
            _save(jobs)
            return f"Job [{job_id}] already exited (removed from registry)"
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
            else:
                os.killpg(os.getpgid(pid), 15)
        except (OSError, subprocess.SubprocessError) as e:
            return f"Error killing {job_id}: {e}"
        time.sleep(0.2)
        if _alive(pid):
            return f"Error: failed to kill job [{job_id}] pid={pid}"
        log = _read_log(Path(j["log"])).rstrip()
        del jobs[job_id]
        _save(jobs)
        tail = f"\n--- final output ---\n{log}" if log else ""
        return f"Killed job [{job_id}] pid={pid}{tail}"


def bg_shell(action: str, command: str | None = None, job_id: str | None = None) -> str:
    act = action.lower().strip()
    if act == "start":
        return start(command or "", job_id)
    if act == "output":
        return output(job_id)
    if act == "list":
        return list_jobs()
    if act == "kill":
        return kill(job_id)
    return f"Error: unknown action {action!r} — use start|output|list|kill"
