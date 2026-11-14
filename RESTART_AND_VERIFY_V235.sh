#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin="$(command -v python3)"; fi
"$python_bin" - <<'PY'
import ast
from pathlib import Path
for p in Path('.').glob('*.py'):
    ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p))
import server
assert server.START_MAP == 'BAM_START_01'
assert len(server.BAMBOO_START_IDS) == 4
assert not any(x.startswith('bamboo_') for x in server.PUBLIC_MAP_IDS)
for mid in server.BAMBOO_START_IDS:
    assert server.BAMBOO_MONSTER_SLOTS[mid]
    assert all(x['kind']=='bamboo_spirit' for x in server.BAMBOO_MONSTER_SLOTS[mid])
print('PASS: installed backend V235, new bamboo maps and monster manifests')
PY
service_dir="$(systemctl show jianghu.service -p WorkingDirectory --value)"
if [[ "$(realpath "$service_dir")" != "$PWD" ]]; then
  echo 'jianghu.service points to a different folder; not restarted.' >&2
  exit 1
fi
systemctl restart jianghu.service
"$python_bin" - <<'PY'
import time, urllib.request
for attempt in range(30):
    try:
        body=urllib.request.urlopen('http://127.0.0.1:8765/healthz',timeout=2).read().decode()
        if 'JIANGHU_BACKEND_V235 bamboo-main-v235' in body and 'roster-progress-v1' in body:
            print('PASS: running backend V235 + roster progress'); print(body); break
    except (OSError,ValueError):
        pass
    time.sleep(1)
else:
    raise SystemExit('FAIL: V235 health not ready. Run: journalctl -u jianghu.service -n 60 --no-pager')
PY
