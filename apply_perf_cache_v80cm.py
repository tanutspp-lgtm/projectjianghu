#!/usr/bin/env python3
"""Jianghu v8.0CL targeted CPU optimization. Default is read-only --check.

Run from repository root, where server.py lives:
    python apply_perf_cache_v80cm.py --check
    python apply_perf_cache_v80cm.py --apply
    python apply_perf_cache_v80cm.py --restore

No combat formula, physics tick, network rate or anti-cheat change.
"""
import argparse
import hashlib
from pathlib import Path
import sys

SRC = Path("server.py")
BACKUP = Path("server.py.v80cl.before_perf_cache.bak")
RULES = (
    (
        "derived=prog.derive_stats(p,hp_reference)",
        "derived=derived_for_snapshot(p)",
    ),
    (
        "p.vx = 205 * move * prog.derive_stats(p,hp_reference)['moveSpeedMultiplier']",
        "p.vx = 205 * move * derived['moveSpeedMultiplier']",
    ),
    (
        "dodge=prog.derive_stats(p,hp_reference)['dodgeVsMonsters']",
        "dodge=derived_for_snapshot(p)['dodgeVsMonsters']",
    ),
)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Validate expected source patterns without modifying files (default)")
    group.add_argument("--apply", action="store_true", help="Apply after validating all 3 substitutions, creating backup")
    group.add_argument("--restore", action="store_true", help="Restore backup (if present)")
    args = parser.parse_args()
    if not SRC.is_file():
        print("ERROR: server.py not found. Run inside Jianghu repository directory.", file=sys.stderr)
        return 1
    if args.restore:
        if not BACKUP.is_file():
            print(f"ERROR: backup not found: {BACKUP}", file=sys.stderr)
            return 1
        restored = BACKUP.read_text(encoding="utf-8")
        compile(restored, str(SRC), "exec")
        SRC.write_text(restored, encoding="utf-8")
        print(f"Restored {SRC} from {BACKUP} (backup retained).")
        return 0
    original = SRC.read_text(encoding="utf-8")
    patched = original
    for old, new in RULES:
        occurrences = patched.count(old)
        if occurrences != 1:
            print(f"ERROR: expected 1 occurrence, found {occurrences}: {old}", file=sys.stderr)
            print("File might be patched already, or this is a different Jianghu version. No changes made.", file=sys.stderr)
            return 1
        patched = patched.replace(old, new, 1)
    compile(patched, str(SRC), "exec")
    print("Verified all 3 exact replacements and Python syntax.")
    print("Original SHA256:", sha256(original))
    print("Proposed SHA256:", sha256(patched))
    if args.apply:
        if BACKUP.exists():
            print(f"ERROR: backup already exists: {BACKUP}. Refusing to overwrite.", file=sys.stderr)
            return 1
        BACKUP.write_text(original, encoding="utf-8")
        SRC.write_text(patched, encoding="utf-8")
        print(f"Applied patch to {SRC}. Original saved at {BACKUP}.")
    else:
        print("Check only. No files changed. Use --apply to make the patch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
