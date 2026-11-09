#!/usr/bin/env bash
# Run the Black History Hub on macOS or Linux: starts the backend and opens the app.
# First run creates backend/.venv and installs requirements (needs Python 3.10+).
# Uses port 8000, or the next free port if 8000 is busy: PORT=8001 ./start.sh to prefer another.
# Press Ctrl+C to stop the server.
set -e
cd "$(dirname "$0")"

VENV="backend/.venv"
PY="$VENV/bin/python"

# Recreate the virtual environment if it exists but its Python no longer runs.
if [ -e "$PY" ] && ! "$PY" -c 'import sys' >/dev/null 2>&1; then
  echo "The virtual environment in $VENV is broken. Recreating it..."
  rm -rf "$VENV"
fi

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

# launch.py picks a free port, starts the server and opens the browser once it answers.
exec "$PY" backend/launch.py
