#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
project_dir="$(pwd -P)"
python_bin="$project_dir/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin="$(command -v python3)"; fi
"$python_bin" CHECK_BEFORE_RESTART.py
"$python_bin" -c "from pathlib import Path; import character_classes_v181 as c; assert len(c.AVATARS)==8; assert c.row_for('tang','attack',1)==36; assert 'combat-layers-v184-v1' in Path('server.py').read_text(); print('Installed Backend V184 verified')"
matches=()
while read -r unit rest; do
  [[ "$unit" == *.service ]] || continue
  work="$(systemctl show "$unit" -p WorkingDirectory --value 2>/dev/null || true)"
  exec_line="$(systemctl show "$unit" -p ExecStart --value 2>/dev/null || true)"
  if [[ "$work" == "$project_dir" && "$exec_line" == *server.py* ]]; then matches+=("$unit"); fi
done < <(systemctl list-unit-files --type=service --no-legend --no-pager)
if [[ ${#matches[@]} != 1 ]]; then
  printf 'Expected one existing game service for %s; found %s. No service changed.\n' "$project_dir" "${#matches[@]}"
  printf 'Check: systemctl list-units --type=service --all | grep -i jianghu\n'
  exit 1
fi
printf 'Restarting existing service: %s\n' "${matches[0]}"
systemctl restart "${matches[0]}"
for attempt in {1..10}; do
  if "$python_bin" VERIFY_RUNNING_V184.py; then exit 0; fi
  sleep 1
done
systemctl status "${matches[0]}" --no-pager -l
exit 1
