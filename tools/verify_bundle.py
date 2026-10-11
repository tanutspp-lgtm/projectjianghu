#!/usr/bin/env python3
"""Local static smoke + source/assets integrity checks. No network or DB required."""
from pathlib import Path
import csv, hashlib, os, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
expected=[ROOT/'client/index.html',ROOT/'client/online_config.js',ROOT/'client/character_manifest.json',ROOT/'client/assets/forest/forest_master_original.png', ROOT/'client/assets/backgrounds/bg_00_sky.png',ROOT/'client/assets/backgrounds/bg_04_foreground_leaves.png',ROOT/'server/server.py',ROOT/'server/requirements.txt']
for item in expected:
    if not item.is_file():raise SystemExit(f'MISSING: {item.relative_to(ROOT)}')
assert len(list((ROOT/'client/characters').glob('*.png')))==30,'30 full character sheets expected'
assert len(list((ROOT/'client/character_previews').glob('*.webp')))==30,'30 previews expected'
assert len(list((ROOT/'client/assets/backgrounds').glob('*.png')))==6,'sky/cloud source + other parallax layers expected'
with (ROOT/'database/exp_v1_character_levels.csv').open(newline='',encoding='utf-8') as f:lev=list(csv.DictReader(f))
with (ROOT/'database/exp_v1_monster_base.csv').open(newline='',encoding='utf-8') as f:mon=list(csv.DictReader(f))
with (ROOT/'database/exp_v1_gap_rules.csv').open(newline='',encoding='utf-8') as f:gap=list(csv.DictReader(f))
assert len(lev)==60 and len(mon)==60 and len(gap)==7
assert int(lev[-2]['equivalent_monster_kills'])==285120 and int(lev[-1]['cumulative_exp_to_reach_level'])==237308585
# Hash manifest ensures assets/source have not silently changed in handoff archive.
for n,line in enumerate((ROOT/'MANIFEST_SHA256.txt').read_text('utf-8').splitlines(),1):
    if not line.strip() or line.startswith('#'):continue
    expected_hash, relpath=line.split('  ',1)
    path=ROOT/relpath
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected_hash:
        raise SystemExit(f'BAD HASH or MISSING file (line {n}): {relpath}')
print('BUNDLE OK: files hashed; 30 full sprites; 30 previews; forest/parallax; server; EXP level tables 60/60/7')
