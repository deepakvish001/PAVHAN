#!/usr/bin/env bash
# PAVHAN launcher.
#
#   ./run.sh            ONE PORT. Builds the app and serves everything from
#                       http://localhost:8000 — simplest, and the microphone
#                       works because the origin is localhost.
#   ./run.sh dev        Two ports, hot reload: API :8000, app :5173.
#   ./run.sh backend    API only.
#   ./run.sh test       Run the API smoke test against a running server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-start}"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "✗ Python 3 was not found. Install Python 3.10+ and try again." >&2
  exit 1
fi

setup_backend() {
  cd "$ROOT/backend"
  if [ ! -d .venv ]; then
    echo "→ Creating the Python environment (first run only)…"
    "$PY" -m venv .venv
  fi
  # shellcheck disable=SC1091
  if [ -f .venv/bin/activate ]; then source .venv/bin/activate
  else source .venv/Scripts/activate   # Git Bash on Windows
  fi
  echo "→ Installing Python packages…"
  python -m pip install -q --upgrade pip
  python -m pip install -q -r requirements.txt
}

build_frontend() {
  cd "$ROOT/frontend"
  if ! command -v npm >/dev/null 2>&1; then
    echo "✗ npm was not found. Install Node.js 18+ from https://nodejs.org" >&2
    exit 1
  fi
  [ -d node_modules ] || { echo "→ Installing npm packages (first run only)…"; npm install; }
  echo "→ Building the app…"
  npm run build
}

case "$MODE" in
  start)
    setup_backend
    build_frontend
    cd "$ROOT/backend"
    echo
    echo "════════════════════════════════════════════════════════"
    echo "  PAVHAN is running."
    echo
    echo "    App   →  http://localhost:8000"
    echo "    API   →  http://localhost:8000/docs"
    echo
    echo "  Open it in Chrome or Edge. Use the localhost address"
    echo "  exactly as printed — browsers switch the microphone"
    echo "  off on any other address that is not https."
    echo "════════════════════════════════════════════════════════"
    echo
    exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;

  dev)
    setup_backend
    cd "$ROOT/backend"
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
    BACKEND_PID=$!
    trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT INT TERM
    sleep 4
    cd "$ROOT/frontend"
    [ -d node_modules ] || npm install
    echo "→ App on http://localhost:5173 (API proxied from :8000)"
    exec npm run dev
    ;;

  backend)
    setup_backend
    cd "$ROOT/backend"
    exec python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ;;

  frontend)
    cd "$ROOT/frontend"
    [ -d node_modules ] || npm install
    exec npm run dev
    ;;

  test)
    cd "$ROOT/backend"
    if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi
    exec python tests/smoke_test.py
    ;;

  *)
    echo "Usage: ./run.sh [start|dev|backend|frontend|test]" >&2
    exit 1 ;;
esac
