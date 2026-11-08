#!/usr/bin/env bash
# Run the Black History Hub on macOS or Linux: starts the backend and opens the app.
# First run creates backend/.venv and installs requirements (needs Python 3.10+).
# Press Ctrl+C to stop the server.
set -e
cd "$(dirname "$0")"

PORT="${PORT:-8000}"
VENV="backend/.venv"
PY="$VENV/bin/python"
URL="http://127.0.0.1:$PORT/app/"

if [ ! -x "$PY" ]; then
  echo "Setting up $VENV for the first time..."
  if command -v python3 >/dev/null 2>&1; then BASE=python3
  elif command -v python >/dev/null 2>&1; then BASE=python
  else echo "Python 3.10+ is not installed. Install it from https://www.python.org/downloads/ and try again."; exit 1
  fi
  "$BASE" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || { echo "Python 3.10 or newer is needed (found $("$BASE" --version 2>&1))."; exit 1; }
  "$BASE" -m venv "$VENV" || { echo "Could not create the virtual environment. On Debian/Ubuntu, install python3-venv first."; exit 1; }
fi

# Install (or finish installing) the requirements if they are missing.
if ! "$PY" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "Installing the backend requirements..."
  "$PY" -m pip install -q -r backend/requirements.txt \
    || { echo "Could not install the requirements. Check your internet connection and run ./start.sh again."; exit 1; }
fi

# Open the browser a few seconds after the server starts building the database.
( sleep 4
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
  fi ) &

echo "Starting the server at $URL  (press Ctrl+C to stop)"
exec "$PY" -m uvicorn app.main:app --app-dir backend --port "$PORT"
