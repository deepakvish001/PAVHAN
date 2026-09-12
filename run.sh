#!/usr/bin/env bash
# PAVHAN — start the API and the app together.
#   ./run.sh            start both (API :8000, app :5173)
#   ./run.sh backend    API only
#   ./run.sh frontend   app only
#   ./run.sh test       run the API smoke test against a running server
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-all}"

start_backend() {
  echo "→ Starting the PAVHAN API on http://127.0.0.1:8000 (docs at /docs)"
  cd "$ROOT/backend"
  [ -d .venv ] || python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q -r requirements.txt
  exec python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

start_frontend() {
  echo "→ Starting the PAVHAN app on http://127.0.0.1:5173"
  cd "$ROOT/frontend"
  [ -d node_modules ] || npm install
  exec npm run dev
}

case "$MODE" in
  backend)  start_backend ;;
  frontend) start_frontend ;;
  test)
    cd "$ROOT/backend" && exec python3 tests/smoke_test.py ;;
  all)
    start_backend &
    BACKEND_PID=$!
    trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT INT TERM
    sleep 4
    start_frontend
    ;;
  *)
    echo "Usage: ./run.sh [all|backend|frontend|test]" >&2
    exit 1 ;;
esac
