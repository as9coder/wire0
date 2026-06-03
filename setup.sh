#!/usr/bin/env bash
# Wire0 one-click installer — chmod +x setup.sh && ./setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORANGE='\033[38;2;212;132;92m'
DIM='\033[2m'
GREEN='\033[32m'
RED='\033[31m'
RESET='\033[0m'

step() { printf "  ${ORANGE}%s${RESET}\n" "$1"; }
ok()   { printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
err()  { printf "  ${RED}✗${RESET} %s\n" "$1"; }

find_python() {
  local c
  for c in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

printf "\n  ${ORANGE}Wire0 Setup${RESET}\n"
printf "  ${DIM}───────────${RESET}\n\n"

step "Looking for Python 3.11+..."
PY="$(find_python)" || {
  err "Python 3.11+ not found."
  printf "\n  ${DIM}Install from https://www.python.org/downloads/${RESET}\n\n"
  exit 1
}
VER="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
ok "Python $VER"

step "Upgrading pip..."
"$PY" -m pip install --upgrade pip -q
ok "pip ready"

step "Installing Wire0..."
"$PY" -m pip install "$ROOT" -q
ok "Wire0 installed"

SCRIPTS="$("$PY" -c 'import sysconfig; print(sysconfig.get_path("scripts"))')"

printf "\n  ${ORANGE}■  Wire0 is ready${RESET}\n\n"
printf "  ${DIM}Run anywhere:${RESET}\n"
printf "    wire0\n"
printf "    wire0 ~/myproject\n\n"

case ":$PATH:" in
  *":$SCRIPTS:"*) ;;
  *)
    printf "  ${DIM}If 'wire0' is not recognized, add to PATH:${RESET}\n"
    printf "    %s\n\n" "$SCRIPTS"
    printf "  ${DIM}Or run:${RESET}\n"
    printf "    %s -m wire0\n\n" "$PY"
    ;;
esac

printf "  ${DIM}Set your OpenRouter key on first run with /key${RESET}\n\n"
