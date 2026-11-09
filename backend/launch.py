"""Start the Black History Hub backend and open the app once it is ready.

Used by start.bat and start.sh. It picks the first free port from PORT
(default 8000) upwards, starts uvicorn on 127.0.0.1, waits until /health
answers, and only then opens the browser. Set NO_BROWSER=1 to skip opening
the browser.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
REPO_ROOT = Path(__file__).resolve().parent.parent
PORTS_TO_TRY = 20       # 8000, 8001, ... before asking the system for any free port
READY_TIMEOUT = 120     # seconds; the server builds the database before it answers
START_ATTEMPTS = 3      # retries if another program grabs the port while we start

# Talk to our own server directly, never through a system-wide HTTP proxy.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def port_is_free(port: int, host: str = HOST) -> bool:
    """True if nothing answers on host:port and we can bind it ourselves."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex((host, port)) == 0:
            return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


def pick_port(preferred: int, tries: int = PORTS_TO_TRY, host: str = HOST) -> int:
    """The first free port from `preferred` upwards, else any free port."""
    for port in range(preferred, min(preferred + tries, 65536)):
        if port_is_free(port, host):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def wait_until_ready(url: str, proc: subprocess.Popen, timeout: float) -> bool:
    """Poll `url` until it returns 200. False if the server exits or times out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with _opener.open(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except OSError:  # not listening yet, reset, timeout, HTTP error
            pass
        time.sleep(0.5)
    return False


def start_server(port: int) -> subprocess.Popen:
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", "backend",
           "--host", HOST, "--port", str(port)]
    return subprocess.Popen(cmd, cwd=REPO_ROOT)


def main() -> int:
    try:
        preferred = int(os.environ.get("PORT", "8000"))
    except ValueError:
        preferred = 8000

    port = preferred
    for _ in range(START_ATTEMPTS):
        port = pick_port(port)
        if port != preferred:
            print(f"Port {preferred} is already in use, so using port {port} instead.")
        app_url = f"http://{HOST}:{port}/app/"
        print(f"Starting the server on port {port}. The browser opens when it is ready...")
        proc = start_server(port)
        try:
            ready = wait_until_ready(f"http://{HOST}:{port}/health", proc, READY_TIMEOUT)
            if ready:
                print(f"\nBlack History Hub is running at {app_url}")
                print("Close this window or press Ctrl+C to stop.\n")
                if not os.environ.get("NO_BROWSER"):
                    webbrowser.open(app_url)
            elif proc.poll() is None:
                print(f"\nThe server is taking a long time to start. Open {app_url} "
                      "in your browser once it says 'Application startup complete'.\n")
            else:
                if not port_is_free(port):
                    # Another program took the port while we were starting: try the next one.
                    port += 1
                    continue
                print("\nThe server stopped before it was ready. See the messages above.")
                return proc.returncode or 1
            return proc.wait()
        except KeyboardInterrupt:
            # Ctrl+C reaches the server too; give it a moment to shut down cleanly.
            try:
                proc.wait(timeout=10)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                proc.kill()
            return 0
    print("\nCould not find a free port to start the server on.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
