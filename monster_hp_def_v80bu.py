"""Immutable server-authoritative monster HP/DEF mirrored from Offline v8.0AO table.
The reference 2-4 hit TTK is a QA benchmark, not fixed percent damage.
"""
import json
from pathlib import Path

RAW = json.loads(Path(__file__).with_name('monster_hp_def_v80bu.json').read_text('utf-8'))
TABLE = {r['level']:r for r in RAW['presets']}
assert set(TABLE) == set(range(1,61))

def preset(level, humanoid=False):
    if type(level) is not int or not 1 <= level <= 60:raise ValueError('monster level must be 1..60')
    row=TABLE[level]['humanoid' if humanoid else 'normal']
    return row['hp'],row['defense']
