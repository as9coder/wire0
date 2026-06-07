# Wire0

Minimal coding agent CLI. Wire your model to the repo.

Wire0 is a small Python REPL that connects an [OpenRouter](https://openrouter.ai/) model to your workspace with eight tools — file search, read/write/patch, foreground shell, and detached background shells. It streams responses, runs tools in parallel, and caches prompts for long sessions.

## Requirements

- Python 3.11+
- An [OpenRouter](https://openrouter.ai/) API key

## Quick start

### pip (recommended)

```bash
pip install wire0
wire0
```

### Windows (from source)

```powershell
git clone https://github.com/as9coder/wire0.git
cd wire0
.\setup.bat
```

### macOS / Linux (from source)

```bash
git clone https://github.com/as9coder/wire0.git
cd wire0
chmod +x setup.sh && ./setup.sh
```

### Manual install from clone

```bash
pip install .
# or editable:
pip install -e .
```

**API key** — prompted on first run, or set anytime with `/key`. Saved to `~/.wire0/config.json`. The `OPENROUTER_API_KEY` environment variable overrides the saved key.

> If you used the old **Agent0** name, Wire0 auto-imports `~/.agent0/config.json` on first run.

## Run

```powershell
wire0                    # workspace = current directory
wire0 D:\myproject       # workspace = specific path
wire0 --plain            # skip welcome screen
```

**Dev launcher** (editable install from clone):

```powershell
.\run.ps1
```

## CLI

| Input | Action |
|-------|--------|
| `/key` | Prompt for OpenRouter API key (hidden input) |
| `/key sk-or-...` | Set key inline |
| `/model` | Show current OpenRouter model id |
| `/model provider/model` | Switch model (any OpenRouter id, saved to config) |
| `/context` or `/ctx` | Show context usage (limit + filled tokens from OpenRouter) |
| `/clear` | Reset conversation and cache session |
| `/exit` | Quit |
| **Ctrl+C** (idle) | Quit with styled farewell |
| **Ctrl+C** (agent running) | Interrupt current turn — CLI stays open |

Prompt history is stored in `~/.wire0_history`.

`/context` fetches the model's context limit from OpenRouter's models API and counts current prompt tokens via a minimal usage probe (~1 output token).

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

## Troubleshooting

### `ModuleNotFoundError: No module named 'wire0'`

The `wire0` command exists but the package install is broken. From the repo folder:

```powershell
.\repair.bat
```

Or manually:

```bash
pip install /path/to/wire0 --force-reinstall
```

### `wire0` not recognized

Add Python's Scripts folder to your PATH, or run:

```bash
python -m wire0
```

## Development

```bash
pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

CI runs tests on Ubuntu and Windows with Python 3.11 and 3.12.

### Publish to PyPI (maintainers)

```powershell
$env:TWINE_PASSWORD = "pypi-..."   # token from pypi.org/manage/account/token/
.\publish.ps1
```

Or add `PYPI_API_TOKEN` to GitHub repo secrets — pushes to `v*` tags auto-publish via `.github/workflows/publish.yml`.

## Project layout

```
wire0/
  cli.py              # REPL, commands, Ctrl+C interrupt
  llm.py              # OpenRouter streaming + tool loop
  tools.py            # Tool implementations and JSON schemas
  context.py          # /context — OpenRouter usage + limits
  logo.py             # ASCII wordmark
  shell.py            # Foreground shell session
  bg_shell.py         # Detached background jobs
  cache.py            # OpenRouter prompt caching
  workspace.py        # Workspace path + file tree
  config.py           # API key + model in ~/.wire0/config.json
  spinner.py          # Braille status indicator
  tui_experimental.py # Optional welcome screen
setup.bat / setup.sh  # One-click install
repair.bat / repair.ps1  # Fix broken global install
```

## Config on disk

| Path | Contents |
|------|----------|
| `~/.wire0/config.json` | OpenRouter API key and saved model |
| `~/.wire0/background/` | Background job registry and logs |
| `~/.wire0_history` | CLI prompt history |

## License

MIT — see [LICENSE](LICENSE).
