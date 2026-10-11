"""Render-compatible root entry point for the v7.9N server source tree."""
from pathlib import Path
import runpy
import sys


SERVER_DIR = Path(__file__).resolve().parent / "server"
sys.path.insert(0, str(SERVER_DIR))
runpy.run_path(str(SERVER_DIR / "server.py"), run_name="__main__")
