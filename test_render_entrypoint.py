"""Smoke-test the root entry point used by Render without external services."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request


ROOT = Path(__file__).resolve().parent
with socket.socket() as reservation:
    reservation.bind(("127.0.0.1", 0))
    port = reservation.getsockname()[1]

environment = os.environ.copy()
environment.update({"HOST": "127.0.0.1", "PORT": str(port), "ALLOWED_ORIGINS": ""})
process = subprocess.Popen(
    [sys.executable, "server.py"],
    cwd=ROOT,
    env=environment,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
try:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(process.stdout.read() if process.stdout else "server exited")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1) as response:
                assert response.status == 200
                assert response.read().decode("utf-8").strip() == "wuxia-online ok"
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise AssertionError("root Render entrypoint did not become healthy")
finally:
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)

print("RENDER ENTRYPOINT TEST PASSED: root server.py serves /healthz")
