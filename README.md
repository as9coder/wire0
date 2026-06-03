# Wire0

Minimal coding agent CLI. Wire your model to the repo.

Wire0 is a small Python REPL that connects an OpenRouter model to your workspace with eight tools — file search, read/write/patch, foreground shell, and detached background shells. It streams responses, runs tools in parallel, and caches prompts for long sessions.

## Requirements

- Python 3.11+
- An [OpenRouter](https://openrouter.ai/) API key

## Setup

```bash
pip install -e .
```

**API key** — prompted on first run, or set anytime with `/key`. Saved to `~/.wire0/config.json`. The `OPENROUTER_API_KEY` environment variable overrides the saved key.

## Run

```powershell
.\run.ps1              # Windows — installs editable package and launches (uses Python 3.13 if present)
wire0                    # workspace = current directory
wire0 D:\myproject       # workspace = specific path
wire0 --plain            # skip experimental welcome screen
```

## CLI

| Input | Action |
|-------|--------|
| `/key` | Prompt for OpenRouter API key (hidden input) |
| `/key sk-or-...` | Set key inline |
| `/model` | Show current OpenRouter model id |
| `/model provider/model` | Switch model (any OpenRouter id, saved to config) |
| `/clear` | Reset conversation and cache session |
| `/exit` | Quit |
| **Ctrl+C** (idle) | Quit with styled farewell |
| **Ctrl+C** (agent running) | Interrupt current turn — CLI stays open |

Prompt history is stored in `~/.wire0_history`.

### Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | Overrides saved key |
| `WIRE0_MODEL` | `openrouter/owl-alpha` | OpenRouter model id |
| `WIRE0_CACHE_TTL` | `1h` | Prompt cache TTL (`ephemeral`) |
| `WIRE0_TUI` | `1` | Set to `0` to disable welcome screen |

## Tools

All tools accept **batch arguments** — the agent is instructed to pass arrays of paths, patches, or commands in a single call rather than looping one item per turn.

| Tool | Purpose |
|------|---------|
| `grep` | Regex search across files/dirs (`include="*.py"`, `ignore_case`) |
| `list_dir` | List directory contents |
| `read_file` | Read files with line numbers (`offset`, `limit`) |
| `patch_file` | Surgical edit — replace unique `old` string with `new` |
| `write_file` | Create or overwrite files (new files only; prefer patch for edits) |
| `delete_path` | Delete files or directories |
| `shell_run` | **Foreground** shell — one persistent session, merged transcript |
| `bg_shell` | **Detached** shell — long-running servers, survives CLI exit |

### `shell_run` vs `bg_shell`

- **`shell_run`** — sync work: tests, builds, git, installs. One session per CLI lifetime. Batch with `commands=["npm install","npm test"]`. Call with no commands to refresh a still-running command. Not for servers.
- **`bg_shell`** — async work: dev servers, docker, watch mode. Actions: `start`, `output`, `list`, `kill`. Jobs live in `~/.wire0/background/` and persist after you exit Wire0.

## How it works

Each turn:

1. Workspace path and file tree (names only) are injected into the system prompt.
2. The model streams a response; tool calls run in parallel (up to 8 workers).
3. Tool results are appended and the loop continues until the model stops calling tools.
4. OpenRouter prompt caching keeps system instructions, tool schemas, and session stable across turns.

The TUI shows a braille spinner while thinking, tool names while working, streamed assistant text, and dim cache stats when available.

## Project layout

```
wire0/
  cli.py              # REPL, spinner, Ctrl+C interrupt, farewell
  llm.py              # OpenRouter streaming + tool loop
  tools.py            # Tool implementations and JSON schemas
  shell.py            # Foreground shell session (merged transcript)
  bg_shell.py         # Detached background jobs
  cache.py            # OpenRouter prompt caching
  workspace.py        # Workspace path + file tree for context
  config.py           # API key in ~/.wire0/config.json
  spinner.py          # Braille status indicator
  tui_experimental.py # Optional welcome screen (opt out with --plain or WIRE0_TUI=0)
```

## Config on disk

| Path | Contents |
|------|----------|
| `~/.wire0/config.json` | OpenRouter API key |
| `~/.wire0/background/` | Background job registry and logs |
| `~/.wire0_history` | CLI prompt history |
