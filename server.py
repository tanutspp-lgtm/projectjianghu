"""WUXIA Flute Arena guest-only authoritative arena server.
Browser inputs are UNTRUSTED. Position, damage, HP, monsters, cooldowns are server-owned.
Runs on Python 3.11+ with websockets>=15.
"""
import asyncio
import gc
from pathlib import Path
import json
import math
import os
import secrets
import struct
import time
from collections import deque, defaultdict
from collections.abc import MutableMapping, MutableSequence
from contextvars import ContextVar
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Optional

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed
import random
import compact_wire_v80du as packed_wire
# EK: optional native accelerated JSON metadata serializer, fallback to exact
# original DU encoder when orjson is not installed or cannot encode a value.
try:
    import orjson as _ek_orjson
except ImportError:
    _ek_orjson = None


def encode_compact_snapshot_ek(packet, cache=None):
    if _ek_orjson is None:
        return packed_wire.encode_snapshot(packet, cache)
    try:
        meta = {k:v for k,v in packet.items() if k not in packed_wire.KINDS}
        mb = _ek_orjson.dumps(meta)  # UTF-8, same decoded JSON semantics
    except (TypeError, ValueError, OverflowError):
        return packed_wire.encode_snapshot(packet, cache)
    out = bytearray(packed_wire.MAGIC)
    out.extend(struct.pack('<I', len(mb)))
    out.extend(mb)
    for kind in packed_wire.KINDS:
        entries=packet.get(kind, ())
        out.extend(packed_wire.uvar(len(entries)))
        for entry in entries:
            out.extend(packed_wire.entity_bytes(kind, entry, cache))
    return bytes(out)
import combat_progression_v80bs as prog
import sandbox_loadouts_v80bt as loadouts
import monster_hp_def_v80bu as monster_balance
import farm_auto_v80bu as farm_auto
from urllib.request import Request, urlopen  # v8.0BO AUTHORITATIVE COMBAT

"""Project Jianghu PvP-first reference combat data; read-only Supabase mirror.

Server owns level, armor and hits. Never accept client damage/level/gear.
Balances are loaded from two RLS read-only Supabase tables at boot (optional),
with identical local v8.0BN calculations as a safe fallback on outage.
This does NOT implement persisted Online inventory/level progression.
"""
import json
import math
import os


ANCHORS=((1,1200),(5,1300),(10,1700),(14,1980),(15,2067),(20,3250),
         (25,3460),(29,3690),(30,3850),(35,3950),(40,4000),(50,4150),(60,4300))
TIERS={0:(0,0),5:(14,84),15:(60,207),30:(111,381),40:(162,545)}  # (DEF, flat gear HP)
PCT={('common',False):(7,9),('common',True):(8,10),
     ('premium',False):(12,14),('premium',True):(14,16),
     ('manual',False):(15,17),('manual',True):(18,20)}
REDUCTION_K=250
BALANCE_VERSION='v8.0BN-pvp-first'
_remote_hp=None
_remote_attacks=None
source='local-v8.0BN'


def _round_pos(v):
    return int(math.floor(v+0.5))  # JavaScript Math.round for nonnegative numbers


def hp_reference(level):
    if not isinstance(level,int) or not 1<=level<=60:
        raise ValueError('combat level must be 1..60')
    if _remote_hp is not None: return _remote_hp[level]
    for (la,ha),(lb,hb) in zip(ANCHORS,ANCHORS[1:]):
        if level<=lb:
            hp=_round_pos(ha+(hb-ha)*(level-la)/(lb-la))
            break
    tier=0 if level<5 else 5 if level<15 else 15 if level<30 else 30 if level<40 else 40
    defense,gear_hp=TIERS[tier]
    return {'level':level,'gear_tier':tier,'max_hp':hp,'gear_hp':gear_hp,
            'defense_0':defense,'defense_5':defense+(25 if tier else 0),
            'defense_7':defense+(35 if tier else 0)}


def monster_attack_range(level,mode='common',humanoid=False):
    if (mode,bool(humanoid)) not in PCT: raise ValueError('bad zone mode')
    ref=hp_reference(level)
    if _remote_attacks is not None:
        return _remote_attacks[(level,mode,bool(humanoid))]
    lo,hi=PCT[(mode,bool(humanoid))]
    raw_min=max(1,_round_pos(ref['max_hp']*lo/100*(REDUCTION_K+ref['defense_7'])/REDUCTION_K))
    raw_max=max(raw_min,_round_pos(ref['max_hp']*hi/100*(REDUCTION_K+ref['defense_0'])/REDUCTION_K))
    return (raw_min,raw_max)


def mitigate(raw,defense):
    if raw<=0: return 0
    return max(1,_round_pos(raw*REDUCTION_K/(REDUCTION_K+max(0,defense))))


def load_from_supabase():
    """Read immutable combat reference. Inability to reach Supabase must not kill the arena."""
    global _remote_hp,_remote_attacks,source
    # Publishable key is designed for public clients; RLS limits these tables to read-only.
    # Render env vars can override both defaults at any time. NEVER embed service_role.
    base=os.environ.get('SUPABASE_URL','https://uxxkyptoocbswedwizct.supabase.co').rstrip('/')
    key=os.environ.get('SUPABASE_PUBLISHABLE_KEY','sb_publishable_GDhK1Y-OrFCwzWRunfc-UQ_56NeDD4M')
    if not base or not key:
        source='local-v8.0BN (Supabase not configured)'
        return False
    def load(path):
        req=Request(f'{base}/rest/v1/{path}?select=*&limit=1000',headers={'apikey':key,'accept':'application/json'})
        with urlopen(req,timeout=5) as resp:
            result=json.load(resp)
        if not isinstance(result,list): raise ValueError('balance response must be list')
        return result
    try:
        hp=load('jianghu_pvp_hp_v80bo')
        attack=load('jianghu_monster_damage_v80bo')
        hmap={int(row['level']):row for row in hp}
        amap={(int(row['level']),row['mode'],bool(row['humanoid'])):
              (int(row['raw_min']),int(row['raw_max'])) for row in attack}
        if len(hp)!=60 or len(hmap)!=60 or len(attack)!=360 or len(amap)!=360:
            raise ValueError('incomplete balance table; expected 60 HP and 360 damage records')
        if any(row.get('balance_version')!=BALANCE_VERSION for row in hp+attack):
            raise ValueError('unapproved balance version')
        for lv in range(1,61):
            r=hmap[lv]
            if not 0<int(r['max_hp'])<100000 or not 0<=int(r['defense_0'])<=int(r['defense_5'])<=int(r['defense_7'])<10000:
                raise ValueError('invalid armor/HP values')
            for mode,human in PCT:
                low,high=amap[(lv,mode,human)]
                if not 0<low<=high<1000000:raise ValueError('invalid monster raw range')
        _remote_hp=hmap
        _remote_attacks=amap
        source='supabase-v8.0BN'
        return True
    except Exception as exc:
        _remote_hp=None
        _remote_attacks=None
        source='local-v8.0BN (Supabase read failed: '+type(exc).__name__+')'
        return False


PORT = int(os.environ.get('PORT', '8765'))
HOST = os.environ.get('HOST', '0.0.0.0')
ORIGINS = tuple(s.strip() for s in os.environ.get('ALLOWED_ORIGINS', '').split(',') if s.strip())
MAX_GUESTS = int(os.environ.get('MAX_GUESTS', '35'))
# v8.0DP: all options are independent, benchmarkable and reversible.
STAGGER_SLOTS = int(os.environ.get('STAGGER_SLOTS','10'))
if STAGGER_SLOTS not in (10,100): raise ValueError('STAGGER_SLOTS must be 10 or 100')
WS_COMPRESSION = os.environ.get('WS_COMPRESSION','none').lower()
if WS_COMPRESSION not in ('none','deflate'): raise ValueError('WS_COMPRESSION must be none or deflate')
AUTO_BG_SNAP_HZ = int(os.environ.get('AUTO_BG_SNAP_HZ','1'))
if AUTO_BG_SNAP_HZ not in (1,2): raise ValueError('AUTO_BG_SNAP_HZ must be 1 or 2')
# 0 = original map levels (1..5); 1..60 = Offline v8.0AO level preset for ALL beasts.
# Deliberately not controlled by any untrusted client; set on the Render service.
MONSTER_PRESET_LEVEL=int(os.environ.get('MONSTER_PRESET_LEVEL','5'))
if not 0<=MONSTER_PRESET_LEVEL<=60:raise ValueError('MONSTER_PRESET_LEVEL must be 0..60')
# QA loadouts are NOT real obtained gear. Keep disabled on public servers.
ENABLE_GUEST_SANDBOX=os.environ.get('ENABLE_GUEST_SANDBOX','0')=='1'
# Laboratory opt-in; unchanged default DV server-first for all legacy clients.
ENABLE_CLIENT_MOVEMENT_AB=os.environ.get('ENABLE_CLIENT_MOVEMENT_AB','0')=='1'
# EC: server-first only; independent of experimental client movement.
ENABLE_FAST_SELF_30HZ=os.environ.get('ENABLE_FAST_SELF_30HZ','1')=='1'
# EH: Operator opt-in stress test. No token; URL secrecy is NOT security.
# Keep disabled outside deliberate tests; global hard limits still apply.
ENABLE_CHANNEL_STRESS = os.environ.get('ENABLE_CHANNEL_STRESS','0') == '1'
# EJ: pure passive performance tracer; disabled by default. No protocol/gameplay changes.
# Enable only during representative tests, then disable to measure baseline without tracer cost.
ENABLE_PERFORMANCE_PROFILER = os.environ.get('JIANGHU_PROFILE','0') == '1'
# EL: phase each socket AFTER its world sample, never delay a missed wall-clock slot by 100ms.
# Rollback without source changes: JIANGHU_EL_SNAPSHOT_SCHED=0.
ENABLE_EL_SNAPSHOT_SCHED = os.environ.get('JIANGHU_EL_SNAPSHOT_SCHED','0') == '1'
# EO experiment: cap global-slot wait only when explicitly enabled.
# Default OFF (0) preserves EN timing; enable 60ms for controlled live A/B.
try:
    EO_WRITER_WAIT_CAP_MS = float(os.environ.get('JIANGHU_EO_WRITER_WAIT_CAP_MS','0'))
except (TypeError,ValueError):
    EO_WRITER_WAIT_CAP_MS = 0.0
if not 0.0 < EO_WRITER_WAIT_CAP_MS <= 90.0:
    EO_WRITER_WAIT_CAP_MS = 0.0

# EM: keep known-bad EL scheduling disabled by default. Explicit =1 still allows A/B.
# Revision shortcut avoids O(inventory size) equality work every recipient sample.
# Increment revision on EVERY inventory mutation. Rollback: JIANGHU_EM_INVENTORY_REV=0.
ENABLE_EM_INVENTORY_REV = os.environ.get('JIANGHU_EM_INVENTORY_REV','1') == '1'
# EN: event journal hot path. Original scans every old record, for every recipient.
# Reverse-scan only records newer than this recipient's acknowledged cursor.
# Opt-out: JIANGHU_EN_EVENT_SCAN=0 (no client deploy required).
ENABLE_EN_EVENT_SCAN = os.environ.get('JIANGHU_EN_EVENT_SCAN','1') == '1' 
CHANNEL_STRESS_PER_CHANNEL = 200
CHANNEL_STRESS_TOTAL = min(200, MAX_GUESTS)  # global guard; 150 bots + observer on MAX_GUESTS=201

# Generated by the SAME offline monster_spawns_v80au.js; only the server decides spawns.
MAP_DATA = json.loads(Path(__file__).with_name('beast_map_common_v80bq.json').read_text(encoding='utf-8'))
WORLD_W = int(MAP_DATA['worldW'])
DT = 1.0 / 30.0
GROUND = [(p['x'], p['x2'], p['y']) for p in MAP_DATA['platforms']]
CLIMBS = tuple((c['x'], c['top'], c['bottom']) for c in MAP_DATA['climbs'])
# The centre ladder ends at the intermediate walkway, NOT the sky floor.
_EXPECTED_CLIMBS=((510,235,550),(1170,390,550),(1590,235,550))
if CLIMBS != _EXPECTED_CLIMBS:
    raise RuntimeError(f'Unsafe map climbs: {CLIMBS}; expected {_EXPECTED_CLIMBS}')
FARM_NAV=farm_auto.Navigation(GROUND,CLIMBS)
# BAMBOO REAL WORLDS: room-based, same 2060px server-owned coordinate envelope.
# No bamboo mob/loot templates until the owner supplies cropped sprites and manifest.
BAMBOO_MAPS = {'forest': {'name': 'ป่าภูเขาเดิม',
            'platforms': [[0, 2060, 550], [170, 850, 390], [1020, 1770, 390], [410, 1070, 235], [1210, 1970, 235]],
            'climbs': [[510, 235, 550, 'rope'], [1170, 390, 550, 'ladder'], [1590, 235, 550, 'rope']]},
 'bamboo_1': {'name': 'ทางเข้าดงไผ่',
              'platforms': [[0, 2060, 550],
                            [300, 710, 423],
                            [890, 1280, 425],
                            [1440, 1950, 425],
                            [650, 1080, 300],
                            [1340, 1770, 300]],
              'climbs': [[850, 300, 550, 'rope'],
                         [1550, 300, 550, 'ladder'],
                         [470, 423, 550, 'ladder'],
                         [1090, 425, 550, 'ladder'],
                         [1775, 425, 550, 'ladder']]},
 'bamboo_2': {'name': 'ทางเลียบดงไผ่',
              'platforms': [[0, 2060, 550],
                            [240, 660, 430],
                            [840, 1240, 430],
                            [1430, 1950, 430],
                            [470, 890, 305],
                            [1170, 1610, 305]],
              'climbs': [[640, 305, 550, 'ladder'],
                         [1410, 305, 550, 'rope'],
                         [415, 430, 550, 'ladder'],
                         [1040, 430, 550, 'ladder'],
                         [1735, 430, 550, 'ladder']]},
 'bamboo_3': {'name': 'ดงไผ่ริมสวนท้อ',
              'platforms': [[0, 2060, 550],
                            [230, 680, 427],
                            [890, 1350, 425],
                            [1490, 2000, 430],
                            [460, 840, 300],
                            [1130, 1550, 300],
                            [1610, 2000, 180]],
              'climbs': [[650, 300, 550, 'rope'],
                         [1320, 300, 550, 'ladder'],
                         [1810, 180, 430, 'rope'],
                         [420, 427, 550, 'ladder'],
                         [1080, 425, 550, 'ladder'],
                         [1650, 430, 550, 'ladder']]},
 'bamboo_4': {'name': 'ลานฝึกหุบไผ่',
              'platforms': [[0, 2060, 550],
                            [260, 715, 425],
                            [850, 1300, 430],
                            [1460, 1970, 425],
                            [490, 905, 305],
                            [1070, 1510, 305],
                            [900, 1270, 180]],
              'climbs': [[670, 305, 550, 'ladder'],
                         [1170, 180, 550, 'rope'],
                         [1710, 425, 550, 'ladder'],
                         [425, 425, 550, 'ladder'],
                         [1025, 430, 550, 'ladder'],
                         [1620, 425, 550, 'ladder']]},
 'outskirts_1': {'name': 'ทางออกดงไผ่ · ชานเมือง',
               # V5: quiet forest exit and quiet town entrance. Three vertically
               # staggered prefab floating islands only in the world center.
               # Each rope connects adjacent platform heights, no continuous rope.
               'platforms': [[0, 2060, 550], [725, 1380, 355], [825, 1355, 135], [865, 1215, -85]],
               'climbs': [[830, 355, 550, 'rope'], [1190, 135, 355, 'rope'], [965, -85, 135, 'rope']]},
 'suburb_gate_1': {'name':'ชุมชนหน้าประตูเมือง',
                   # Map 7: peaceful town boundary, main floor only, no floating platforms.
                   'platforms': [[0, 2060, 550]],
                   'climbs': []},
 'city_proto_1': {'name':'นครชั้นนอก · ตลาด',
                  'platforms': [[0, 5100, 550]], 'climbs': []},
 'city_inner_1': {'name':'นครชั้นใน · ราชการ',
                  'platforms': [[0, 3700, 550]], 'climbs': []},
 'peach_exit_1': {'name':'ทุ่งท้อเลียบธาร',
                  'platforms': [[0, 2060, 550]], 'climbs': []}}
# Map 11 V21: server-authoritative tileset platform/rope geometry.
# Must match the approved V21 frontend MAP11_GEOMETRY exactly (world width 2400).
BAMBOO_MAPS['forest_fork_11'] = {'name':'ทางแยกป่าและเชิงเขา',
  'platforms':[[0, 2400, 550], [250, 700, 300], [730, 920, 215], [980, 1260, 130], [1320, 1680, 50], [1740, 1970, -25], [1855, 2085, -185], [1960, 2210, -355], [2140, 2400, -445], [2080, 2400, -700]],
  'climbs':[[440, 300, 550, 'rope'], [1900, -185, -25, 'rope'], [2020, -355, -185, 'rope'], [2300, -700, -445, 'rope']]}

# Four forest worlds beyond the lower-right Map11 portal. Scenery-first, no new monster balance.
GRANITE_FOREST_MAPS = {'granite_forest_1': {'name': 'ชายป่าเชิงผา', 'platforms': [[0, 2400, 550], [240, 720, 300], [840, 1340, 300], [1460, 2060, 300], [510, 990, 60], [1110, 1680, 60], [900, 1400, -180]], 'climbs': [[430, 300, 550, 'rope'], [1130, 300, 550, 'rope'], [1890, 300, 550, 'rope'], [650, 60, 300, 'rope'], [1200, 60, 300, 'rope'], [1260, -180, 60, 'rope']]}, 'granite_forest_2': {'name': 'ดงไม้ยักษ์', 'platforms': [[0, 2400, 550], [200, 680, 300], [800, 1320, 300], [1440, 2080, 300], [480, 980, 60], [1100, 1660, 60], [1780, 2240, 60], [1620, 2080, -180]], 'climbs': [[400, 300, 550, 'rope'], [1050, 300, 550, 'rope'], [1870, 300, 550, 'rope'], [600, 60, 300, 'rope'], [1230, 60, 300, 'rope'], [1930, 60, 300, 'rope'], [1980, -180, 60, 'rope']]}, 'granite_forest_3': {'name': 'ช่องแสงกลางพนา', 'platforms': [[0, 2400, 550], [120, 2280, 300], [120, 2280, 60], [120, 2280, -180], [120, 2280, -420]], 'climbs': [[340, 300, 550, 'rope'], [2060, 300, 550, 'rope'], [460, 60, 300, 'rope'], [1940, 60, 300, 'rope'], [580, -180, 60, 'rope'], [1820, -180, 60, 'rope'], [700, -420, -180, 'rope'], [1700, -420, -180, 'rope']]}, 'granite_forest_4': {'name': 'ป่าลึกใต้ผาหิน', 'platforms': [[0, 2400, 550], [200, 680, 300], [800, 1320, 300], [1440, 2070, 300], [430, 930, 60], [1050, 1660, 60], [1780, 2240, 60], [890, 1390, -180], [1520, 2020, -180]], 'climbs': [[350, 300, 550, 'rope'], [1060, 300, 550, 'rope'], [1950, 300, 550, 'rope'], [570, 60, 300, 'rope'], [1230, 60, 300, 'rope'], [1870, 60, 300, 'rope'], [1300, -180, 60, 'rope'], [1950, -180, 60, 'rope']]}}
BAMBOO_MAPS.update(GRANITE_FOREST_MAPS)
MOUNTAIN_MAPS = {'granite_ascent_1': {'name': 'ทางไต่ผาแกรนิต', 'platforms': [[0, 1400, 550], [690, 1030, 310], [935, 1305, 70], [780, 1160, -170], [650, 1000, -410], [900, 1300, -650], [1040, 1380, -890], [800, 1170, -1130], [665, 1050, -1370], [920, 1300, -1610], [1020, 1400, -1850]], 'climbs': [[860, 310, 550, 'ladder'], [982, 70, 310, 'ladder'], [1048, -170, 70, 'ladder'], [890, -410, -170, 'ladder'], [950, -650, -410, 'ladder'], [1170, -890, -650, 'ladder'], [1105, -1130, -890, 'ladder'], [925, -1370, -1130, 'ladder'], [985, -1610, -1370, 'ladder'], [1160, -1850, -1610, 'ladder']]}}
BAMBOO_MAPS.update(MOUNTAIN_MAPS)
GRANITE_WALL_MAPS = {'granite_wall_1': {'name': 'ระเบียงผาแกรนิต', 'platforms': [[0, 2400, 550], [120, 2280, 310], [220, 2180, 70]], 'climbs': [[400, 310, 550, 'ladder'], [2000, 310, 550, 'ladder'], [650, 70, 310, 'ladder'], [1750, 70, 310, 'ladder']]}, 'granite_wall_2': {'name': 'ทางเลียบผารอยแยก', 'platforms': [[0, 2400, 550], [80, 2130, 280], [300, 2320, 10], [1990, 2230, -470]], 'climbs': [[760, 280, 550, 'ladder'], [1830, 280, 550, 'ladder'], [500, 10, 280, 'ladder'], [1500, 10, 280, 'ladder'], [2050, -470, 10, 'ladder']]}, 'granite_summit_1': {'name': 'ยอดเขาแกรนิต', 'platforms': [[0, 2000, 550], [160, 400, 650], [440, 720, 470], [800, 1080, 470], [1320, 1600, 470], [1680, 1960, 470]], 'climbs': [[220, 550, 650, 'ladder']]}}
BAMBOO_MAPS.update(GRANITE_WALL_MAPS)
GRANITE_WALL_PORTALS = {('granite_ascent_1', 'granite_wall_1'): ('right', -1850, 65, 175, 550), ('granite_wall_1', 'granite_ascent_1'): ('left', 550, 125, 1225, -1850), ('granite_wall_1', 'granite_wall_2'): ('right', 550, 125, 175, 550), ('granite_wall_2', 'granite_wall_1'): ('left', 550, 125, 2225, 550)}

WORLD_V56=json.loads((Path(__file__).resolve().parent/'world_v56.json').read_text())
EXPANSION_MAPS=WORLD_V56['maps']
from world_physics_v56 import step as expansion_physics, ground_y as expansion_ground_y, portal_at as expansion_portal_at, dismount as expansion_dismount
BAMBOO_MAPS.update({mid:{'name':m['name'],'platforms':[[p['x'],p['x2'],p['y']] for p in m['platforms']],'climbs':[[c['x'],c['top'],c['bottom'],c.get('type','rope')] for c in m['climbs']]} for mid,m in EXPANSION_MAPS.items()})

PUBLIC_MAP_IDS = ('forest','bamboo_1','bamboo_2','bamboo_3','bamboo_4','outskirts_1','suburb_gate_1','city_proto_1','city_inner_1','peach_exit_1','forest_fork_11',*GRANITE_FOREST_MAPS,*MOUNTAIN_MAPS,*GRANITE_WALL_MAPS,*EXPANSION_MAPS)
# Bamboo newbie monsters: 14 per map/channel (30% reduction from 20).
# Map 1/2: spirit=9,rabbit=5; Map 3/4: spirit=5,rabbit=5,squirrel=4.
BAMBOO_MONSTER_QUOTAS = {
    'bamboo_1': {'bamboo_spirit':9,'bamboo_rabbit':5},
    'bamboo_2': {'bamboo_spirit':9,'bamboo_rabbit':5},
    'bamboo_3': {'bamboo_spirit':5,'bamboo_rabbit':5,'brush_squirrel':4},
    'bamboo_4': {'bamboo_spirit':5,'bamboo_rabbit':5,'brush_squirrel':4},
    'outskirts_1': {'bamboo_spirit':5,'bamboo_rabbit':5,'brush_squirrel':4},
    'peach_exit_1': {'bamboo_spirit':4,'bamboo_rabbit':3,'brush_squirrel':3},
}
BAMBOO_MONSTER_NAMES = {'bamboo_spirit':'หน่อเซียน','bamboo_rabbit':'กระต่ายหูไผ่','brush_squirrel':'กระรอกหางพู่กัน'}
def bamboo_spawn_slots(room):
    quota=BAMBOO_MONSTER_QUOTAS[room]
    kinds=[]
    while len(kinds)<sum(quota.values()):
        for kind in quota:
            if kinds.count(kind)<quota[kind]: kinds.append(kind)
    lanes=BAMBOO_MAPS[room]['platforms']
    entries=[]
    for i,kind in enumerate(kinds):
        idx=i%len(lanes)
        lane=lanes[idx]
        lane_count=len(range(idx,len(kinds),len(lanes)))
        position=i//len(lanes)
        lo,hi,y=lane
        x=lo+65+(hi-lo-130)*(position+1)/(lane_count+1)
        entries.append({'id':f'{room}:mob:{i+1:02}', 'kind':kind,'x':round(x,1),'y':float(y)})
    assert len(entries)==sum(quota.values()) and {k:sum(e['kind']==k for e in entries) for k in quota}==quota
    return tuple(entries)
BAMBOO_MONSTER_SLOTS = {name:bamboo_spawn_slots(name) for name in BAMBOO_MONSTER_QUOTAS}

# Precomputed immutable geometry avoids allocating arrays every 30Hz tick.
BAMBOO_GROUNDS = {mid: tuple((a,b,y) for a,b,y in data['platforms']) for mid,data in BAMBOO_MAPS.items()}
BAMBOO_CLIMBS = {mid: tuple((c[0],c[1],c[2]) for c in data['climbs']) for mid,data in BAMBOO_MAPS.items()}
# Each map has different platforms and climbs. AUTO navigation is server-owned
# and must use the CURRENT player's world, never the original forest route graph.
# Cache once per map (immutable geometry); no per-bot/per-tick graph rebuild.
WORLD_FARM_NAV = {'forest': FARM_NAV, **{
    map_id: farm_auto.Navigation(BAMBOO_GROUNDS[map_id], BAMBOO_CLIMBS[map_id])
    for map_id in BAMBOO_MAPS if map_id != 'forest'
}}
from swamp_pit_nav import MultiPitNavigator
SWAMP_RECOVERY={mid:MultiPitNavigator(m) for mid,m in EXPANSION_MAPS.items() if m['kind']=='swamp'}
class ExpansionNavigation:
    def __init__(self,room,base):self.room,self.base=room,base
    def __getattr__(self,name):return getattr(self.base,name)
    def choose(self,actor,state,now,monsters,allow_cast=True):
        nav=SWAMP_RECOVERY.get(self.room)
        goal=getattr(state,'goal',None)
        if nav:
            decision=nav.choose(actor,(goal['x'],goal['y']) if isinstance(goal,dict) and 'x' in goal and 'y' in goal else None,now)
            if decision is not None:return decision.buttons,list(decision.actions)
            # The raised central bank is continuous ground, not a missing ladder.
            m=EXPANSION_MAPS[self.room];gy=expansion_ground_y(m,actor.x)
            if isinstance(goal,dict) and actor.ground and gy is not None and abs(actor.y-gy)<3 and abs(goal.get('x',actor.x)-actor.x)>12 and not any(q['left']<=actor.x<=q['right'] for q in m['pits']):
                gx=goal['x'];between=[y for x,y in m['profile'] if min(gx,actor.x)<=x<=max(gx,actor.x)]
                if any(y<550 for y in between) or gy<550:return (2 if gx>actor.x else 1),[]
        return self.base.choose(actor,state,now,monsters,allow_cast=allow_cast)
for _mid in EXPANSION_MAPS:WORLD_FARM_NAV[_mid]=ExpansionNavigation(_mid,WORLD_FARM_NAV[_mid])
from late_map_nav_v67 import LateNavigation
for _mid,_map in EXPANSION_MAPS.items():
    if _map.get('region')=='late_v67':WORLD_FARM_NAV[_mid]=LateNavigation(_map)

def farm_nav_for(room):
    return WORLD_FARM_NAV.get(room, FARM_NAV)


def active_ground():
    return BAMBOO_GROUNDS.get(current_world().room, GROUND)
def active_climbs():
    # The diagonal city stairs are handled by a separate server-owned spline,
    # not by the rope/ladder movement or AUTO route logic.
    if current_world().room in ('city_proto_1','city_inner_1'): return ()
    return BAMBOO_CLIMBS.get(current_world().room, CLIMBS)

GRANITE_SUMMIT_LADDER_LINKS = {('granite_wall_2', 'granite_summit_1'): (-1, 2050, -470, 10, 25, 267, 550), ('granite_summit_1', 'granite_wall_2'): (1, 220, 550, 650, 25, 2097, 10)}

def city_world_width(room):
    if room in EXPANSION_MAPS:return EXPANSION_MAPS[room]['worldWidth']
    return 2000 if room=='granite_summit_1' else 1400 if room in MOUNTAIN_MAPS else 2400 if room == 'forest_fork_11' or room in GRANITE_FOREST_MAPS or room in GRANITE_WALL_MAPS else (5100 if room == 'city_proto_1' else (3700 if room == 'city_inner_1' else WORLD_W))

def map_payload(map_id):
    data=BAMBOO_MAPS[map_id]
    return {'map':map_id,'mapName':data['name'],
            'mapPlatforms':[{'x':a,'x2':b,'y':y} for a,b,y in data['platforms']],
            'mapClimbs':[{'x':x,'top':t,'bottom':b,'type':typ} for x,t,b,typ in data['climbs']],
            'mapWidth':city_world_width(map_id)}

ALLOWED_BUTTONS = (1 | 2 | 4 | 8 | 16)
ATTACKS = {'attack': (0.34, 0.32, 520, 165, 1.45, 1), 'aoe': (0.62, 0.48, 365, 135, 1.15, 99), 'break': (0.52, 0.37, 560, 45, 1.1, 2)}
ACTION_NAMES = {'jump', 'dash', 'attack', 'aoe', 'break', 'lock'}
COLORS = {'black', 'white', 'brown', 'red', 'gold'}

def valid_avatar(s):
    if not isinstance(s, str) or len(s) > 24: return False
    bits = s.split('_')
    return len(bits) == 4 and bits[0] in ('male', 'female') and bits[1] == 'hair' and bits[2] in ('01', '02', '03') and bits[3] in COLORS


def clamp(v, lo, hi): return max(lo, min(hi, v))


def can_stand(x, y, prev):
    for lo, hi, top in active_ground():
        if lo + 8 < x < hi - 8 and prev <= top + 7 and y >= top:
            return top
    return None


@dataclass
class Actor:
    id: str
    x: float
    y: float
    hp: int
    max_hp: int
    face: int = -1
    vx: float = 0
    vy: float = 0
    ground: bool = True
    climb: Optional[tuple] = None
    climb_cd: float = 0
    climb_dist: float = 0
    walk_dist: float = 0
    guard: bool = False
    broken: float = 0
    stun: float = 0
    down: float = 0
    dead: float = 0
    inv: float = 0
    cool: float = 0
    action: str = 'idle'
    action_at: float = 0
    action_duration: float = 0


@dataclass
class Guest(Actor):
    ws: object = None
    room: str = 'forest'  # independent forest / movement_lab instances
    channel: int = 1
    map_switch_at: float = 0.0
    stress_test: bool = False
    world_ref: object = None
    stress_status_at: float = 0.0  # EI: throttle stress occupancy probes
    channel_switch_at: float = 0.0
    channel_switch_times: deque = field(default_factory=deque)
    # Map selector requests have their OWN budget; refreshing/changing channels cannot consume it.
    map_request_times: deque = field(default_factory=deque)
    avatar: str = 'male_hair_01_black'
    buttons: int = 0
    last_input: float = field(default_factory=time.monotonic)
    last_seq: int = -1
    packet_times: deque = field(default_factory=deque)
    movement_packet_times: deque = field(default_factory=deque)  # DZ: isolate 20Hz client_move from legacy input limiter
    movement_sync_times: deque = field(default_factory=deque)  # EA: forced recovery probes cannot consume action budget
    action_times: deque = field(default_factory=deque)
    level: int = 5  # server-owned guest training level, not client-controlled
    armor_enhance: int = 5  # server-owned reference +5 armor
    last_attack_at: float = -1e9
    last_damage_at: float = -1e9
    # DJ: Keep firing the same living target until it dies or leaves legal range.
    manual_target_id: Optional[str] = None
    # DK: Single-slot manual spell intent overrides automatic basic attacks.
    manual_auto_skill: Optional[str] = None
    manual_auto_until: float = 0.0
    kb_time: float = 0.0
    kb_dir: int = 0
    # Server-authoritative ephemeral Guest character, not yet account persistent.
    exp: int = 0
    stat_points: int = 0
    skill_points: int = 0
    total_kills: int = 0
    stats: dict = field(default_factory=lambda:dict.fromkeys(prog.STAT_KEYS,0))
    skill_ranks: dict = field(default_factory=lambda:{'attack':1,'aoe':1,'break':1,'mastery':0})
    sp: float = 100.0
    max_sp: float = 100.0
    sta: float = 100.0
    max_sta: float = 100.0
    defense: int = 0
    inventory: list = field(default_factory=list)
    inventory_revision: int = 0
    writer_inventory_revision: int = -1
    auto_command_seq: int = 0
    auto_revision: int = 0
    last_crit: bool = False
    # Guest QA-only: server owns all loadout selections. No Supabase character mutation.
    test_level: Optional[int] = None
    qi_equipped: list = field(default_factory=lambda:[None,None,None])
    qi_ranks: dict = field(default_factory=dict)
    gear_level: Optional[int] = None
    gear_def_row: int = 0
    gear_atk_row: int = 5
    gear_enhancement: int = 5
    qi_heal_kills: int = 0
    qi_shield: int = 0
    qi_shield_until: float = 0
    qi_shield_cd: float = 0
    auto_state: farm_auto.State = field(default_factory=farm_auto.State)
    manual_guard:bool=False
    manual_guard_at:float=0.0
    # v8.0DF: visual facing during an accepted cast, independent from walk velocity.
    # Never use this field for physics, dash, attack permission, or damage checks.
    cast_face: int = 0
    snapshot_outbox: asyncio.Queue = field(default_factory=lambda:asyncio.Queue(maxsize=1))
    snapshot_task: Optional[asyncio.Task] = None
    snapshot_slot: int = 0  # 0..9, optional EL 2.5ms offset after world sample
    snapshot_last_sent_at: float = 0.0  # EL diagnostic only: server-side active-client cadence
    background_phase: int = 0 # v8.0DS: stable 0..9, schedules hidden views across ten 100ms broadcasts
    applied_input_seq: int = -1  # actual command consumed by the authoritative 30Hz simulation
    protocol_delta: bool = False # legacy BX clients still require unfiltered full snapshots
    protocol_binary: bool = False # v8.0DU opt-in; independent from delta cadence
    view_mode: str = 'active' # v8.0DP explicit visual subscription, never changes AI/physics
    stable_stats_key: object = None
    stable_derived_stats: object = None
    client_perf: dict = field(default_factory=dict)
    client_perf_at: float = 0.0
    writer_probe_counter: int = 0 # v8.0CR: sample 1 in 32 delta packets
    # v8.0DX: Client-proposed movement A/B. Old path is untouched by default.
    movement_mode: str = 'server'
    move_epoch: int = 0
    move_seq: int = -1
    move_shadow: object = None
    move_last_at: float = 0.0
    move_budget_x: float = 24.0
    move_rejects: int = 0
    move_last_correction: float = 0.0
    # EA: after server-forced knockback/stun, the accepted position can be
    # airborne while no client proposals arrive. One synchronisation can
    # re-anchor the validator; normal movement remains client-proposed.
    move_recovery_armed: bool = False
    # EC: Optional server-authoritative 30Hz self stream, owner only.
    fast_self_mode: bool = False
    fast_self_epoch: int = 0
    fast_self_last: object = None
    fast_self_outbox: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1))
    fast_self_task: Optional[asyncio.Task] = None
    ws_send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    event_cursor: int = 0  # EK: only advance after a successful packet send


@dataclass
class Monster(Actor):
    name: str = ''
    home: float = 0
    spawn_y: float = 550
    hum: bool = False
    ai_cool: float = 0
    decision: float = 0
    attack_time: float = 0
    walk_direction: int = 1
    level: int = 5
    zone_mode: str = "common"
    species: str = 'wolf'
    slot: str = ''
    pouncer: bool = False
    aggro_until: float = 0.0
    bite_started_at: float = -1e9
    bite_ready_at: float = 0.0
    bite_hit_done: bool = False
    bite_dir: int = -1
    patrol_phase: str = 'choose'
    patrol_dir: int = 1
    patrol_goal_x: float = 0
    patrol_until: float = 0.0
    last_combat: bool = False
    spawn_at: float = 0.0
    mark_stacks: dict = field(default_factory=dict)
    defense: int = 0
    # Newbie bamboo mobs are peaceful until struck by an actual player attack.
    retaliate_target: str = ''
    retaliate_until: float = 0.0


@dataclass
class Shot:
    id: int
    owner: str
    kind: str
    x: float
    y: float
    vx: float
    damage: int
    life: float
    pierce: int
    hit: set = field(default_factory=set)
    critical: bool = False
    # First-tick swept collision starts at the caster center, not the +52 visual muzzle.
    # Used only for first update; never supplied/trusted from the browser.
    origin_x: Optional[float] = None


# EE: fixed, administrator-owned channels. A guest can never create a world.
PUBLIC_CHANNEL_IDS = (1, 2, 3)
CHANNEL_IDS = tuple(range(1,16))  # 4..15 exist ONLY for privileged stress sessions
MAP_HARD_CAPS = {'forest': 10, 'movement_lab': 10, 'city': 70, 'bamboo_1': 10, 'bamboo_2': 10, 'bamboo_3': 10, 'bamboo_4': 10, 'outskirts_1': 10, 'suburb_gate_1': 10, 'city_proto_1': 70, 'city_inner_1': 70, 'peach_exit_1': 10, 'forest_fork_11':10}  # 10 player cap in Map11.
MAP_HARD_CAPS.update({room:10 for room in GRANITE_FOREST_MAPS})
MAP_HARD_CAPS.update({room:10 for room in MOUNTAIN_MAPS})
MAP_HARD_CAPS.update({room:10 for room in GRANITE_WALL_MAPS})
MAP_HARD_CAPS.update({room:10 for room in EXPANSION_MAPS})
CHANNEL_SWITCH_COOLDOWN = 10.0
CHANNEL_TOTAL_GUEST_CAP = min(MAX_GUESTS, int(os.environ.get('CHANNEL_TOTAL_GUEST_CAP', '30')))
MAX_PENDING_JOINS = 16
_pending_joins = 0

@dataclass
class WorldState:
    channel: int
    room: str
    players: dict = field(default_factory=dict)
    monsters: dict = field(default_factory=dict)
    shots: list = field(default_factory=list)
    peaches: list = field(default_factory=list)  # server-owned squirrel peach shots, map/channel isolated
    loot_drops: list = field(default_factory=list)
    events: list = field(default_factory=list)
    # EK: bounded world-level event journal persists across overwritten world samples.
    event_journal: deque = field(default_factory=lambda: deque(maxlen=2048))
    event_seq: int = 0
    snapshot_previous: dict = field(default_factory=lambda: {kind: {} for kind in ('players','mobs','loot','shots')})
    initialized: bool = False
    # EF: tiny sleeping capsule. Runtime monsters/shots/events/snapshot caches
    # are dropped when the last player leaves; remaining respawn/loot TTLs
    # continue using SERVER monotonic time to prevent CH-hop respawn exploits.
    sleeping_mobs: dict = field(default_factory=dict)
    sleeping_loot: list = field(default_factory=list)
    sleeps: int = 0
    wakes: int = 0

worlds = {(ch, room): WorldState(ch, room) for ch in CHANNEL_IDS for room in ('forest','movement_lab','bamboo_1','bamboo_2','bamboo_3','bamboo_4','outskirts_1','suburb_gate_1','city_proto_1','city_inner_1','peach_exit_1','forest_fork_11',*GRANITE_FOREST_MAPS,*MOUNTAIN_MAPS,*GRANITE_WALL_MAPS,*EXPANSION_MAPS)}
_world_context = ContextVar('jianghu_active_world', default=worlds[(1, 'forest')])
connected_players = {}  # global admission/telemetry ONLY, never combat or rewards

def current_world():
    return _world_context.get()

class WorldDict(MutableMapping):
    def __init__(self, attr): self.attr = attr
    def target(self): return getattr(current_world(),self.attr)
    def __getitem__(self,key): return self.target()[key]
    def __setitem__(self,key,value): self.target()[key]=value
    def __delitem__(self,key): del self.target()[key]
    def __iter__(self): return iter(self.target())
    def __len__(self): return len(self.target())
    def __repr__(self): return repr(self.target())

class WorldList(MutableSequence):
    def __init__(self, attr): self.attr=attr
    def target(self): return getattr(current_world(),self.attr)
    def __getitem__(self,key):return self.target()[key]
    def __setitem__(self,key,value):self.target()[key]=value
    def __delitem__(self,key):del self.target()[key]
    def __len__(self):return len(self.target())
    def insert(self,index,value):self.target().insert(index,value)
    def __iter__(self):return iter(self.target())
    def __repr__(self):return repr(self.target())

players = WorldDict('players')
monsters = WorldDict('monsters')
shots = WorldList('shots')
loot_drops = WorldList('loot_drops')
LOOT_TEMPLATES=json.loads(Path(__file__).with_name('loot_templates_v80bs.json').read_text(encoding='utf-8'))
LOOT_PICKUP_X=130
LOOT_PICKUP_Y=75
LOOT_OWNER_SEC=60
LOOT_LIFETIME_SEC=180
LOOT_INTRO_SEC=0.98
LOOT_BAG_CAP=48
events = WorldList('events')
shot_seq = 0
server_step = 0
snapshot_join_sequence = 0
# One-second bounded performance counters, cheap enough for the 30Hz game loop.
perf_ticks = deque(maxlen=180)
perf_loop_lags = deque(maxlen=180)
perf_encodes = deque(maxlen=360)
perf_data = {'tickP95Ms':0.0,'tickMaxMs':0.0,'rxInputsPerSec':0,'txKiBPerSec':0.0,'playerCount':0,'monsterCount':0,'eventLoopLagP95Ms':0,'eventLoopLagMaxMs':0,'snapshotEncodeP95Ms':0,'snapshotEncodeMaxMs':0}
perf_last_report = time.monotonic()
perf_in_count = 0
perf_out_bytes = 0
# v8.0CL: bounded anonymous diagnostic aggregates printed to Render app logs.
# No guest names, addresses, IPs, inventory or player positions are logged.
DIAG_WINDOW_SEC = 15.0
_diag_last = time.monotonic()
_diag_process_cpu = time.process_time()
_diag_sent = 0
_diag_overwritten = 0
_diag_send_durations = deque(maxlen=1500)
_diag_boot = secrets.token_hex(4)
_diag_cgroup_prev = None
# CV: bounded low-overhead tail-latency diagnostics; all durations are ms.
# Never record identities, IPs, positions or input payloads.
_cv_loop_spikes = deque(maxlen=128)
_cv_writer_wait = deque(maxlen=2000)
_cv_snapshot_age = deque(maxlen=2000)
_cv_active_snapshot_gap = deque(maxlen=2000)  # EL: successful active writer sends only
_cv_send_spikes = deque(maxlen=128)
_cv_outbox_skipped = 0
_bg_snapshot_queued = 0 # number of Background views actually enqueued in the window
_bg_snapshot_peak_batch = 0 # max Background views enqueued in a single 100ms broadcast
_fast_self_sent = 0
_fast_self_skipped = 0
_fast_self_bytes = 0
_em_auto_ack_sent = 0
_em_auto_canceled = 0
_em_fast_self_auto_violations = 0
_em_fast_self_stress_violations = 0
_em_inv_fast_reuse = 0
_em_inv_full_compare = 0
_em_inv_copy = 0
_em_writer_samples = {'packetBytes':0,'samples':0,'privateBytes':0,'privateChangedKeys':0,
                      'entities':0,'inventorySize':0,'events':0}
SPATIAL_CELL = 240


def em_process_memory():
    # /proc self is Linux-specific; never blocks game and is queried only per 15s.
    try:
        for row in Path('/proc/self/status').read_text().splitlines():
            if row.startswith('VmRSS:'):
                return int(row.split()[1])  # KiB
    except (OSError, IndexError, ValueError):
        pass
    return None

def read_cgroup_cpu():
    """Best-effort cgroup-v2 CPU limit/throttling counters, once per 15s.
    Missing/unsupported Linux cgroups leave nullable diagnostics; no game logic.
    """
    root = Path('/sys/fs/cgroup')
    quota = None
    throttling = None
    try:
        parts = (root / 'cpu.max').read_text(encoding='utf-8').split()
        if len(parts) == 2 and parts[0] != 'max':
            quota = round(int(parts[0]) / int(parts[1]), 3)
    except (OSError, ValueError, ZeroDivisionError):
        pass
    try:
        stats = dict(line.split()[:2] for line in
                     (root / 'cpu.stat').read_text(encoding='utf-8').splitlines()
                     if len(line.split()) >= 2)
        throttling = (int(stats['nr_throttled']), int(stats['throttled_usec']))
    except (OSError, ValueError, KeyError):
        pass
    return quota, throttling

def index_players_by_x():
    # Share one indexed player roster across 20 beasts; combat remains authoritative.
    cells = defaultdict(list)
    for p in players.values():
        if p.dead<=0 and p.room==current_world().room:
            cells[int(p.x // SPATIAL_CELL)].append(p)
    return cells

def candidate_players_by_x(m, grid):
    if grid is None:
        return (p for p in players.values() if p.room==current_world().room)  # only same map/channel may be targeted
    radius=BEAST_AGGRO+65
    first=int((m.x-radius)//SPATIAL_CELL)
    last=int((m.x+radius)//SPATIAL_CELL)
    return (p for cell in range(first,last+1) for p in grid.get(cell,()))

def performance_rollup(now):
    global perf_last_report,perf_in_count,perf_out_bytes
    elapsed=now-perf_last_report
    if elapsed<1:return
    ordered=sorted(perf_ticks)
    lags=sorted(perf_loop_lags)
    encodes=sorted(perf_encodes)
    def p95(a):return round(a[min(len(a)-1,int(len(a)*.95))]*1000,2) if a else 0
    def peak(a):return round(a[-1]*1000,2) if a else 0
    perf_data.update(tickP95Ms=round(ordered[min(len(ordered)-1,int(len(ordered)*.95))]*1000,2) if ordered else 0,
                     tickMaxMs=round(max(ordered)*1000,2) if ordered else 0,
                     rxInputsPerSec=round(perf_in_count/elapsed),
                     txKiBPerSec=round(perf_out_bytes/1024/elapsed,1),
                     playerCount=len(connected_players),monsterCount=sum(len(w.monsters) for w in worlds.values()),
                     eventLoopLagP95Ms=p95(lags),eventLoopLagMaxMs=peak(lags),
                     snapshotEncodeP95Ms=p95(encodes),snapshotEncodeMaxMs=peak(encodes))
    perf_in_count=0;perf_out_bytes=0;perf_last_report=now



# v8.0CQ passive server-only profiler: sample one complete 30Hz tick per second.
# Report stage wall-times, not CPU-time. Throttling can inflate these values.
_profile_samples={name:[] for name in ('player','monster','projectile_loot','world_snapshot')}
# v8.0CR: independent writer-stage timings. Bounded samples, private to Render
# diagnostics. Do not place wall-time diagnostics into packets/gameplay.
_writer_stage_samples={name:deque(maxlen=1800) for name in
                       ('aoi','delta','private','json','send')}

# EJ opt-in profiler. Each synchronous stage uses perf_counter_ns wall-clock
# (single-thread event loop: a useful proxy for time monopolising the core).
# async waits have explicit '.wait'/'await' names and MUST NOT count as CPU.
# Totals are all observed calls; bounded rolling samples inform P95/P99 only.
_PROFILE_MAX_SAMPLES=4096
_profile_stages={}
_profile_worlds={}

def _profile_add(name, elapsed_ns, world_key=None):
    if not ENABLE_PERFORMANCE_PROFILER:return
    rec=_profile_stages.get(name)
    if rec is None:
        rec=[0,0,0,deque(maxlen=_PROFILE_MAX_SAMPLES)]
        _profile_stages[name]=rec
    elapsed_ns=max(0,int(elapsed_ns))
    rec[0]+=elapsed_ns
    rec[1]+=1
    rec[2]=max(rec[2],elapsed_ns)
    rec[3].append(elapsed_ns)
    if world_key is not None:
        key=str(world_key[0])+':'+world_key[1]
        item=_profile_worlds.get(key)
        if item is None:
            item=[0,0]
            _profile_worlds[key]=item
        item[0]+=elapsed_ns;item[1]+=1

def _profile_report(window, cpu_pct):
    if not ENABLE_PERFORMANCE_PROFILER:return
    def summary(rec):
        total,count,maximum,samples=rec
        ordered=sorted(samples)
        def p(frac):
            return round(ordered[min(len(ordered)-1,int((len(ordered)-1)*frac))]/1e6,3) if ordered else None
        return {'n':count,'totalMs':round(total/1e6,2),
                'msPerSec':round(total/1e6/max(.001,window),2),
                'avgMs':round(total/max(1,count)/1e6,4),
                'p95Ms':p(.95),'p99Ms':p(.99),
                'maxMs':round(maximum/1e6,3)}
    wait_names={'writer.slot_wait_intentional','writer.send_lock_wait',
                'writer.send_await','self.send_lock_wait','self.send_await'}
    sync_stages={k:summary(v) for k,v in sorted(_profile_stages.items(),key=lambda kv:kv[1][0],reverse=True)
                 if k not in wait_names}
    wait_stages={k:summary(v) for k,v in sorted(_profile_stages.items(),key=lambda kv:kv[1][0],reverse=True)
                 if k in wait_names}
    top=[{'world':k,'totalMs':round(v[0]/1e6,2),'ticks':v[1],
          'players':len(worlds[tuple([int(k.split(':',1)[0]),k.split(':',1)[1]])].players),
          'monsters':len(worlds[tuple([int(k.split(':',1)[0]),k.split(':',1)[1]])].monsters)}
         for k,v in sorted(_profile_worlds.items(),key=lambda kv:kv[1][0],reverse=True)[:5]]
    data={'v':'v8.0EO','ts':int(time.time()),'boot':_diag_boot,
          'windowSec':round(window,2),'cpuCorePct':cpu_pct,
          'sampleMeaning':'all-call totals; bounded newest P95/P99 samples; nested sync stages overlap; concurrent async waits are NOT CPU',
          'syncStages':sync_stages,'waitStages':wait_stages,'worldTop':top}
    print('JIANGHU_PROFILE '+json.dumps(data,separators=(',',':')),flush=True)
    _profile_stages.clear();_profile_worlds.clear()


def report_performance_to_render(now):
    """Emit one compact, structured, anonymous JSON line every 15s.
    Read these with Render list_logs text='JIANGHU_DIAG' and compare with CPU metrics.
    No external IO here beyond a bounded print; no database dependency in game loop.
    """
    global _diag_last, _diag_process_cpu, _diag_sent, _diag_overwritten, _diag_cgroup_prev, _cv_outbox_skipped
    global _bg_snapshot_queued, _bg_snapshot_peak_batch, _fast_self_sent, _fast_self_skipped, _fast_self_bytes
    global _em_auto_ack_sent, _em_auto_canceled, _em_fast_self_auto_violations, _em_fast_self_stress_violations
    global _em_inv_fast_reuse, _em_inv_full_compare, _em_inv_copy
    if now-_diag_last<DIAG_WINDOW_SEC:return
    window=now-_diag_last
    cpu_delta=time.process_time()-_diag_process_cpu
    quota, cgroup=read_cgroup_cpu()
    throttled_periods=throttled_ms_per_sec=None
    if cgroup is not None and _diag_cgroup_prev is not None:
        throttled_periods=max(0,cgroup[0]-_diag_cgroup_prev[0])
        throttled_ms_per_sec=round(max(0,cgroup[1]-_diag_cgroup_prev[1])/1000/window,2)
    _diag_cgroup_prev=cgroup
    _diag_last=now;_diag_process_cpu=time.process_time()
    active=[p.client_perf for p in connected_players.values() if p.client_perf and now-p.client_perf_at<35]
    sends=sorted(_diag_send_durations)
    def percentile(a, ratio):
        return round(a[min(len(a)-1,int((len(a)-1)*ratio))],2) if a else None
    data={
        'v':'v8.0EO','boot':_diag_boot,'ts':int(time.time()),'windowSec':round(window,1),
        'guests':len(connected_players),'autoGuests':sum(bool(p.auto_state.enabled) for p in connected_players.values()),'backgroundAutoGuests':sum(p.view_mode=='background' and p.auto_state.enabled for p in connected_players.values()),'backgroundGuests':sum(p.view_mode=='background' for p in connected_players.values()),'activeGuests':sum(p.view_mode=='active' for p in connected_players.values()),
        'monsters':sum(len(w.monsters) for w in worlds.values()),'backgroundSnapshotQueued':_bg_snapshot_queued,'backgroundBatchPeak':_bg_snapshot_peak_batch,'cpuCorePct':round(100*cpu_delta/max(.001,window),1),
        'cpuQuotaCores':quota,'cgroupThrottledPeriods':throttled_periods,
        'cgroupThrottleMsPerSec':throttled_ms_per_sec,
        'tickP95Ms':perf_data['tickP95Ms'],'tickMaxMs':perf_data['tickMaxMs'],
        'loopP95Ms':perf_data['eventLoopLagP95Ms'],'loopMaxMs':perf_data['eventLoopLagMaxMs'],
        'encodeP95Ms':perf_data['snapshotEncodeP95Ms'],'encodeMaxMs':perf_data['snapshotEncodeMaxMs'],
        'totalGuestCap':CHANNEL_TOTAL_GUEST_CAP,'pendingJoins':_pending_joins,
        'stressEnabled':ENABLE_CHANNEL_STRESS,'perfProfilerEnabled':ENABLE_PERFORMANCE_PROFILER,
        'elSnapshotSchedulerEnabled':ENABLE_EL_SNAPSHOT_SCHED,
        'eoWriterWaitCapMs':0 if ENABLE_EL_SNAPSHOT_SCHED else EO_WRITER_WAIT_CAP_MS,
        'emInventoryRevisionEnabled':ENABLE_EM_INVENTORY_REV,
        'enEventScanEnabled':ENABLE_EN_EVENT_SCAN,
        'rssKiB':em_process_memory(),'gcCounts':list(gc.get_count()),
        'gcCollections':[x['collections'] for x in gc.get_stats()],
        'stressAutoEnabled':sum(p.stress_test and p.auto_state.enabled for p in connected_players.values()),
        'stressAutoOff':sum(p.stress_test and not p.auto_state.enabled for p in connected_players.values()),
        'fastSelfAutoViolations':_em_fast_self_auto_violations,
        'fastSelfStressViolations':_em_fast_self_stress_violations,
        'autoAckSent':_em_auto_ack_sent,'autoManualCancels':_em_auto_canceled,
        'stressGuests':sum(p.stress_test for p in connected_players.values()),
        'stressByChannel':{str(ch):sum(p.stress_test for p in worlds[(ch,'forest')].players.values()) for ch in CHANNEL_IDS},
        'channels':{str(ch):{'forest':len(worlds[(ch,'forest')].players),'lab':len(worlds[(ch,'movement_lab')].players)} for ch in CHANNEL_IDS},
        'awakeWorlds':sum(w.initialized for w in worlds.values()),
        'sleepingWorlds':sum(not w.initialized for w in worlds.values()),
        'runtimeMonsters':sum(len(w.monsters) for w in worlds.values()),
        'snapSent':_diag_sent,'snapOverwritten':_diag_overwritten,
        'fastSelfSent':_fast_self_sent,'fastSelfSkipped':_fast_self_skipped,'fastSelfTxKiB':round(_fast_self_bytes/1024,1),
        'wsSendP95Ms':percentile(sends,0.95),'wsSendMaxMs':percentile(sends,1.0),
        'txKiBs':perf_data['txKiBPerSec'],'rxInputsSec':perf_data['rxInputsPerSec'],
        'browserCount':len(active),'browserFpsMin':min((a['fps'] for a in active),default=None),
        'browserPingMsP95':percentile(sorted(a['pingMs'] for a in active if a['pingMs'] is not None),0.95),
        'browserSnapGapP95Ms':percentile(sorted(a['gapP95Ms'] for a in active),0.95),
        'browserSnapGapMaxMs':max((a['gapMaxMs'] for a in active),default=None),
        'browserFrameMsP95':percentile(sorted(a['frameMs'] for a in active),0.95),
    }
    data['profileTickStageAvgMs']={k:round(sum(values)/len(values),3) if values else None
                                    for k,values in _profile_samples.items()}
    data['profileWriterStageP95Ms']={k:percentile(sorted(values),0.95) for k,values in _writer_stage_samples.items()}
    data['profileWriterStageAvgMs']={k:round(sum(values)/len(values),3) if values else None
                                      for k,values in _writer_stage_samples.items()}
    data['profileWriterStageSamples']={k:len(values) for k,values in _writer_stage_samples.items()}
    # Target the 180-200ms intermittent spikes: distributions and bounded worst
    # samples can distinguish scheduling, stale snapshots and network sends.
    waits=sorted(_cv_writer_wait)
    ages=sorted(_cv_snapshot_age)
    active_send_gaps=sorted(_cv_active_snapshot_gap)
    data['tailLatency']={
        'loopSpikeCount':len(_cv_loop_spikes),
        'loopSpikeMaxMs':round(max(_cv_loop_spikes),2) if _cv_loop_spikes else None,
        'writerSlotWaitP95Ms':percentile(waits,.95),
        'writerSlotWaitMaxMs':percentile(waits,1),
        'snapshotAgeP95Ms':percentile(ages,.95),
        'snapshotAgeMaxMs':percentile(ages,1),
        'activeSnapshotSendGapP95Ms':percentile(active_send_gaps,.95),
        'activeSnapshotSendGapP99Ms':percentile(active_send_gaps,.99),
        'activeSnapshotSendGapMaxMs':percentile(active_send_gaps,1),
        'sendSpikeCount':len(_cv_send_spikes),
        'sendSpikeMaxMs':round(max(_cv_send_spikes),2) if _cv_send_spikes else None,
        'outboxSkipped':_cv_outbox_skipped,
    }
    data['emWriter']={
        'inventoryRevisionReuses':_em_inv_fast_reuse,
        'inventoryFullComparisons':_em_inv_full_compare,
        'inventoryCopies':_em_inv_copy,
        'sampleCount':_em_writer_samples['samples'],
        **{key+'Avg':round(_em_writer_samples[key]/max(1,_em_writer_samples['samples']),2)
           for key in ('packetBytes','privateBytes','privateChangedKeys','entities','inventorySize','events')},
    }
    _profile_report(window,data['cpuCorePct'])
    _cv_outbox_skipped=0
    _bg_snapshot_queued=0;_bg_snapshot_peak_batch=0
    _cv_loop_spikes.clear();_cv_writer_wait.clear()
    _cv_snapshot_age.clear();_cv_send_spikes.clear();_cv_active_snapshot_gap.clear()
    for values in _writer_stage_samples.values():values.clear()
    for values in _profile_samples.values():values.clear()
    # No telemetry is written to Supabase until a separate authenticated storage path exists.
    print('JIANGHU_DIAG '+json.dumps(data,separators=(',',':')),flush=True)
    _diag_sent=0;_diag_overwritten=0;_diag_send_durations.clear()
    _fast_self_sent=0;_fast_self_skipped=0;_fast_self_bytes=0
    _em_auto_ack_sent=0;_em_auto_canceled=0
    _em_fast_self_auto_violations=0;_em_fast_self_stress_violations=0
    _em_inv_fast_reuse=0;_em_inv_full_compare=0;_em_inv_copy=0
    for key in _em_writer_samples:_em_writer_samples[key]=0


# NOTE: The OFFLINE JavaScript spawner remains the source of truth for this test-map
# manifest. Regenerate the JSON when changing the map; never accept client spawn data.
BEAST_AGGRO=280
BEAST_CHASE_SPEED=112
BEAST_PATROL_SPEED=BEAST_CHASE_SPEED*0.65
# v8.0DG pending: no map-wide respawn waves, shared queues, or random staggering.
# Every monster has its own countdown in Monster.dead, starting on the killing tick.
# Death at T -> respawn at about T+RESPAWN_SEC (nearest simulation tick).
# Two monsters dying in the same tick may respawn together, by design.
RESPAWN_SEC=5.0

def next_respawn_delay():
    return RESPAWN_SEC

def supported(m, x=None):
    x=m.x if x is None else x
    return any(abs(m.y-y)<12 and lo+20<x<hi-20 for lo,hi,y in active_ground())

def own_lane(m):
    return next(((lo,hi,y) for lo,hi,y in active_ground() if abs(m.y-y)<12 and lo+12<m.x<hi-12),None)

# v8.0CQ: query one lane per mob-target selection, not once per candidate player.
_LANE_NOT_GIVEN=object()
def reachable_player(m,p,lane=_LANE_NOT_GIVEN):
    if lane is _LANE_NOT_GIVEN:lane=own_lane(m)
    if not lane or p.dead>0 or p.climb or not lane[0]+12<p.x<lane[1]-12:return False
    if p.ground:return abs(p.y-m.y)<12
    return m.y-128<=p.y<=m.y+22

def spawn_mobs():
    monsters.clear()
    room=current_world().room
    if room=='forest':
        slots=MAP_DATA['slots']  # original mountain roster, untouched
    elif room in BAMBOO_MONSTER_SLOTS:
        slots=BAMBOO_MONSTER_SLOTS[room]
    else:
        return
    for index,slot in enumerate(slots):
        species=slot['kind']
        x,y=float(slot['x']),float(slot['y'])
        mid=slot['id']
        if room=='forest':
            assert species in ('boar','wolf')
            level=MONSTER_PRESET_LEVEL or min(5,1+index%5)
            name='หมูป่า' if species=='boar' else 'หมาป่า'
        else:
            assert species in BAMBOO_MONSTER_NAMES
            level=MONSTER_PRESET_LEVEL or min(5,1+(PUBLIC_MAP_IDS.index(room)-1)+index%3)
            name=BAMBOO_MONSTER_NAMES[species]
        max_hp,defense=monster_balance.preset(level,False)
        monsters[mid]=Monster(id=mid,name=name,
            x=x,y=y,hp=max_hp,max_hp=max_hp,defense=defense,home=x,spawn_y=y,hum=False,
            level=level,zone_mode='common',species=species,
            slot=mid,pouncer=slot.get('pouncer',False),bite_ready_at=time.monotonic()+.65,
            patrol_dir=-1 if index%2 else 1,patrol_phase='idle',
            patrol_until=time.monotonic()+2+random.random()*2,spawn_at=time.monotonic())


def hibernate_world(world):
    """Release a playerless instance WITHOUT resetting respawn timers or unclaimed loot.

    All mutations are synchronous in the single asyncio event loop. Never
    serialize or clone Guest actors, award loot, or persist a character here.
    CH/map registry stays present solely for capacity checks/instant admission.
    """
    if world.players:
        return False
    if not world.initialized:
        # Already asleep; do not overwrite the compact capsule on duplicate leave.
        return False
    now = time.monotonic()
    # Save ONLY exceptional monster slots: dead countdowns and damaged survivors.
    # Absolute deadlines ensure sleeping time is counted toward respawn.
    world.sleeping_mobs = {
        mid: {'hp': int(m.hp), 'ready_at': now + m.dead if m.dead > 0 else 0.0}
        for mid, m in world.monsters.items()
        if m.dead > 0 or m.hp < m.max_hp
    }
    # Loot is NOT picked up or re-created by sleeping. Keep original unique IDs,
    # owner/private windows, pickup delays and absolute expiry deadlines.
    world.sleeping_loot = [d.copy() for d in world.loot_drops if d['expiresAt'] > now]
    world.monsters.clear()
    world.shots.clear()
    world.peaches.clear()
    world.loot_drops.clear()
    world.events.clear()
    world.event_journal.clear()
    for cache in world.snapshot_previous.values():
        cache.clear()
    world.initialized = False
    world.sleeps += 1
    return True


def wake_world(world):
    """Wake only on an admitted first player; never on channel-list polling.

    Recreate normal monster instances from the server-owned map manifest, then
    restore damaged HP/death deadlines from the tiny capsule. Stale unclaimed
    loot expires naturally; no item/inventory/EXP mutations happen here.
    """
    if world.initialized:
        return False
    token = _world_context.set(world)
    try:
        now = time.monotonic()
        if world.room == 'forest' or world.room in BAMBOO_MONSTER_SLOTS:
            spawn_mobs()
            for mid, state in world.sleeping_mobs.items():
                m = world.monsters.get(mid)
                if m is None:
                    continue  # map manifest may have changed since the capsule
                ready_at = state['ready_at']
                if ready_at > now:
                    m.dead = ready_at - now
                    m.hp = 0
                elif ready_at == 0.0 and state['hp'] > 0:
                    m.hp = min(m.max_hp, state['hp'])
                # If dead timer elapsed during sleep, use fresh full HP spawn.
        world.loot_drops[:] = [d for d in world.sleeping_loot if d['expiresAt'] > now]
        world.sleeping_mobs.clear()
        world.sleeping_loot.clear()
        world.events.clear()
        world.event_journal.clear()
        for cache in world.snapshot_previous.values():
            cache.clear()
        world.initialized = True
        world.wakes += 1
        return True
    finally:
        _world_context.reset(token)


# EK: events are not dropped when a newer snapshot replaces a queued frame.
# IDs are server-owned, bounded per world and never interpreted for game authority.
def record_world_event(world, payload):
    world.event_seq += 1
    payload['eid'] = f'{world.channel}:{world.room}:{world.event_seq}'
    # Size budget is computed once per event and reused by every recipient.
    event_wire_size = len(_COMPACT_WIRE_JSON_ENCODER.encode(payload))
    world.event_journal.append((world.event_seq, time.monotonic(), payload, event_wire_size))
    world.events.append(payload)


def event(event_type, x, y, **kwargs):
    record_world_event(current_world(), {'t': event_type, 'x': round(x, 1), 'y': round(y, 1), **kwargs})


def set_action(actor, a, dur):
    actor.action = a
    actor.action_at = 0
    actor.action_duration = dur


def physics(actor, dt):
    if current_world().room in EXPANSION_MAPS:
        expansion_physics(actor,dt,EXPANSION_MAPS[current_world().room]);return
    # v8.0CI: Resolve horizontal world-wall collision BEFORE ground support.
    # Dash can move > one collider margin in a single 30Hz server tick. If
    # can_stand sees the out-of-bounds x before clamping, a grounded character
    # may miss the one-way floor and fall underneath it permanently.
    actor.x = clamp(actor.x, 27, city_world_width(current_world().room) - 27)
    old = actor.y
    if actor.climb is None:
        actor.vy += 1400 * dt
        actor.y += actor.vy * dt
        actor.ground = False
        if actor.vy >= 0:
            top = can_stand(actor.x, actor.y, old)
            if top is not None:
                actor.y = top
                actor.vy = 0
                actor.ground = True
    if actor.y > 800:
        actor.y, actor.vy, actor.ground = 550, 0, True
        if isinstance(actor, Guest):
            hurt(actor, 100, actor.x, actor.y - 70, 'fall')


def hurt(victim, damage, x, y, kind,critical=False,owner=None):
    if victim.dead > 0 or victim.inv > 0: return
    if isinstance(victim, Guest) and victim.guard and victim.broken <= 0:
        event('block', victim.x, victim.y - 82, victim=victim.id)
        return
    if isinstance(victim,Guest) and victim.qi_shield>0:
        absorbed=min(victim.qi_shield,damage)
        victim.qi_shield-=absorbed;damage-=absorbed
        if absorbed:event('block',victim.x,victim.y-100,victim=victim.id)
    victim.hp = max(0, victim.hp - damage)
    if isinstance(victim,Guest):try_qi_shield(victim)
    victim.stun = 0.25
    victim.inv = .42 if isinstance(victim, Guest) else 0
    if isinstance(victim,Monster):
        # Offline v8.0AY: ranged impacts INTERRUPT movement, not physical shove.
        victim.vx=0
        victim.bite_started_at=-1e9
        victim.bite_hit_done=False
        victim.last_combat=False
    elif isinstance(victim,Guest) and kind=='monster':
        # Offline v8.0AX: never remove classic monster hit recoil.
        victim.inv=1.12
        victim.stun=.16
        victim.kb_time=.28
        # Source position delivered by call-site via x (the monster's world x).
        victim.kb_dir=(1 if victim.x>=x else -1)
        victim.vx=victim.kb_dir*300
        victim.vy=-240
        victim.ground=False
        victim.guard=False
        if victim.climb is not None:
            victim.climb=None
            victim.climb_cd=max(.5,victim.climb_cd)
    if isinstance(victim,Guest):victim.last_damage_at=time.monotonic()
    event('hit', victim.x, victim.y - 78, victim=victim.id, damage=damage, kind=kind,critical=critical,
          **({'owner':owner} if owner is not None else {}))
    if victim.hp <= 0 and victim.dead <= 0:
        victim.dead = next_respawn_delay() if isinstance(victim, Monster) else 2.5
        victim.guard = False
        event('defeat', victim.x, victim.y - 80, victim=victim.id)


def try_qi_shield(p):
    if not loadouts.active_qi(p,0) or p.hp<=0 or p.hp>=p.max_hp*.35 or p.qi_shield>0 or time.monotonic()<p.qi_shield_cd:return
    shield=loadouts.qi_mechanics(p,'flute_echo')['shield']
    if not shield:return
    value=prog.jsround(p.max_hp*shield['hpPct']/100+p.sp*shield['spPct']/100)
    if value<=0:return
    now=time.monotonic();p.qi_shield=value;p.qi_shield_until=now+30;p.qi_shield_cd=now+120
    event('qi_shield',p.x,p.y-110,victim=p.id,amount=value)

def perform_action(p: Guest, action: str):
    if p.dead > 0 or p.down > 0 or p.stun > 0 or p.broken > 0: return
    if p.room=='movement_lab' and action not in ('jump','dash','lock'): return  # training-only movement lab has no combat
    if action == 'jump':
        if p.ground and p.climb is None:
            p.vy, p.ground, p.climb = -540, False, None
            set_action(p, 'jump', .25)
        elif p.climb is not None:
            p.climb = None
            p.climb_cd = .35
            p.vy, p.vx = -475, p.face * 160
            set_action(p, 'jump', .25)
        return
    if action == 'dash':
        if p.cool <= 0 and p.climb is None and p.sta >= 30:
            p.sta -= 30
            p.vx, p.inv, p.cool = p.face * 650, .17, .5
            set_action(p, 'dash', .26)
        return
    if action == 'lock': return  # Lock targets never dictate damage on server.
    if action not in ATTACKS or p.cool > 0 or p.climb is not None or p.guard: return
    if p.sp < prog.SKILL_SP[action]: return
    # Second independent server clock check; rejects spoofed burst commands even
    # when the animation/cool timer is accidentally changed. No queued attacks.
    server_now=time.monotonic()
    if server_now-p.last_attack_at+0.000001 < ATTACKS[action][0]: return
    p.last_attack_at=server_now
    # v8.0DF: Match Offline's nearest-monster auto-facing on manual casts.
    # AUTO AI already owns its target/facing. Direction is computed from server
    # monster coordinates, never from an untrusted client-supplied aim/position.
    shot_dir=p.face
    if not p.auto_state.enabled and p.room in PUBLIC_MAP_IDS:
        # DJ: Re-select ONLY after death or truly invalid position. Never
        # retarget mid-combat just because the other mob takes one step closer.
        def legal_aim(m):
            return (m is not None and m.dead<=0 and m.hp>0 and
                    abs(m.x-p.x)<900 and abs(m.y-p.y)<120)
        candidate=monsters.get(p.manual_target_id)
        if not legal_aim(candidate):
            candidate=min((m for m in monsters.values() if legal_aim(m)),
                          key=lambda m:abs(m.x-p.x),default=None)
            p.manual_target_id=candidate.id if candidate else None
        if candidate is not None and abs(candidate.x-p.x)>12:
            shot_dir=1 if candidate.x>p.x else -1
    p.cast_face=shot_dir
    global shot_seq
    cooldown, duration, speed, _, lifespan, pierce = ATTACKS[action]
    damage,critical=prog.roll_attack(p,action,hp_reference)
    p.sp-=prog.SKILL_SP[action]
    p.cool = cooldown
    set_action(p, action, duration)
    shot_seq += 1
    y = p.y - 84 - (3 if action == 'aoe' else 4 if action == 'break' else 0)
    shots.append(Shot(shot_seq, p.id, action, p.x + shot_dir * 52, y, shot_dir * speed, damage, lifespan, pierce, critical=critical, origin_x=p.x))
    # Every confirmed cast has a short-lived visual trace even when the actual
    # server-owned projectile hits a mob before the next 10Hz snapshot.
    event('cast',p.x,p.y-34,kind=action,owner=p.id,shotId=str(shot_seq),
          shotX=round(p.x+shot_dir*52,1),shotY=round(y,1),shotDir=shot_dir,
          shotSpeed=speed)


# Never grant extra casts or reduce cooldown. A manual spell pressed during AUTO
# waits for the next legal cast window instead of being lost to AUTO spam.
AUTO_MANUAL_PRIORITY_SEC = 1.25

def pending_auto_manual(p: Guest, server_now: float) -> bool:
    action = p.manual_auto_skill
    if action is None: return False
    if not p.auto_state.enabled or server_now > p.manual_auto_until:
        p.manual_auto_skill = None
        return False
    if p.sp < prog.SKILL_SP[action]:
        p.manual_auto_skill = None
        return False
    # Reserved input has priority even while stun, guard, ladder or cooldown
    # prevents a cast. Never bypass any of the ordinary action checks.
    if p.cool > 0 or p.climb is not None or p.guard or p.dead > 0 or p.down > 0 or p.stun > 0 or p.broken > 0:
        return True
    previous = p.last_attack_at
    perform_action(p, action)
    if p.last_attack_at != previous:
        p.manual_auto_skill = None
        return False
    return True

def update_guest(p: Guest, dt, tick_now):
    if EXPANSION_MAPS.get(p.room,{}).get('downOnly'):p.buttons &= ~4
    p.applied_input_seq=p.last_seq  # ack only after simulation consumes this input
    # v8.0DV: preserve exact timer order, clamp and 30Hz duration while
    # avoiding six dynamic getattr/setattr operations per Guest per tick.
    p.cool=max(0,p.cool-dt)
    p.inv=max(0,p.inv-dt)
    p.stun=max(0,p.stun-dt)
    p.down=max(0,p.down-dt)
    p.broken=max(0,p.broken-dt)
    p.climb_cd=max(0,p.climb_cd-dt)
    p.action_at += dt
    derived=derived_for_snapshot(p)
    if p.qi_shield and (tick_now>=p.qi_shield_until or not loadouts.active_qi(p,0)):p.qi_shield=0
    p.sp=min(p.max_sp,p.sp+derived['spRegenPerSec']*dt)
    p.sta=min(p.max_sta,p.sta+derived['staRegenPerSec']*dt)
    if not p.dead and p.hp>0:p.hp=min(p.max_hp,p.hp+derived['hpRegenPerSec']*dt)
    p.kb_time=max(0,p.kb_time-dt)
    if tick_now - p.last_input > .55:
        p.buttons = 0
    if p.hp <= 0 and not p.dead:
        p.dead = 2.5
    if p.dead > 0:
        p.dead -= dt
        p.buttons = 0
        p.guard = False
        p.vx *= .83
        p.x += p.vx * dt
        physics(p, dt)
        if p.dead <= 0:
            p.dead = 0.0
            p.x, p.y, p.vx, p.vy, p.hp, p.stun, p.down, p.inv, p.cool, p.climb = (175 + len(players) * 23, 550, 0, 0, p.max_hp, 0, 0, 1, .3, None)
            if p.room in EXPANSION_MAPS:p.x,p.y=EXPANSION_MAPS[p.room]['spawn']
            p.sp=p.max_sp;p.sta=p.max_sta
            p.ground = True
            event('respawn', p.x, p.y, victim=p.id)
        return
    if p.kb_time>0:
        p.vx=p.kb_dir*300
        p.x+=p.vx*dt
        physics(p,dt)
        return
    if p.down > 0:
        p.vx *= .75
        p.x += p.vx * dt
        p.guard = False
        physics(p, dt)
        return
    p.guard = bool(p.buttons & 16) and p.broken <= 0 and p.stun <= 0 and p.climb is None
    near = next((c for c in active_climbs() if abs(c[0] - p.x) < 36 and c[1] - 8 <= p.y <= c[2] + 12), None)
    axis = int(bool(p.buttons & 8)) - int(bool(p.buttons & 4))
    if city_stair_step(p,dt,axis): return
    # v8.0DE: Climb completion deliberately lands at rope_x+47, but normal
    # climb acquisition only works within 36px. A human holding DOWN from the
    # landing was stranded, while AUTO first walks back to the rope. Align at
    # normal walking speed (never teleport) only when grounded on a continuous
    # real platform crossing the climb; forbid bottom-floor/down reacquisition.
    if (p.climb is None and axis > 0 and p.ground and not p.guard and p.climb_cd <= 0
            and p.stun <= 0 and (p.action != 'dash' or p.action_at >= .26)):
        landing = next((c for c in active_climbs()
                        if 12 < abs(c[0] - p.x) <= 56
                        and c[1] - 3 <= p.y < c[2] - 8
                        and any(abs(y - p.y) < 6 and lo + 8 < min(p.x, c[0])
                                and max(p.x, c[0]) < hi - 8 for lo, hi, y in active_ground())), None)
        if landing is not None:
            step = 205 * derived['moveSpeedMultiplier'] * dt
            p.x += clamp(landing[0] - p.x, -step, step)
            p.vx = 0
            if abs(p.x - landing[0]) > 12:
                return  # Held DOWN continues alignment until safe climb entry.
            near = landing
    # v8.0CE: Holding UP on the upper platform must never re-capture
    # the ladder and start a fresh upward climb through open air.
    # Players can still intentionally press DOWN to descend from the landing.
    if near and axis < 0 and p.ground and p.y <= near[1] + 6:
        near = None
    if near and axis and not p.guard and p.climb_cd <= 0:
        p.climb = near
        p.x, p.vx, p.vy, p.ground = near[0], 0, 0, False
    # DJ: The long ropes cross a real second-floor platform. A human pressing
    # LEFT/RIGHT at that height can step off safely. Previously the server
    # ignored horizontal input for the entire climb; only AUTO could jump off.
    # Do not permit mid-air or wall-clipping exits: require a crossing foothold.
    sideways = int(bool(p.buttons & 2)) - int(bool(p.buttons & 1))
    if p.climb is not None and sideways and axis == 0 and p.stun <= 0 and not p.guard:
        cx, top, bottom = p.climb
        landing = min((fy for lo, hi, fy in active_ground()
                       if lo + 28 < cx < hi - 28 and top + 20 < fy < bottom - 20
                       and abs(p.y - fy) <= 23),
                      key=lambda fy: abs(p.y - fy), default=None)
        if landing is not None:
            p.climb = None
            p.climb_cd = .32
            p.y, p.x, p.vx, p.vy, p.ground = landing, cx + sideways * 18, 0, 0, True
            p.face = sideways
    if p.climb is not None:
        cx, top, bottom = p.climb
        old_y = p.y
        p.y = clamp(p.y + axis * 175 * dt, top, bottom)
        # Hard physical ceiling/floor; never allow any stale upward state to
        # survive a climb that reaches the end of the ladder.
        p.y = clamp(p.y, top, bottom)
        p.climb_dist += abs(p.y - old_y)
        p.x, p.vx, p.vy = cx, 0, 0
        if axis < 0 and p.y <= top + 1:
            p.climb, p.climb_cd, p.y, p.x, p.ground = None, .28, top, expansion_dismount(EXPANSION_MAPS.get(p.room),cx,top,47), True
        elif axis > 0 and p.y >= bottom - 1:
            p.climb, p.climb_cd, p.y, p.x, p.ground = None, .28, bottom, expansion_dismount(EXPANSION_MAPS.get(p.room),cx,bottom,45), True
        return
    move = int(bool(p.buttons & 2)) - int(bool(p.buttons & 1))
    if move and p.stun <= 0 and not p.guard:
        p.face = 1 if move > 0 else -1
        if p.action != 'dash' or p.action_at > .26:
            p.vx = 205 * move * derived['moveSpeedMultiplier']
    elif p.action != 'dash' or p.action_at > .26:
        p.vx *= max(0, 1 - 12 * dt)
    if p.guard: p.vx = 0
    p.x += p.vx * dt
    if p.ground and move: p.walk_dist += abs(p.vx * dt)
    physics(p, dt)


# v8.0DX experiment. A/B is OFF unless ENABLE_CLIENT_MOVEMENT_AB=1.
# Shadow simulation uses the original DV update_guest function as a *validator*.
# It does not publish server-computed coordinates in Client mode. Only validated
# proposals replace p.x/p.y, which drive PvE/loot and snapshots.
_MOVE_FIELDS=('x','y','vx','vy','ground','climb','climb_cd','climb_dist','walk_dist','face')


# CITY V8: both towns use ONE continuous ground plane and NO stair state.
CITY_STAIR_CLIMBS=()
def city_stair_step(p,dt,axis):
    return False

def movement_capture(p):
    return tuple(getattr(p,k) for k in _MOVE_FIELDS)


def movement_restore(p,values):
    for key,value in zip(_MOVE_FIELDS,values):setattr(p,key,value)


def movement_change_mode(p,mode):
    p.movement_mode=mode
    p.fast_self_last=None
    p.move_epoch+=1
    p.move_seq=-1
    p.move_budget_x=24.0
    p.move_last_at=time.monotonic()
    p.move_rejects=0
    p.move_recovery_armed=False
    p.buttons=0
    p.last_input=p.move_last_at
    p.move_shadow=movement_capture(p) if mode=='client' else None
    return {'t':'movement_mode_ack','mode':mode,'epoch':p.move_epoch,
            'x':round(p.x,3),'y':round(p.y,3),'vx':round(p.vx,3),'vy':round(p.vy,3),
            'ground':p.ground,'face':p.face,'climb':bool(p.climb),
            'cool':round(p.cool,3),'sta':round(p.sta,3)}


def movement_tick(p,dt,tick_now):
    if p.room in ('city_proto_1','city_inner_1') and p.movement_mode!='server':
        movement_change_mode(p,'server')
    if p.movement_mode!='client' or p.auto_state.enabled:
        update_guest(p,dt,tick_now)
        return
    # While server-forced knockback/death/down is active, the normal DV
    # simulation takes over and the validator baseline follows it.
    if p.dead>0 or p.kb_time>0 or p.stun>0 or p.down>0 or p.hp<=0:
        update_guest(p,dt,tick_now)
        p.move_shadow=movement_capture(p)
        p.move_budget_x=24.0
        p.move_recovery_armed=True
        return
    accepted=movement_capture(p)
    if p.move_shadow is None:p.move_shadow=accepted
    movement_restore(p,p.move_shadow)
    old_buttons=p.buttons
    if (old_buttons & 3) and (old_buttons & 12):p.buttons=old_buttons & ~(4|8)
    update_guest(p,dt,tick_now)
    p.buttons=old_buttons
    p.move_shadow=movement_capture(p)
    movement_restore(p,accepted)
    # Timers/regen/stamina, attack cooldown, and combat stay server-owned.
    # Client's proposal is the sole normal locomotion position source.


def movement_validate(p,m,tick_now):
    if p.room in ('city_proto_1','city_inner_1'): return 'city-single-floor-server-authority'
    if p.movement_mode!='client' or p.auto_state.enabled:
        return 'not-in-client-mode'
    seq=m['seq']
    if seq<=p.move_seq:return 'stale-sequence'
    p.move_seq=seq
    if p.dead>0 or p.kb_time>0 or p.stun>0 or p.down>0 or p.hp<=0:
        return 'forced-server-motion'
    if p.move_recovery_armed:
        # EA: first proposal after server-forced movement must start from the
        # last ACCEPTED position, not a shadow that has already fallen to a
        # different floor while client proposals were suspended. Exactly once
        # per real stun/knockback; never grant arbitrary client re-anchors.
        p.move_shadow=movement_capture(p)
        p.move_budget_x=24.0
        p.move_last_at=tick_now
        p.move_recovery_armed=False
    x,y,vx,vy=m['x'],m['y'],m['vx'],m['vy']
    grounded=m['ground']; climb=m['climb']
    # Bounds and declared state are NEVER trusted as authority.
    if not 27<=x<=city_world_width(p.room)-27 or not (-4800 if p.room in EXPANSION_MAPS else -4500 if p.room in MOUNTAIN_MAPS else -850 if p.room=='forest_fork_11' or p.room in GRANITE_FOREST_MAPS or p.room in GRANITE_WALL_MAPS else -100)<=y<=800:return 'map-bounds'
    if abs(vx)>675 or abs(vy)>1200:return 'velocity-cap'
    if p.room in EXPANSION_MAPS:
        soil_y=expansion_ground_y(EXPANSION_MAPS[p.room],x)
        if soil_y is not None and y>soil_y+.25:return 'terrain-through'
    if p.room in EXPANSION_MAPS and any(x+19>r['x'] and x-19<r['x']+r['w'] and y>r['y']+.1 and y-122<r['y']+r['h']-.1 for r in EXPANSION_MAPS[p.room].get('solids',())):return 'solid-wall'
    expected=p.move_shadow or movement_capture(p)
    ex,ey,evx,evy,eground,eclimb=expected[:6]
    moving_dash=p.action=='dash' and p.action_at<=.32 and p.cool>0
    normal_speed=205*derived_for_snapshot(p)['moveSpeedMultiplier']
    speed=(650 if moving_dash else max(normal_speed,abs(evx)) if p.action=='dash' and p.action_at<.52 else normal_speed)
    elapsed=min(.4,max(0,tick_now-p.move_last_at))
    p.move_last_at=tick_now
    # Token bucket caps short jitter, but cumulative overspeed cannot be
    # hidden by sending lots of small packets. Budget is NEVER reset on accept.
    p.move_budget_x=min(80.0 if moving_dash else 30.0,p.move_budget_x+speed*elapsed)
    delta_x=abs(x-p.x)
    if delta_x>p.move_budget_x+0.001:return 'cumulative-speed'
    if not moving_dash and abs(vx)>max(speed*1.08+5,abs(evx)+45):return 'horizontal-speed'
    if moving_dash and abs(x-p.x)>0.5 and (x-p.x)*p.face<-.25:return 'dash-direction'
    # Reference is advanced by the unchanged DV 30Hz world physics. A bounded
    # lead absorbs one-way latency / Safari frame jitter, NOT long-term speed.
    x_lead=85 if p.action=='dash' and p.action_at<=.52 else 36
    if abs(x-ex)>x_lead:return 'server-shadow-horizontal'
    if abs(y-ey)>78:return 'server-shadow-vertical'
    # Under gravity, clients cannot claim new airborne ascent unless the
    # reference is jumping or legitimately climbing. One-way platforms may
    # be passed on the way UP, but not through during descent.
    if y<min(p.y,ey)-8 and vy<0 and evy>=0 and eclimb is None:return 'unexpected-ascent'
    if climb:
        if eclimb is None:return 'illegal-climb'
        cx,top,bottom=eclimb
        if abs(x-cx)>2 or not top-1<=y<=bottom+1:return 'climb-geometry'
    elif grounded:
        supported=any(lo+8<x<hi-8 and abs(y-top)<=2 for lo,hi,top in active_ground())
        if p.room in EXPANSION_MAPS:
            gy=expansion_ground_y(EXPANSION_MAPS[p.room],x)
            if gy is not None:supported=abs(y-gy)<=2 or any(not q.get('contourGround') and q['x']+8<x<q['x2']-8 and abs(y-q['y'])<=2 for q in EXPANSION_MAPS[p.room]['platforms'])
        if not supported:return 'invalid-ground'
    # Crossing a one-way solid from above to below (descending) is not legal.
    if y>p.y+2 and vy>=0 and not climb:
        collision_lanes=([(q['x'],q['x2'],q['y']) for q in EXPANSION_MAPS[p.room]['platforms'] if not q.get('contourGround')] if p.room in EXPANSION_MAPS else active_ground())
        for lo,hi,top in collision_lanes:
            if lo+8<min(x,p.x) and max(x,p.x)<hi-8 and p.y<=top+2<y-2:
                return 'platform-through'
    if abs(y-p.y)>105 and not climb:return 'vertical-teleport'
    p.move_budget_x=max(0,p.move_budget_x-delta_x)
    p.x,p.y,p.vx,p.vy=x,y,vx,vy
    p.ground=grounded
    p.climb=eclimb if climb else None
    if vx>.5:p.face=1
    elif vx<-.5:p.face=-1
    p.move_recovery_armed=False
    return None


def mob_patrol(m, t):
    lane=own_lane(m)
    if lane is None:return 0
    lo=max(lane[0]+45,m.home-340)
    hi=min(lane[1]-45,m.home+340)
    if lo>=hi:return 0
    if m.patrol_phase=='idle':
        if t<m.patrol_until:return 0
        m.patrol_phase='choose'
    if m.patrol_phase=='choose':
        direction=m.patrol_dir
        if m.x<=lo+26:direction=1
        elif m.x>=hi-26:direction=-1
        elif random.random()<.47:direction=-direction
        duration=3.4+random.random()*2.8
        goal=clamp(m.x+direction*BEAST_PATROL_SPEED*duration,lo,hi)
        if abs(goal-m.x)<24:
            direction=-direction
            goal=clamp(m.x+direction*BEAST_PATROL_SPEED*duration,lo,hi)
        if abs(goal-m.x)<3:
            m.patrol_phase='idle';m.patrol_until=t+2+random.random()*2
            return 0
        m.patrol_dir=direction
        m.patrol_goal_x=goal
        m.patrol_until=t+duration
        m.patrol_phase='walk'
    direction=m.patrol_dir
    if t>=m.patrol_until or (m.x>=m.patrol_goal_x if direction>0 else m.x<=m.patrol_goal_x):
        m.patrol_phase='idle';m.patrol_until=t+2+random.random()*2
        return 0
    if not supported(m,m.x+direction*26):
        m.patrol_dir=-direction
        m.patrol_phase='idle';m.patrol_until=t+2+random.random()*2
        return 0
    return direction*BEAST_PATROL_SPEED


def update_squirrel(m,dt,p,t):
    # Physical peach with a visible wind-up, no magic or client authority.
    # No leap/biting behavior: squirrel attacks at range only.
    stunned=m.down>0 or m.stun>0 or m.broken>0
    if stunned:
        m.vx=0;m.bite_started_at=-1e9;m.bite_hit_done=False
    elif m.bite_started_at>0:
        age=t-m.bite_started_at
        m.vx=0
        if age>=.27 and not m.bite_hit_done:
            m.bite_hit_done=True
            lo,hi=monster_attack_range(m.level,m.zone_mode,False)
            damage=max(1,prog.jsround((lo+hi)*.39))  # ranged early-map tuning; victim DEF still applies
            current_world().peaches.append({'id':f'peach:{m.id}:{server_step}',
                'x':m.x+m.bite_dir*22,'y':m.y-57.0,'vx':m.bite_dir*255.0,
                'life':1.55,'damage':damage})
        if age>=.52:
            m.bite_started_at=-1e9;m.bite_hit_done=False
    elif p and 38<abs(p.x-m.x)<340 and abs(p.y-m.y)<35 and t>=m.bite_ready_at:
        m.bite_started_at=t;m.bite_hit_done=False
        m.bite_dir=1 if p.x>m.x else -1
        m.face=m.bite_dir;m.vx=0
        m.bite_ready_at=t+2.5
    elif p and abs(p.x-m.x)<340:
        # Stand and face the player while waiting to throw; don't walk into them.
        m.vx=0;m.face=1 if p.x>m.x else -1
    else:
        m.vx=mob_patrol(m,t)
    if m.vx:
        direction=1 if m.vx>0 else -1
        if not supported(m,m.x+direction*26):m.vx=0
        else:m.face=direction
    m.x+=m.vx*dt
    physics(m,dt)
    if abs(m.x-m.home)>380:
        m.x=m.home+380*(1 if m.x>m.home else -1);m.vx=0


def update_peach_shots(dt):
    # Server-only projectile collision; shared snapshot is display-only.
    world=current_world()
    alive=[]
    for peach in world.peaches:
        px=peach['x']
        nx=px+peach['vx']*dt
        peach['life']-=dt
        if peach['life']<=0 or not 0<=nx<=city_world_width(current_world().room):continue
        hit=False
        for player in players.values():
            if player.dead>0 or player.hp<=0 or player.climb is not None:continue
            if abs((player.y-57)-peach['y'])>37:continue
            if min(px,nx)-21<=player.x<=max(px,nx)+21:
                if player.inv<=0:
                    dodge=derived_for_snapshot(player)['dodgeVsMonsters']
                    if random.random()*100<dodge:event('miss',player.x,player.y-80,victim=player.id)
                    else:hurt(player,mitigate(peach['damage'],player.defense),px,peach['y'],'monster')
                hit=True
                break
        if hit:
            event('peach_impact',nx,peach['y'])
        else:
            peach['x']=nx
            alive.append(peach)
    world.peaches=alive


def update_mob(m,dt,player_grid=None):
    t=time.monotonic()
    if m.dead>0:
        m.dead=max(0,m.dead-dt)
        if m.dead==0:
            m.hp=m.max_hp
            m.x=m.home;m.y=m.spawn_y
            m.vx=m.vy=m.stun=m.down=m.broken=0
            m.ground=True;m.guard=False
            m.bite_started_at=-1e9;m.bite_hit_done=False
            m.bite_ready_at=t+.45
            m.aggro_until=0;m.retaliate_target='';m.retaliate_until=0;
            m.patrol_phase='idle';m.patrol_until=t+2+random.random()*2;m.last_combat=False;m.mark_stacks.clear()
            m.spawn_at=t
        return
    m.stun=max(0,m.stun-dt)
    m.down=max(0,m.down-dt)
    m.broken=max(0,m.broken-dt)
    # Spatial grid reduces candidates; lane is constant for this target selection.
    # Cache only across candidate checks BEFORE movement, never across game ticks.
    _mob_ai_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
    target_lane=own_lane(m)
    # v8.0DV: one distance calculation per candidate instead of a generator,
    # predicate distance and min-key distance. Strict '<' retains the first
    # actor in stable insertion order on equal distances (original min rule).
    p=None
    nearest=float('inf')
    mx=m.x
    for candidate in candidate_players_by_x(m,player_grid):
        if not reachable_player(m,candidate,target_lane):continue
        distance=abs(candidate.x-mx)
        if distance<BEAST_AGGRO+65 and distance<nearest:
            p=candidate;nearest=distance
    if m.species in BAMBOO_MONSTER_NAMES:
        if t>=m.retaliate_until:
            m.retaliate_target=''
        if not m.retaliate_target or p is None or p.id!=m.retaliate_target:
            # A struck bamboo mob must not choose a different innocent bystander.
            p=next((candidate for candidate in candidate_players_by_x(m,player_grid)
                    if candidate.id==m.retaliate_target and
                    reachable_player(m,candidate,target_lane)),None) if m.retaliate_target else None
        if p is not None and abs(p.x-m.x)>=BEAST_AGGRO+65:
            p=None
    if ENABLE_PERFORMANCE_PROFILER:_profile_add('monster.target_search',time.perf_counter_ns()-_mob_ai_start)
    if m.species=='brush_squirrel':
        return update_squirrel(m,dt,p,t)
    dx=p.x-m.x if p else 0
    dy=p.y-m.y if p else 10000
    near=bool(p and abs(dx)<BEAST_AGGRO)
    if near:m.aggro_until=t+1.25
    engage=bool(p and (near or t<m.aggro_until))
    stopped=m.down>0 or m.stun>0 or m.broken>0
    if stopped:
        m.bite_started_at=-1e9
        m.bite_hit_done=False
    if m.bite_started_at>0 and t-m.bite_started_at>=.42:
        m.bite_started_at=-1e9;m.bite_hit_done=False
    if not stopped and m.bite_started_at<0 and engage and m.ground and t>=m.bite_ready_at and abs(dx)<(46 if m.species in BAMBOO_MONSTER_NAMES else 72) and abs(dy)<62:
        m.bite_started_at=t;m.bite_hit_done=False
        m.bite_dir=1 if dx>=0 else -1
        m.bite_ready_at=t+1.05
    if stopped:
        m.vx=0
    elif m.bite_started_at>0:
        age=t-m.bite_started_at
        m.face=m.bite_dir
        m.vx=m.bite_dir*170 if .11<=age<.23 else 0
    elif engage:
        if not m.last_combat:
            m.patrol_phase='choose'
        m.last_combat=True
        if abs(dx)<=38:m.vx=0
        else:
            direction=1 if dx>0 else -1
            m.vx=direction*BEAST_CHASE_SPEED if supported(m,m.x+direction*28) else 0
    else:
        if m.last_combat:
            m.last_combat=False;m.patrol_phase='idle';m.patrol_until=t+2+random.random()*2
        m.vx=mob_patrol(m,t)
    if m.vx:
        direction=1 if m.vx>0 else -1
        if not supported(m,m.x+direction*26):m.vx=0
        else:m.face=direction
    m.x+=m.vx*dt
    _prof_monster_physics_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
    physics(m,dt)
    if ENABLE_PERFORMANCE_PROFILER:_profile_add('monster.physics',time.perf_counter_ns()-_prof_monster_physics_start)
    if abs(m.x-m.home)>380:
        m.x=m.home+380*(1 if m.x>m.home else -1)
        m.vx=0
    # Bites have an animation wind-up, with real contact damage only after impact.
    if m.bite_started_at>0 and not m.bite_hit_done and t-m.bite_started_at>=.19:
        m.bite_hit_done=True
        if p and p.dead<=0 and abs(p.x-m.x)<(36 if m.species in BAMBOO_MONSTER_NAMES else 60) and abs(p.y-m.y)<60 and p.inv<=0:
            lo,hi=monster_attack_range(m.level,m.zone_mode,False)
            raw=random.randint(lo,hi)
            # Actual Guest defense is gear-derived, not an imaginary +5 armor.
            # .88 source beast bite coefficient is retained from v8.0BQ test map.
            dodge=derived_for_snapshot(p)['dodgeVsMonsters']
            if random.random()*100<dodge:event('miss',p.x,p.y-80,victim=p.id)
            else:hurt(p,mitigate(prog.jsround(raw*.88),p.defense),m.x,m.y-80,'monster')


def spawn_loot_for(killer,m):
    # Exactly one random tier-matched weapon on each beast kill, per Offline createDeathLoot.
    if m.hum or m.species not in ('wolf','boar'):return None
    tier=40 if m.level>=40 else 30 if m.level>=30 else 15 if m.level>=15 else 5
    candidates=[it for it in LOOT_TEMPLATES if it['level']==tier]
    if not candidates:return None
    template=random.choice(candidates)
    x=m.x+random.uniform(-8,8)
    valid=[y for lo,hi,y in active_ground() if lo+12<x<hi-12 and y>=m.y-22]
    ground_y=min(valid) if valid else 550
    now=time.monotonic()
    drop={'id':'loot-'+secrets.token_hex(8),'item_id':template['item_id'],'x':round(x,1),'y':ground_y,
          'ownerId':killer.id,'bornAt':now,'privateUntil':now+LOOT_OWNER_SEC,
          'expiresAt':now+LOOT_LIFETIME_SEC,'pickupAt':now+LOOT_INTRO_SEC}
    loot_drops.append(drop)
    if len(loot_drops)>36:loot_drops.pop(0)
    return drop


def advance_loot():
    t=time.monotonic()
    for drop in loot_drops[:]:
        if t>=drop['expiresAt']:
            loot_drops.remove(drop);continue
        if t<drop['pickupAt']:continue
        # v8.0DV: While the 60-second ownership lock is active there can be
        # exactly ONE eligible guest. Direct-ID lookup replaces O(all guests)
        # scanning per drop per 30Hz tick; same checks and loot/event order.
        # Once public, retain players.values() insertion order verbatim.
        if t<drop['privateUntil']:
            owner=players.get(drop['ownerId'])
            candidates=(owner,) if owner is not None else ()
        else:
            candidates=players.values()
        for p in candidates:
            if p.room!='forest' or p.dead>0 or p.hp<=0 or len(p.inventory)>=LOOT_BAG_CAP:continue
            if abs(p.x-drop['x'])>LOOT_PICKUP_X or abs(p.y-drop['y'])>LOOT_PICKUP_Y:continue
            entry={'uid':'bag-'+secrets.token_hex(8),'item_id':drop['item_id'],'obtainedAt':int(time.time()*1000)}
            p.inventory.append(entry)
            p.inventory_revision += 1
            event('loot_pickup',drop['x'],drop['y'],victim=p.id,item_id=drop['item_id'])
            # Updated bag is sent only to the owner, never copied into public snapshots.
            # The socket event is queued outside the synchronous world update.
            loot_drops.remove(drop)
            break


def grant_monster_kill(s,m):
    killer=players.get(s.owner)
    if killer is None or killer.room!=current_world().room:return
    old_level=killer.level
    award,levels=prog.grant_kill_exp(killer,m.level)
    if levels:
        # Match offline: maintain current HP fraction on level-up.
        fraction=killer.hp/killer.max_hp if killer.max_hp>0 else 1
        prog.apply_derived_resources(killer,hp_reference)
        killer.hp=min(killer.max_hp,prog.jsround(killer.max_hp*fraction))
        event('levelup',killer.x,killer.y-125,victim=killer.id,level=killer.level,levels=levels)
    event('exp',killer.x,killer.y-90,victim=killer.id,amount=award,monsterLevel=m.level)
    spawn_loot_for(killer,m)
    if loadouts.active_qi(killer,1):
        mechanic=loadouts.qi_mechanics(killer,'flute_sustain')
        killer.qi_heal_kills+=1
        if killer.qi_heal_kills>=mechanic['healKills']:
            killer.qi_heal_kills=0
            restore=min(killer.max_hp-killer.hp,max(1,prog.jsround(killer.max_hp*mechanic['healPct']/100)))
            killer.hp+=restore
            event('heal',killer.x,killer.y-110,victim=killer.id,amount=restore)


def hit_by_shot(s,victim,damage,is_mob):
    if is_mob and isinstance(victim,Monster) and victim.species in BAMBOO_MONSTER_NAMES:
        attacker=players.get(s.owner)
        if attacker is not None and attacker.room==current_world().room:
            victim.retaliate_target=attacker.id
            victim.retaliate_until=time.monotonic()+12.0
    previous_alive=victim.hp>0 and victim.dead<=0
    actual=mitigate(damage,victim.defense) if is_mob else damage
    hurt(victim,actual,s.x,s.y,s.kind,critical=s.critical,owner=s.owner)
    if previous_alive and is_mob and victim.hp<=0:grant_monster_kill(s,victim)
    return actual


def bonus_hit(killer, victim, raw,kind='qi_echo'):
    """Qi bonus is a real server-side damage event; never trust client hits."""
    if victim.dead>0 or victim.hp<=0:return 0
    value=mitigate(prog.jsround(raw),victim.defense)  # same DEF/(250+DEF) as Offline
    if victim.species in BAMBOO_MONSTER_NAMES:
        victim.retaliate_target=killer.id;victim.retaliate_until=time.monotonic()+12.0
    victim.hp=max(0,victim.hp-value)
    victim.stun=max(victim.stun,.2)
    victim.vx=0
    victim.bite_started_at=-1e9
    event('hit',victim.x,victim.y-78,victim=victim.id,damage=value,kind=kind,owner=killer.id)
    if victim.hp<=0:
        victim.dead=next_respawn_delay();victim.guard=False
        event('defeat',victim.x,victim.y-80,victim=victim.id)
        grant_monster_kill(type('Owner',(),{'owner':killer.id})(),victim)
    return value


def apply_qi_on_primary_hit(shot,victim,damage):
    killer=players.get(shot.owner)
    if not killer or killer.room!=current_world().room or not isinstance(victim,Monster):return
    if loadouts.active_qi(killer,1) and shot.kind=='attack':
        mechanics=loadouts.qi_mechanics(killer,'flute_sustain')
        if random.random()*100<mechanics['stunPct']:
            victim.stun=max(victim.stun,mechanics['stunSeconds'])
            event('qi_stun',victim.x,victim.y-96,victim=victim.id)
    if loadouts.active_qi(killer,2):
        m=loadouts.qi_mechanics(killer,'death_mark')
        now=time.monotonic();count,expiry=victim.mark_stacks.get(killer.id,(0,0))
        if now>expiry:count=0
        if count>=m['markMaxStacks']:
            victim.mark_stacks[killer.id]=(0,0)
            bonus_hit(killer,victim,damage*m['explosionPct']/100,'death_mark')
            if random.random()*100<m['explosionStunPct']:
                victim.stun=max(victim.stun,m['explosionStunSeconds'])
                event('qi_stun',victim.x,victim.y-96,victim=victim.id)
        else:victim.mark_stacks[killer.id]=(count+1,now+m['markExpireSeconds'])
    if loadouts.active_qi(killer,0) and shot.kind=='attack':
        m=loadouts.qi_mechanics(killer,'flute_echo')
        candidates=[x for x in monsters.values() if x is not victim and x.dead<=0 and x.hp>0 and math.hypot(x.x-victim.x,(x.y-victim.y)*1.5)<=m['echoRange']]
        if candidates:
            target=min(candidates,key=lambda x:math.hypot(x.x-victim.x,x.y-victim.y))
            if not target.guard:bonus_hit(killer,target,damage*m['echoPct']/100,'qi_echo')

# v8.0CA: Guest arena is strictly cooperative PvE, NOT a PK arena.
# Fail closed: even if a future collision caller erroneously passes a Guest,
# do not allow player damage, crowd-control, guard-break or projectile consumption.
def apply_shot(s, victim, is_mob):
    if not is_mob or not isinstance(victim, Monster): return False
    if victim.id in s.hit or victim.dead > 0: return False
    if not is_mob and victim.id == s.owner: return False
    s.hit.add(victim.id)
    if s.kind == 'break':
        if victim.guard and victim.broken <= 0:
            victim.guard = False
            victim.broken = 1.15
            victim.stun = .85
            event('guardbreak', victim.x, victim.y - 78, victim=victim.id)
            return True
        actual=hit_by_shot(s,victim,s.damage,is_mob)
        if is_mob and victim.hp>0:apply_qi_on_primary_hit(s,victim,actual)
        s.pierce -= 1
        return s.pierce <= 0
    if victim.guard and victim.broken <= 0:
        event('block', victim.x, victim.y - 82, victim=victim.id)
        return True
    if not is_mob and victim.inv > 0: return False
    dmg = int(s.damage * (0.78 if not is_mob else 1))
    actual=hit_by_shot(s,victim,dmg,is_mob)
    if is_mob and victim.hp>0:apply_qi_on_primary_hit(s,victim,actual)
    if s.kind == 'aoe' and victim.dead <= 0:
        victim.down = max(victim.down, 1)
        if victim.climb is not None:
            victim.climb = None
            victim.climb_cd = .6
            victim.vy = 90
            victim.ground = False
    if s.kind == 'aoe': return False
    s.pierce -= 1
    return s.pierce <= 0


# v8.0CQ: 1D broadphase for swept projectiles. Per-tick only (monsters move and
# can die during a shot). Keep old narrowphase/ordering as the reference.
SHOT_CELL = 160
SHOT_GRID_MIN_SHOTS = 4
SHOT_GRID_MIN_MONSTERS = 16


def update_shots(dt):
    # Do not pay the index build cost for small combat encounters. Index stores
    # ORIGINAL insertion index, preserving Python's stable sort on tied x values.
    grid = None
    if len(shots) >= SHOT_GRID_MIN_SHOTS and len(monsters) >= SHOT_GRID_MIN_MONSTERS:
        grid = defaultdict(list)
        for order, monster in enumerate(monsters.values()):
            grid[int(monster.x // SHOT_CELL)].append((order, monster))
    active = []
    for s in shots:
        old_x = s.origin_x if s.origin_x is not None else s.x
        s.origin_x = None  # only the first tick starts at the owner's center
        s.life -= dt
        s.x += s.vx * dt
        if s.life <= 0: continue
        # Original exact swept collision: do NOT change strict comparisons,
        # height, wall edge rules, multi-target pierce or first-tick origin.
        lo, hi = min(old_x, s.x), max(old_x, s.x)
        radius = 60 if s.kind == 'aoe' else 36
        if grid is None:
            victims = [v for v in monsters.values() if v.dead <= 0 and
                       abs(v.y - s.y - 78) < 95 and lo-radius < v.x < hi+radius]
            victims.sort(key=lambda v: (v.x-old_x)*(1 if s.vx >= 0 else -1))
        else:
            # Gather from exactly those x cells crossed by the swept segment.
            # Use an insertion-order tie breaker, including across cell boundaries.
            ranked = []
            for cell in range(int((lo-radius)//SHOT_CELL),
                              int((hi+radius)//SHOT_CELL)+1):
                for order, v in grid.get(cell, ()):
                    if v.dead <= 0 and abs(v.y-s.y-78) < 95 and lo-radius < v.x < hi+radius:
                        ranked.append(((v.x-old_x)*(1 if s.vx >= 0 else -1), order, v))
            ranked.sort(key=lambda x: (x[0], x[1]))
            victims = [item[2] for item in ranked]
        consumed = False
        for v in victims:
            if apply_shot(s, v, isinstance(v, Monster)):
                consumed = True
                break
        if not consumed and -80 <= s.x <= city_world_width(current_world().room) + 80: active.append(s)
    shots[:] = active


def actor_frame(a, tick):
    if a.dead > 0: return 18 if a.ground else 16
    if a.down > 0: return 17 if a.ground else 16
    if isinstance(a,Guest) and a.room=='city_proto_1' and a.climb in CITY_STAIR_CLIMBS:
        return 3 + (int(a.climb_dist / 18) % 4)
    if a.climb: return 14 + (int(a.climb_dist / 64) % 2)
    if isinstance(a,Guest) and a.kb_time>0:return 9
    if a.stun > .02: return 9
    if a.guard: return 8
    if a.action == 'attack' and a.action_at < a.action_duration: return 19 if a.action_at < .09 else 20 if a.action_at < .21 else 21
    if a.action == 'aoe' and a.action_at < a.action_duration: return 22 if a.action_at < .14 else 23
    if a.action == 'break' and a.action_at < a.action_duration: return 7 if a.action_at < .14 else 8
    if a.action == 'dash' and a.action_at < a.action_duration: return 10 if a.action_at < .12 else 11
    if not a.ground: return 12 if a.vy < 0 else 13
    if abs(a.vx) > 25: return 3 + (int(a.walk_dist / 20) % 4)
    return int(tick / 17) % 3


def actor_visual_face(a):
    # A caster may walk LEFT while shooting RIGHT. Report the cast facing for
    # both self and remote sprites during the attack animation; keep a.face
    # as the actual movement/dash orientation for server mechanics.
    if (isinstance(a,Guest) and a.action in ATTACKS and a.action_at<a.action_duration
            and not (a.dead>0 or a.down>0 or a.stun>0.02 or a.guard or a.climb)
            and a.cast_face in (-1,1)):
        return a.cast_face
    return a.face


def actor_json(a):
    return {'id': a.id, 'level': a.level if isinstance(a,(Guest,Monster)) else 1, 'x': round(a.x, 2), 'y': round(a.y, 2), 'vx': round(a.vx, 2), 'vy': round(a.vy, 2),
            'face': actor_visual_face(a), 'hp': a.hp, 'max': a.max_hp, 'ground': a.ground, 'guard': a.guard, 'down': round(a.down, 2), 'dead': round(a.dead, 2),
            'stun': round(a.stun, 2), 'inv': round(a.inv, 2), 'climb': bool(a.climb), 'frame': actor_frame(a, server_step), 'action': a.action,
            **({'defense':a.defense} if isinstance(a,Monster) else {'lastAppliedSeq':a.applied_input_seq})}


def derived_for_snapshot(p):
    # Dirty-signature cache: recompute expensive gear/qi/derived totals only
    # after server-owned level/stat/qi/equipment state changes, not every 100ms.
    # v8.0DV: most production players have no QA qi ranks. Skip allocating
    # sorted generator/tuples on every 30Hz tick for the empty case; retain
    # the original canonical signature for nonempty ranks and all changes.
    qi_sig=(tuple(sorted((k,tuple(sorted(v.items()))) for k,v in p.qi_ranks.items()))
            if p.qi_ranks else ())
    sig=(p.level,p.test_level,tuple(p.stats[k] for k in prog.STAT_KEYS),
         tuple(p.qi_equipped),qi_sig,
         p.gear_level,p.gear_def_row,p.gear_atk_row,p.gear_enhancement)
    if sig!=p.stable_stats_key:
        p.stable_stats_key=sig
        p.stable_derived_stats=prog.derive_stats(p,hp_reference)
    return p.stable_derived_stats

def private_progression(p):
    return {'expWithinLevel':p.exp,'expToNext':prog.exp_to_next(p.level),
            'statPoints':p.stat_points,'skillPoints':p.skill_points,'totalKills':p.total_kills,
            'stats':p.stats,'skillRanks':p.skill_ranks,
            'sp':round(p.sp,2),'maxSp':p.max_sp,'sta':round(p.sta,2),'maxSta':p.max_sta,
            'defense':p.defense,'derived':derived_for_snapshot(p),
            'movementForced':bool(p.kb_time>0 or p.stun>0 or p.down>0 or p.dead>0 or p.hp<=0),
            'auto':p.auto_state.enabled,'autoRevision':p.auto_revision,'autoStay':p.auto_state.stay_alert,'autoAnchor':(dict(p.auto_state.anchor) if p.auto_state.stay_alert and p.auto_state.anchor else None),'autoTarget':(dict(p.auto_state.goal) if p.auto_state.enabled and p.auto_state.goal else None),
            'autoTargetSeconds':round(max(0,p.auto_state.goal_due-time.monotonic()),1) if p.auto_state.enabled else 0,
            'sandboxAvailable':ENABLE_GUEST_SANDBOX,'inputAck':p.applied_input_seq,'performance':perf_data.copy(),**(loadouts.private_snapshot(p) if ENABLE_GUEST_SANDBOX else {})}


# v8.0CR reuse the exact stdlib encoder config instead of constructing a
# JSONEncoder object on every 10Hz packet. Still JSON/UTF-8, wire-identical:
# default ensure_ascii=True, allow_nan=True, sort_keys=False and same separators.
_COMPACT_WIRE_JSON_ENCODER=json.JSONEncoder(separators=(',',':'))

# v8.0BY network scalability: one server-owned world sample per 100ms.
# AOI is strictly visual; hit detection and rewards still use ALL server actors.
AOI_RADIUS=int(os.environ.get('AOI_RADIUS','950'))
if AOI_RADIUS<700 or AOI_RADIUS>6000:raise ValueError('AOI_RADIUS must be 700..6000')
DELTA_REFRESH_TICKS=150 # 5 seconds at 30Hz, periodic full keyframe self-heals missed state.


class SharedSnapshot(dict):
    """Wire-compatible dict with a private cache shared by per-client delta encoders.
    Cache lifetime equals this one world sample; it is never serialized or global.
    """
    __slots__ = ('entity_patch_cache','aoi_bucket_cache','packed_entry_cache','created_monotonic','all_forest_players','event_highwater')

    def __init__(self, content):
        super().__init__(content)
        self.entity_patch_cache = {}
        self.packed_entry_cache = {}
        self.aoi_bucket_cache = {}
        self.created_monotonic = time.monotonic()
        # Default FALSE for manually assembled snapshots / test fixtures.
        self.all_forest_players = False
        self.event_highwater = 0


# v8.0CU: shared X broadphase for AUTO targets (built at most once per
# decision tick). This is an optimization only: values() retains original order
# so tie-breaking and 0.75s target locks remain deterministic.
AUTO_QUERY_CELL=256
AUTO_QUERY_MIN_MOBS=48
class AutoMonsterCandidates:
    __slots__=('source','cells')
    def __init__(self, source):
        self.source=source
        self.cells={}
        for index,m in enumerate(source.values()):
            self.cells.setdefault(int(m.x//AUTO_QUERY_CELL),[]).append((index,m))
    def near(self,x,radius=305):
        lo=int((x-radius)//AUTO_QUERY_CELL)
        hi=int((x+radius)//AUTO_QUERY_CELL)
        candidates=[pair for cell in range(lo,hi+1) for pair in self.cells.get(cell,())]
        candidates.sort(key=lambda item:item[0])
        return [m for _,m in candidates if abs(m.x-x)<radius]

# v8.0CX: bounded structural sharing across consecutive 10Hz world samples.
# A dict with unchanged wire values reuses the exact immutable-by-convention
# object reference. Per-client delta baselines only update after send success;
# identity therefore safely bypasses redundant field comparisons, even if
# other clients skipped mailbox samples. No revision numbers are sent on wire.
# Snapshot structural sharing must NEVER reuse entities across channels.
# Each world owns its own previous-entity cache.


def _reuse_snapshot_entities(kind, entries):
    cache = current_world().snapshot_previous
    old = cache[kind]
    next_entities = {}
    result = []
    for entry in entries:
        eid = entry['id']
        previous = old.get(eid)
        if previous is not None and previous == entry:
            entry = previous
        next_entities[eid] = entry
        result.append(entry)
    cache[kind] = next_entities
    return result


def snapshot():
    """Shared immutable-by-convention world state; no per-guest JSON on the tick path."""
    moment=time.monotonic()
    # A joined player's room cannot change during a socket session. When all
    # actors are forest guests there is no foreign room to filter in 100 per-
    # client AOI views. Existing in-flight snapshots stay safe on disconnect.
    forest_only=all(p.room=='forest' for p in players.values())
    world=SharedSnapshot({'t':'snapshot','tick':server_step,
            'players':_reuse_snapshot_entities('players',[{**actor_json(p),'avatar':p.avatar} for p in players.values()]),
            'mobs':_reuse_snapshot_entities('mobs',[{**actor_json(m),'name':m.name,'hum':m.hum,'species':m.species,
                     'biteAge':round(max(0,moment-m.bite_started_at),3) if m.bite_started_at>0 else -1,
                     'spawnId':m.slot} for m in monsters.values()]),
            'loot':_reuse_snapshot_entities('loot',[{'id':d['id'],'item_id':d['item_id'],'x':d['x'],'y':d['y'],
                     'ownerId':d['ownerId'],'privateFor':round(max(0,d['privateUntil']-moment),1),
                     'expiresIn':round(max(0,d['expiresAt']-moment),1)} for d in loot_drops]),
            'shots':_reuse_snapshot_entities('shots',
                [{'id':str(s.id),'kind':s.kind,'x':round(s.x,1),'y':round(s.y,1),
                  'dir':1 if s.vx>=0 else -1} for s in shots] +
                [{'id':s['id'],'kind':'peach','x':round(s['x'],1),'y':round(s['y'],1),
                  'dir':1 if s['vx']>=0 else -1} for s in current_world().peaches]),
            'events':events[:80]})
    world.all_forest_players=forest_only
    world.event_highwater=current_world().event_seq
    return world


# Share a positional coarse index within ONE immutable SharedSnapshot only.
# 64+ entities is the break-even guard: ordinary 20-mob test maps keep the
# original fast linear scan. Candidate hits are restored to original insertion
# order, and final filtering always uses the EXACT old abs() comparison.
AOI_INDEX_MIN_ENTITIES=64
AOI_INDEX_CELL=240


def _aoi_entities(world,kind,p,cx,radius):
    entities=world[kind]
    if not isinstance(world,SharedSnapshot) or len(entities)<AOI_INDEX_MIN_ENTITIES:
        if kind=='players':
            return {e['id']:e for e in entities if e['id']==p.id or abs(e['x']-cx)<=radius}
        return {e['id']:e for e in entities if abs(e['x']-cx)<=radius}
    buckets=world.aoi_bucket_cache.get(kind)
    if buckets is False:
        if kind=='players':
            return {e['id']:e for e in entities if e['id']==p.id or abs(e['x']-cx)<=radius}
        return {e['id']:e for e in entities if abs(e['x']-cx)<=radius}
    if buckets is None:
        # If the entire map section fits inside roughly one AOI, sorting
        # candidates costs more than a plain list comprehension.
        xlo=min(e['x'] for e in entities)
        xhi=max(e['x'] for e in entities)
        if xhi-xlo<=radius*4:
            world.aoi_bucket_cache[kind]=False
            if kind=='players':
                return {e['id']:e for e in entities if e['id']==p.id or abs(e['x']-cx)<=radius}
            return {e['id']:e for e in entities if abs(e['x']-cx)<=radius}
        buckets={}
        for idx,e in enumerate(entities):
            buckets.setdefault(int(e['x']//AOI_INDEX_CELL),[]).append((idx,e))
        world.aoi_bucket_cache[kind]=buckets
        if kind=='players':
            world.aoi_bucket_cache['players_by_id']={e['id']:(idx,e) for idx,e in enumerate(entities)}
    lo=int((cx-radius)//AOI_INDEX_CELL)
    hi=int((cx+radius)//AOI_INDEX_CELL)
    selected=[entry for cell in range(lo,hi+1) for entry in buckets.get(cell,())]
    # Preserve the 'self always visible' rule even if p.x has moved between
    # snapshot creation and this writer's turn. Never index by live actor position.
    if kind=='players':
        self_entry=world.aoi_bucket_cache['players_by_id'].get(p.id)
        if self_entry is not None and not lo<=int(self_entry[1]['x']//AOI_INDEX_CELL)<=hi:
            selected.append(self_entry)
    selected.sort(key=lambda entry:entry[0])
    if kind=='players':
        return {e['id']:e for _,e in selected if e['id']==p.id or abs(e['x']-cx)<=radius}
    return {e['id']:e for _,e in selected if abs(e['x']-cx)<=radius}


def aoi_view(world,p):
    """Exact v8.0CQ wire semantics; indexed only for dense immutable worlds."""
    cx=p.x
    radius=AOI_RADIUS
    ranged_radius=radius+200
    # One-time per-world decision; a 100-mob but COMPACT map shouldn't route
    # every viewer through the indexed path just because its roster is large.
    # For ordinary forest maps this branch skips all index setup.
    use_index=False
    if isinstance(world,SharedSnapshot):
        if (len(world['players'])<AOI_INDEX_MIN_ENTITIES and
            len(world['mobs'])<AOI_INDEX_MIN_ENTITIES and
            len(world['shots'])<AOI_INDEX_MIN_ENTITIES and
            len(world['loot'])<AOI_INDEX_MIN_ENTITIES):
            use_index=False
        else:
            use_index=world.aoi_bucket_cache.get('_use_index')
            if use_index is None:
                use_index=False
                for kind,extra in (('players',0),('mobs',200),('shots',200),('loot',0)):
                    entities=world[kind]
                    if len(entities)<AOI_INDEX_MIN_ENTITIES:continue
                    lo=min(e['x'] for e in entities)
                    hi=max(e['x'] for e in entities)
                    if hi-lo>4*(radius+extra):use_index=True
                    else:world.aoi_bucket_cache[kind]=False
                world.aoi_bucket_cache['_use_index']=use_index
    if not use_index:
        return {
            'players':{e['id']:e for e in world['players'] if e['id']==p.id or abs(e['x']-cx)<=radius},
            'mobs':{e['id']:e for e in world['mobs'] if abs(e['x']-cx)<=ranged_radius},
            'shots':{e['id']:e for e in world['shots'] if abs(e['x']-cx)<=ranged_radius},
            'loot':{e['id']:e for e in world['loot'] if abs(e['x']-cx)<=radius},
        }
    return {'players':_aoi_entities(world,'players',p,cx,radius),
            'mobs':_aoi_entities(world,'mobs',p,cx,ranged_radius),
            'shots':_aoi_entities(world,'shots',p,cx,ranged_radius),
            'loot':_aoi_entities(world,'loot',p,cx,radius)}


def encode_aoi_delta(world,p,previous,last_full_tick,prev_private=None,prev_inventory=None,events_override=None):
    """Diff from LAST SUCCESSFULLY SENT packet, not the newest queued packet.
    Dropped mailbox packets can't corrupt the next delta's baseline.
    """
    _trace_writer=ENABLE_PERFORMANCE_PROFILER or (p.writer_probe_counter & 31)==0
    p.writer_probe_counter+=1
    if _trace_writer:_writer_aoi_start=time.perf_counter_ns()
    current=aoi_view(world,p)
    if p.room=='movement_lab':
        # The movement laboratory has no combat entities by design.
        current['players']={eid:e for eid,e in current['players'].items() if players.get(eid) is not None and players[eid].room==p.room}
        current['mobs']={};current['shots']={};current['loot']={}
    elif p.room.startswith('bamboo_'):
        # LIVE bamboo maps: do NOT clear the server-owned mobs, peach shots or loot.
        # The old shared movement_lab filter accidentally made them invisible while
        # leaving authoritative collisions/damage active in world simulation.
        current['players']={eid:e for eid,e in current['players'].items() if players.get(eid) is not None and players[eid].room==p.room}
    elif not (isinstance(world,SharedSnapshot) and world.all_forest_players):
        # v8.0DV: keep original live room filter for mixed-room worlds;
        # avoid rebuilding a large identical dict for forest-only worlds.
        current['players']={eid:e for eid,e in current['players'].items() if (players.get(eid) is None or players[eid].room==p.room)}
    if _trace_writer:
        _writer_stage_samples['aoi'].append((time.perf_counter_ns()-_writer_aoi_start)/1e6)
        if ENABLE_PERFORMANCE_PROFILER:_profile_add('writer.aoi',time.perf_counter_ns()-_writer_aoi_start)
        _writer_delta_start=time.perf_counter_ns()
    full=previous is None or world['tick']-last_full_tick>=DELTA_REFRESH_TICKS
    result={'t':'snapshot','tick':world['tick']}
    # Per-sample shared cache; no recalculation of lookup or isinstance inside
    # each per-kind/per-entity iteration. Cache pins old/new dict references.
    cache=world.entity_patch_cache if isinstance(world,SharedSnapshot) else None
    if full:
        result['full']=True
        for kind in current:result[kind]=list(current[kind].values())
    else:
        result['delta']=True
        for kind,entities in current.items():
            before=previous[kind]
            changed=[]
            for key,item in entities.items():
                old=before.get(key)
                if old is None:changed.append(item)
                else:
                    # Most viewers compare the SAME two server-owned entity dicts.
                    # Reuse their patch within this shared world sample, but key by
                    # both actual object identities: each client may have a different
                    # last-successfully-SENT baseline after mailbox drops.
                    if old is item:
                        # Structural sharing proves equality even for clients
                        # whose previous successful send was several ticks ago.
                        continue
                    cache_key=(id(old),id(item)) if cache is not None else None
                    entry=cache.get(cache_key) if cache is not None else None
                    if entry is not None:
                        patch=entry[2]
                    elif old == item:
                        patch=None
                        if cache is not None and len(cache)<2048:cache[cache_key]=(old,item,patch)
                    else:
                        patch={'id':key}
                        for attr,value in item.items():
                            if attr!='id' and old.get(attr)!=value:patch[attr]=value
                        if cache is not None and len(cache)<2048:cache[cache_key]=(old,item,patch)
                    if patch is not None and len(patch)>1:changed.append(patch)
            result[kind]=changed
            missing=[key for key in before if key not in entities]
            if missing:result['removed'+kind.capitalize()]=missing
    # A positional event from another room is never allowed to bleed across rooms.
    # Events without actor IDs belong to the original forest world only.
    def visible_room_event(e):
        source_id=e.get('owner') or e.get('victim')
        source=players.get(source_id) if source_id else None
        if source is not None:return source.room==p.room
        # Events come from this already room-isolated world; monster IDs are not guests.
        return p.world_ref.room==p.room
    # EL: pending_world_events() already applies the exact room and AOI
    # predicate. Its bounded result is socket-local, and this function is
    # synchronous; repeating visibility checks wastes work without adding
    # protection. Retain the legacy filtering when no override is supplied.
    if events_override is not None:
        result['events']=events_override
    else:
        result['events']=[e for e in world['events'] if visible_room_event(e) and
                          (e.get('victim')==p.id or e.get('owner')==p.id or
                           abs(float(e.get('x',p.x))-p.x)<=AOI_RADIUS+200)]
    if _trace_writer:
        _writer_stage_samples['delta'].append((time.perf_counter_ns()-_writer_delta_start)/1e6)
        if ENABLE_PERFORMANCE_PROFILER:_profile_add('writer.delta',time.perf_counter_ns()-_writer_delta_start)
        _writer_private_start=time.perf_counter_ns()
    priv=private_progression(p)
    priv['inputAck']=current['players'][p.id]['lastAppliedSeq']
    if full or prev_private is None:
        result['self']=priv
    else:
        result['self']={k:v for k,v in priv.items() if prev_private.get(k)!=v}
    # Immutable-by-copy ownership baseline: most 10Hz packets do not change
    # inventory. Compare live data first; copy only when baseline changed.
    global _em_inv_fast_reuse, _em_inv_full_compare, _em_inv_copy
    # Safe only because the current Guest inventory is mutated in exactly one
    # authoritative pickup path, which increments inventory_revision.
    reuse_revision=(ENABLE_EM_INVENTORY_REV and not full and prev_inventory is not None
                    and p.writer_inventory_revision==p.inventory_revision
                    and len(prev_inventory)==len(p.inventory))
    if reuse_revision:
        _em_inv_fast_reuse+=1
        inv=prev_inventory
    elif not full and prev_inventory is not None:
        _em_inv_full_compare+=1
        if prev_inventory==p.inventory:
            inv=prev_inventory
        else:
            inv=[dict(e) for e in p.inventory]
            _em_inv_copy+=1
    else:
        inv=[dict(e) for e in p.inventory]
        _em_inv_copy+=1
    if full or inv is not prev_inventory:
        result['inventory']=inv
    if _trace_writer:
        _writer_stage_samples['private'].append((time.perf_counter_ns()-_writer_private_start)/1e6)
        if ENABLE_PERFORMANCE_PROFILER:_profile_add('writer.private',time.perf_counter_ns()-_writer_private_start)
        _writer_json_start=time.perf_counter_ns()
    if getattr(p,'protocol_binary',False):
        cache=world.packed_entry_cache if isinstance(world,SharedSnapshot) else None
        packet=encode_compact_snapshot_ek(result,cache)
    else:
        packet=_COMPACT_WIRE_JSON_ENCODER.encode(result)
    if _trace_writer:
        _writer_stage_samples['json'].append((time.perf_counter_ns()-_writer_json_start)/1e6)
        if ENABLE_PERFORMANCE_PROFILER:_profile_add('writer.json',time.perf_counter_ns()-_writer_json_start)
    if ENABLE_PERFORMANCE_PROFILER and (p.writer_probe_counter & 31)==1:
        _em_writer_samples['samples']+=1
        _em_writer_samples['packetBytes']+=len(packet)
        _em_writer_samples['privateBytes']+=len(_COMPACT_WIRE_JSON_ENCODER.encode(result.get('self',{})))
        _em_writer_samples['privateChangedKeys']+=len(result.get('self',{}))
        _em_writer_samples['entities']+=sum(len(result.get(k,())) for k in packed_wire.KINDS)
        _em_writer_samples['inventorySize']+=len(p.inventory)
        _em_writer_samples['events']+=len(result.get('events',()))
    return (packet,current,
            (world['tick'] if full else last_full_tick),priv,inv)


# EK: collect at most one bounded chunk from the world journal, preserving
# causal server order even when the one-slot snapshot mailbox discards frames.
# Event cursor is per socket and updated ONLY after successful send.
# A bounded amount of visual history may catch up after overwritten snapshots.
# NEVER let a burst of accumulated hits multiply outgoing bandwidth unboundedly.
EVENT_REPLAY_TTL = 4.0
EVENT_MAX_PER_PACKET = 32
EVENT_MAX_BYTES_PER_PACKET = 2048


def event_visible_to_guest(e, p):
    # Exact same room and AOI rules as previous v8.0EJ snapshot path.
    source_id = e.get('owner') or e.get('victim')
    source = players.get(source_id) if source_id else None
    if (source.room == p.room if source is not None else p.world_ref.room == p.room) is False:
        return False
    return (e.get('victim') == p.id or e.get('owner') == p.id or
            abs(float(e.get('x', p.x)) - p.x) <= AOI_RADIUS + 200)


def pending_world_events(p, highwater):
    journal = p.world_ref.event_journal
    if not journal or highwater <= p.event_cursor:
        return [], p.event_cursor
    now = time.monotonic()
    payload = []
    cursor = p.event_cursor
    bytes_used = 0
    if ENABLE_EN_EVENT_SCAN:
        # event_seq is strictly monotonic within a world's deque, including
        # after hibernation (the deque is cleared, but seq is not reset).
        # Iterate from newest to oldest and stop at LAST SUCCESSFUL send.
        # Reversing the short candidate list restores original causal order.
        # Crucially, this avoids scanning up to 2048 old events PER SOCKET at
        # every 10Hz writer cycle once the bounded journal fills up.
        newer=[]
        for entry in reversed(journal):
            if entry[0] > highwater:
                continue
            if entry[0] <= cursor:
                break
            newer.append(entry)
        candidate_records=reversed(newer)
    else:
        candidate_records=journal
    for seq, created, item, event_bytes in candidate_records:
        if seq <= cursor: continue
        if seq > highwater: break
        # Invisible/expired events do not consume recipient budget.
        if now-created>EVENT_REPLAY_TTL or not event_visible_to_guest(item, p):
            cursor = seq
            continue
        if len(payload) >= EVENT_MAX_PER_PACKET or (payload and bytes_used + event_bytes > EVENT_MAX_BYTES_PER_PACKET):
            break  # preserve causal order; next successful packet drains remainder
        payload.append(item)
        cursor = seq
        bytes_used += event_bytes
    # Evicted records are no longer available. This never replays old history.
    if not payload and cursor < highwater and (not journal or journal[-1][0] <= highwater):
        cursor = highwater
    return payload, cursor


async def snapshot_writer(p: Guest):
    """Stagger 10Hz sending, serialize/diff per client in that phase (not game tick).
    Bounded one-snapshot mailbox; one slow socket cannot block simulation.
    """
    previous=None;last_full_tick=-1;prev_private=None;prev_inventory=None
    try:
        while True:
            world=await p.snapshot_outbox.get()
            slot_start=time.monotonic()
            _prof_slot_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
            if ENABLE_EL_SNAPSHOT_SCHED and isinstance(world, SharedSnapshot):
                # EK produces each world every 100ms but offsets worlds across
                # three 30Hz ticks. Waiting for a global modulo-100ms socket
                # slot can miss the just-created sample and add ~100ms latency.
                # Instead stagger sockets across 22.5ms AFTER this world sample.
                # Overdue samples are immediately eligible (no wrap-around).
                stagger = (p.snapshot_slot % STAGGER_SLOTS) * .0025
                wait = max(0.0, world.created_monotonic + stagger - slot_start)
            else:
                # Exact EK fallback for A/B and immediate rollback.
                period=.1;offset=p.snapshot_slot*(period/STAGGER_SLOTS)
                wait=(offset-(slot_start%period))%period
                if EO_WRITER_WAIT_CAP_MS and wait > EO_WRITER_WAIT_CAP_MS / 1000.0:
                    wait = EO_WRITER_WAIT_CAP_MS / 1000.0
            if wait>.001:await asyncio.sleep(wait)
            if ENABLE_PERFORMANCE_PROFILER:_profile_add('writer.slot_wait_intentional',time.perf_counter_ns()-_prof_slot_start)
            _cv_writer_wait.append((time.monotonic()-slot_start)*1000)
            # Consume the newest world, if producer overran our send slot.
            while not p.snapshot_outbox.empty():
                try:world=p.snapshot_outbox.get_nowait()
                except asyncio.QueueEmpty:break
                else:
                    global _cv_outbox_skipped
                    _cv_outbox_skipped+=1
            if isinstance(world,SharedSnapshot):
                _cv_snapshot_age.append((time.monotonic()-world.created_monotonic)*1000)
            event_highwater=(world.event_highwater if isinstance(world,SharedSnapshot) else p.world_ref.event_seq)
            pending_events,event_cursor=pending_world_events(p,event_highwater)
            encode_start=time.monotonic()
            # Snapshot the revision BEFORE any socket await. Loot may arrive
            # while send is suspended; only acknowledge the version encoded.
            encoded_inventory_revision=p.inventory_revision
            _prof_encode_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
            if p.protocol_delta:
                packet,current,full_tick,priv,inv=encode_aoi_delta(world,p,previous,last_full_tick,prev_private,prev_inventory,pending_events)
            else:
                # Legacy clients receive original full-world shape until upgraded.
                old=dict(world);old['players']=[a for a in world['players'] if (players.get(a['id']) is None or players[a['id']].room==p.room)];old['self']=private_progression(p);old['inventory']=p.inventory;old['events']=pending_events
                packet=_COMPACT_WIRE_JSON_ENCODER.encode(old)
                current,full_tick,priv,inv=None,-1,None,None
            perf_encodes.append(time.monotonic()-encode_start)
            if ENABLE_PERFORMANCE_PROFILER:_profile_add('writer.encode_total',time.perf_counter_ns()-_prof_encode_start)
            try:
                send_start=time.monotonic()
                _prof_lock_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                async with p.ws_send_lock:
                    if ENABLE_PERFORMANCE_PROFILER:
                        _profile_add('writer.send_lock_wait',time.perf_counter_ns()-_prof_lock_start)
                        _prof_send_start=time.perf_counter_ns()
                    async with asyncio.timeout(1.5):
                        await p.ws.send(packet)
                    if ENABLE_PERFORMANCE_PROFILER:_profile_add('writer.send_await',time.perf_counter_ns()-_prof_send_start)
                global _diag_sent
                _diag_sent+=1
                _diag_send_durations.append((time.monotonic()-send_start)*1000)
                if _diag_send_durations[-1]>=50:_cv_send_spikes.append(_diag_send_durations[-1])
                _writer_stage_samples['send'].append((time.monotonic()-send_start)*1000)
                global perf_out_bytes
                # The default JSONEncoder ensure_ascii=True escapes every non-ASCII
                # codepoint, so wire UTF-8 byte length equals character count.
                perf_out_bytes += len(packet)
                previous,last_full_tick=current,full_tick
                p.event_cursor=event_cursor
                prev_private,prev_inventory=priv,inv
                p.writer_inventory_revision=encoded_inventory_revision
                if p.view_mode=='active':
                    sent_now=time.monotonic()
                    if p.snapshot_last_sent_at:
                        # This is REAL observed send cadence inside the server.
                        # Do not combine with hidden/background 1Hz traffic.
                        _cv_active_snapshot_gap.append((sent_now-p.snapshot_last_sent_at)*1000)
                    p.snapshot_last_sent_at=sent_now
                else:
                    p.snapshot_last_sent_at=0.0
            except (asyncio.TimeoutError,ConnectionClosed,OSError):
                try:await p.ws.close(code=1011,reason='Snapshot send timeout')
                except Exception:pass
                return
    except asyncio.CancelledError:return



# EC: Tiny owner-only packet after authoritative physics; never includes other
# players/mobs or client-supplied positions. world/AOI remains 10Hz.
def enqueue_fast_self(p: Guest):
    if not (ENABLE_FAST_SELF_30HZ and p.fast_self_mode and p.movement_mode=='server'
            and p.view_mode=='active' and not p.auto_state.enabled
            and p.fast_self_task and not p.fast_self_task.done()):
        return
    state=(round(p.x,2),round(p.y,2),round(p.vx,2),round(p.vy,2),
           p.ground,bool(p.climb),actor_visual_face(p),actor_frame(p,server_step),p.applied_input_seq)
    if state==p.fast_self_last:return # idle bandwidth: send only when state changes
    p.fast_self_last=state
    packet=_COMPACT_WIRE_JSON_ENCODER.encode({'t':'self_pos','tick':server_step,'epoch':p.fast_self_epoch,
        'x':state[0],'y':state[1],'vx':state[2],'vy':state[3],
        'ground':state[4],'climb':state[5],'face':state[6],
        'frame':state[7],'lastAppliedSeq':state[8]})
    q=p.fast_self_outbox
    if q.full():
        global _fast_self_skipped
        _fast_self_skipped+=1
        try:q.get_nowait()
        except asyncio.QueueEmpty:pass
    try:q.put_nowait(packet)
    except asyncio.QueueFull:pass

async def fast_self_writer(p: Guest):
    """Latest-only self stream, no 30Hz world re-encode. Shared socket lock
    with the 10Hz writer and a bounded mailbox to prevent stale buildup."""
    try:
        while True:
            packet=await p.fast_self_outbox.get()
            _prof_self_lock_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
            async with p.ws_send_lock:
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('self.send_lock_wait',time.perf_counter_ns()-_prof_self_lock_start)
                # If snapshot send held the lock, always send newest available.
                while not p.fast_self_outbox.empty():
                    try:packet=p.fast_self_outbox.get_nowait()
                    except asyncio.QueueEmpty:break
                if not (p.fast_self_mode and p.movement_mode=='server' and
                        p.view_mode=='active' and ENABLE_FAST_SELF_30HZ
                        and not p.auto_state.enabled):continue
                try:
                    _prof_self_send_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                    async with asyncio.timeout(1.5):
                        await p.ws.send(packet)
                    if ENABLE_PERFORMANCE_PROFILER:_profile_add('self.send_await',time.perf_counter_ns()-_prof_self_send_start)
                    global _fast_self_sent,_fast_self_bytes,perf_out_bytes
                    _fast_self_sent+=1
                    global _em_fast_self_auto_violations,_em_fast_self_stress_violations
                    if p.auto_state.enabled:_em_fast_self_auto_violations+=1
                    if p.stress_test:_em_fast_self_stress_violations+=1
                    _fast_self_bytes+=len(packet)
                    perf_out_bytes+=len(packet)
                except (asyncio.TimeoutError,ConnectionClosed,OSError):
                    try:await p.ws.close(code=1011,reason='Fast self send timeout')
                    except Exception:pass
                    return
    except asyncio.CancelledError:return


def background_snapshot_due(p: Guest, step: int) -> bool:
    """Schedule each hidden client 1/2Hz across 10Hz broadcast slots.

    Background clients have an independent 0..9 phase, fixed at connection
    time. Thus 100 hidden clients at 1Hz make ~10 queued updates every 100ms,
    instead of all 100 on one tick each second. The 10Hz active path and
    30Hz authoritative game loop are unaffected.
    """
    phases = 10 // AUTO_BG_SNAP_HZ
    return (step // 3) % phases == p.background_phase % phases


def queue_latest_snapshot(p: Guest, world):
    q=p.snapshot_outbox
    if q.full():
        global _diag_overwritten
        _diag_overwritten+=1
        try:q.get_nowait()
        except asyncio.QueueEmpty:pass
    try:q.put_nowait(world)
    except asyncio.QueueFull:pass


async def game_loop():
    global server_step, _bg_snapshot_queued, _bg_snapshot_peak_batch
    next_tick=time.monotonic()
    while True:
        next_tick+=DT
        _prof_tick_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
        tick_now=time.monotonic()
        lag=min(3.0,max(0.0,tick_now-(next_tick-DT)))
        perf_loop_lags.append(lag)
        if lag>=.05:_cv_loop_spikes.append(lag*1000)
        server_step+=1
        profile_tick=server_step%30==0
        # One 30Hz tick; all currently occupied isolated map/channel worlds.
        # An empty world costs zero AI, zero physics and zero snapshots.
        for world_state in worlds.values():
            if not world_state.players:continue
            token=_world_context.set(world_state)
            try:
                _prof_world_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                _prof_substage=_prof_world_start
                stage_start=time.perf_counter_ns() if profile_tick else 0
                # Build AUTO query grid only if the map is dense AND some AUTO bot
                # is due. No repeated index construction per player or per frame.
                autos_due=(len(monsters)>=AUTO_QUERY_MIN_MOBS and any(
                    p.auto_state.enabled and tick_now>=p.auto_state.next_step for p in players.values()))
                auto_monsters=(AutoMonsterCandidates(monsters) if autos_due else monsters)
                if ENABLE_PERFORMANCE_PROFILER:
                    _profile_add('player.auto_setup',time.perf_counter_ns()-_prof_substage)
                _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                for p in list(players.values()):
                    if p.auto_state.enabled:
                        # Check queued human casts EVERY simulation tick, before AUTO
                        # makes its 10Hz decision. No double cast in one cooldown.
                        human_reserved = pending_auto_manual(p, tick_now)
                        # Keep authoritative physics at 30Hz; decisions at <=10Hz.
                        # Movement remains held between decisions, no browser AI.
                        if tick_now >= p.auto_state.next_step:
                            _prof_auto_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                            buttons,actions=farm_nav_for(p.room).choose(p,p.auto_state,tick_now,auto_monsters,allow_cast=not human_reserved)
                            if ENABLE_PERFORMANCE_PROFILER:_profile_add('player.auto_choose',time.perf_counter_ns()-_prof_auto_start)
                            p.buttons=buttons
                            # Guard is a manual held combat action, not movement input.
                            # It must expire on lost connections/background tabs.
                            if p.manual_guard and tick_now-p.manual_guard_at>.55:p.manual_guard=False
                            if p.manual_guard:p.buttons|=16
                            # Preserve 10Hz decisions and the original 100ms cadence.
                            # Advancing from the old deadline, rather than the current
                            # tick, avoids phase collapse after scheduling jitter. If the
                            # process was suspended/throttled, skip missed decisions.
                            p.auto_state.next_step=(tick_now+.1 if tick_now-p.auto_state.next_step>.1
                                                    else p.auto_state.next_step+.1)
                            for action in actions:perform_action(p,action)
                        if p.manual_guard and tick_now-p.manual_guard_at>.55:p.manual_guard=False
                        if p.manual_guard:p.buttons|=16
                        else:p.buttons&=~16
                        p.last_input=tick_now
                    _prof_move_start=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                    movement_tick(p,DT,tick_now)
                    if ENABLE_PERFORMANCE_PROFILER:_profile_add('player.movement',time.perf_counter_ns()-_prof_move_start)
                if profile_tick:
                    stage_end=time.perf_counter_ns()
                    _profile_samples['player'].append((stage_end-stage_start)/1e6)
                    stage_start=stage_end
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('player.phase_total',time.perf_counter_ns()-_prof_substage)
                _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                grid=index_players_by_x()
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('monster.player_grid',time.perf_counter_ns()-_prof_substage)
                _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                for m in monsters.values():update_mob(m,DT,grid)
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('monster.phase_total',time.perf_counter_ns()-_prof_substage)
                _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                if profile_tick:
                    stage_end=time.perf_counter_ns()
                    _profile_samples['monster'].append((stage_end-stage_start)/1e6)
                    stage_start=stage_end
                update_shots(DT)
                if world_state.room in BAMBOO_MONSTER_SLOTS: update_peach_shots(DT)
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('combat.projectiles',time.perf_counter_ns()-_prof_substage)
                _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                advance_loot()
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('loot.advance',time.perf_counter_ns()-_prof_substage)
                _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                # EC: capture only SERVER-CONFIRMED state, after mobs/knockback/loot.
                # Does not change server physics, inputs, world snapshot or AOI cadence.
                if ENABLE_FAST_SELF_30HZ:
                    for p in players.values():enqueue_fast_self(p)
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('self.enqueue_phase',time.perf_counter_ns()-_prof_substage)
                _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                if profile_tick:
                    stage_end=time.perf_counter_ns()
                    _profile_samples['projectile_loot'].append((stage_end-stage_start)/1e6)
                    stage_start=stage_end
                if server_step%3==(world_state.channel-1)%3:
                    # v8.0EK: world-level 10Hz spread over 30Hz ticks.
                    # v8.0DS: all Active viewers keep their 10Hz stream. Hidden viewers
                    # retain 1/2Hz each, but are spread across the ten 100ms broadcasts
                    # instead of all waking on the same once-per-second tick.
                    # NEVER slow 30Hz physics, 10Hz AUTO decisions or combat here.
                    recipients=[]
                    bg_queued=0
                    for p in players.values():
                        if p.snapshot_task is None or p.snapshot_task.done():
                            continue
                        if p.view_mode == 'background':
                            if not background_snapshot_due(p,server_step):
                                continue
                            bg_queued+=1
                        recipients.append(p)
                    if ENABLE_PERFORMANCE_PROFILER:_profile_add('snapshot.recipients',time.perf_counter_ns()-_prof_substage)
                    _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                    if recipients:
                        world=snapshot()
                        if ENABLE_PERFORMANCE_PROFILER:_profile_add('snapshot.build',time.perf_counter_ns()-_prof_substage)
                        _prof_substage=time.perf_counter_ns() if ENABLE_PERFORMANCE_PROFILER else 0
                        for p in recipients:queue_latest_snapshot(p,world)
                        if ENABLE_PERFORMANCE_PROFILER:_profile_add('snapshot.enqueue',time.perf_counter_ns()-_prof_substage)
                    _bg_snapshot_queued+=bg_queued
                    _bg_snapshot_peak_batch=max(_bg_snapshot_peak_batch,bg_queued)
                    # Events are visual effects; no replay of stale events after tab resumes.
                    events.clear()
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('snapshot.phase_total',time.perf_counter_ns()-_prof_substage)
                if profile_tick:
                    _profile_samples['world_snapshot'].append((time.perf_counter_ns()-stage_start)/1e6)
            finally:
                if ENABLE_PERFORMANCE_PROFILER:_profile_add('world.total',time.perf_counter_ns()-_prof_world_start,(world_state.channel,world_state.room))
                _world_context.reset(token)
        if ENABLE_PERFORMANCE_PROFILER:_profile_add('tick.total',time.perf_counter_ns()-_prof_tick_start)
        perf_ticks.append(time.monotonic()-tick_now)
        performance_rollup(time.monotonic())
        report_performance_to_render(time.monotonic())
        await asyncio.sleep(max(0,next_tick-time.monotonic()))
        if time.monotonic()-next_tick>.4:next_tick=time.monotonic()


def strict_message(raw):
    try: m = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError, RecursionError): return None
    if not isinstance(m, dict): return None
    return m


def check_rate(q, rate, window=1):
    now = time.monotonic()
    q.append(now)
    while q and q[0] < now - window: q.popleft()
    return len(q) <= rate


def stress_occupancy(room='forest'):
    # EI: a read-only view, no allocation or world wake. Count ALL occupants.
    return [{'id':ch,'players':len(worlds[(ch,room)].players)} for ch in CHANNEL_IDS]

def channel_status(room='forest'):
    return [{'id':ch,'players':len(worlds[(ch,room)].players),
             'cap':MAP_HARD_CAPS[room]} for ch in PUBLIC_CHANNEL_IDS]

async def switch_channel(p, target):
    """Same character object, no duplication/copy of inventory, stats, levels.
    Atomic admission and ownership change in the single event loop.
    A future distributed version must replace this with a fenced handoff.
    """
    now=time.monotonic()
    if target not in PUBLIC_CHANNEL_IDS:
        return {'t':'channel_ack','ok':False,'reason':'invalid_channel','channel':p.channel,'channels':channel_status(p.room)}
    if target==p.channel:
        return {'t':'channel_ack','ok':True,'channel':p.channel,'channels':channel_status(p.room),'same':True}
    new_world=worlds[(target,p.room)]
    if len(new_world.players)>=MAP_HARD_CAPS[p.room]:
        return {'t':'channel_ack','ok':False,'reason':'map_full','channel':p.channel,'channels':channel_status(p.room)}
    if now-p.channel_switch_at<CHANNEL_SWITCH_COOLDOWN:
        return {'t':'channel_ack','ok':False,'reason':'cooldown','channel':p.channel,'channels':channel_status(p.room)}
    if p.auto_state.enabled:
        return {'t':'channel_ack','ok':False,'reason':'auto_active','channel':p.channel,'channels':channel_status(p.room)}
    if now-p.last_attack_at<8 or now-p.last_damage_at<8:
        return {'t':'channel_ack','ok':False,'reason':'in_combat','channel':p.channel,'channels':channel_status(p.room)}
    if p.dead>0 or p.hp<=0 or p.stun>0 or p.down>0 or p.kb_time>0:
        return {'t':'channel_ack','ok':False,'reason':'busy','channel':p.channel,'channels':channel_status(p.room)}
    # Prevent switching mid-cast, midair, or while on a rope.
    if not p.ground or p.climb or p.action in ('attack','aoe','break','dash'):
        return {'t':'channel_ack','ok':False,'reason':'must_stand_idle','channel':p.channel,'channels':channel_status(p.room)}
    old=p.world_ref
    # Atomic slot claim before ANY await: two simultaneous transfers can never
    # both pass the 10-player hard cap. Current actor is moved, never copied.
    old.shots[:]=[shot for shot in old.shots if shot.owner!=p.id]
    record_world_event(old, {'t':'leave','x':round(p.x,1),'y':round(p.y,1),'victim':p.id})
    old.players.pop(p.id,None)
    # Last-player departure releases runtime arrays immediately; preserve only
    # bounded sleeping capsule and respawn deadlines. No await within transfer.
    hibernate_world(old)
    new_world.players[p.id]=p
    p.event_cursor=new_world.event_seq  # never replay a prior channel's events
    p.channel=target;p.world_ref=new_world
    _world_context.set(new_world)
    wake_world(new_world)
    # Cancel obsolete delta writer and start a new baseline only AFTER ACK.
    prior_snapshot=p.snapshot_task
    if prior_snapshot:prior_snapshot.cancel()
    p.snapshot_task=None
    # No new player object; inventory/EXP and account state cannot be copied.
    _world_context.set(new_world)
    p.buttons=0;p.vx=0;p.vy=0;p.x=175+(len(new_world.players)-1)%8*35;p.y=550
    p.ground=True;p.climb=None;p.guard=False
    p.auto_state.enabled=False;p.auto_state.stay_alert=False
    p.auto_state.anchor=None;p.auto_state.goal=None
    p.manual_target_id=None;p.manual_auto_skill=None;p.manual_guard=False
    p.channel_switch_at=now
    record_world_event(new_world, {'t':'join','x':round(p.x,1),'y':round(p.y,1),'victim':p.id})
    p.fast_self_epoch+=1;p.fast_self_last=None
    while not p.fast_self_outbox.empty():
        try:p.fast_self_outbox.get_nowait()
        except asyncio.QueueEmpty:break
    while not p.snapshot_outbox.empty():
        try:p.snapshot_outbox.get_nowait()
        except asyncio.QueueEmpty:break
    # Server-first is mandatory on transfer (old client movement proposal epochs invalid).
    movement_change_mode(p,'server')
    return {'t':'channel_ack','ok':True,'channel':target,'channels':channel_status(p.room),
            'x':p.x,'y':p.y,'fastSelfEpoch':p.fast_self_epoch,'moveEpoch':p.move_epoch}

async def switch_map(p, target, via='selector'):
    # Server owns both worlds; no client positions/physics accepted.
    now=time.monotonic()
    if target not in PUBLIC_MAP_IDS or p.room not in PUBLIC_MAP_IDS:
        return {'t':'map_ack','ok':False,'reason':'invalid_map','map':p.room}
    if target==p.room:
        return {'t':'map_ack','ok':True,'same':True,**map_payload(p.room)}
    source_index=PUBLIC_MAP_IDS.index(p.room)
    target_index=PUBLIC_MAP_IDS.index(target)
    branch_portal = via=='portal' and {p.room,target}=={'forest_fork_11','granite_ascent_1'}
    wall_portal = GRANITE_WALL_PORTALS.get((p.room,target)) if via=='portal' else None
    summit_ladder = GRANITE_SUMMIT_LADDER_LINKS.get((p.room,target)) if via=='portal' else None
    expansion_link=next((l for l in WORLD_V56['links'] if l['from']==p.room and l['to']==target),None) if via=='portal' else None
    if via=='portal':
        if expansion_link is not None:
            if not expansion_portal_at(expansion_link,p):return {'t':'map_ack','ok':False,'reason':'portal_too_far_or_no_up','map':p.room}
        elif p.room in EXPANSION_MAPS or target in EXPANSION_MAPS:
            return {'t':'map_ack','ok':False,'reason':'invalid_portal','map':p.room}
        elif summit_ladder is not None:
            direction,cx,top,bottom,tolerance,_,_=summit_ladder
            end=top if direction<0 else bottom
            on_ladder=(p.climb==(cx,top,bottom) and abs(p.x-cx)<=12
                       and (end-8<=p.y<=end+tolerance if direction<0 else end-tolerance<=p.y<=end+8))
            landed=(p.climb is None and p.ground and abs(p.y-end)<=8
                    and abs(p.x-cx)<=75)
            intent=bool(p.buttons & (4 if direction<0 else 8))
            if not intent or not (on_ladder or landed):
                return {'t':'map_ack','ok':False,'reason':'portal_wrong_ladder','map':p.room}
        elif p.room in GRANITE_WALL_MAPS or target in GRANITE_WALL_MAPS:
            if wall_portal is None:
                return {'t':'map_ack','ok':False,'reason':'invalid_portal','map':p.room}
            side,exit_y,margin,_,_=wall_portal
            if not p.ground or p.climb is not None or abs(p.y-exit_y)>35:
                return {'t':'map_ack','ok':False,'reason':'portal_wrong_floor','map':p.room}
            if (side=='right' and p.x<city_world_width(p.room)-margin) or (side=='left' and p.x>margin):
                return {'t':'map_ack','ok':False,'reason':'portal_too_far','map':p.room}
        elif p.room in MOUNTAIN_MAPS or target in MOUNTAIN_MAPS:
            if not branch_portal:
                return {'t':'map_ack','ok':False,'reason':'invalid_portal','map':p.room}
            if not p.ground or p.climb is not None:
                return {'t':'map_ack','ok':False,'reason':'portal_wrong_floor','map':p.room}
            if p.room=='forest_fork_11':
                if abs(p.y+700)>35:
                    return {'t':'map_ack','ok':False,'reason':'portal_wrong_floor','map':p.room}
                if p.x<city_world_width(p.room)-125:
                    return {'t':'map_ack','ok':False,'reason':'portal_too_far','map':p.room}
            else:
                if abs(p.y-550)>35:
                    return {'t':'map_ack','ok':False,'reason':'portal_wrong_floor','map':p.room}
                if p.x>125:
                    return {'t':'map_ack','ok':False,'reason':'portal_too_far','map':p.room}
        else:
            if (target in GRANITE_FOREST_MAPS or p.room in GRANITE_FOREST_MAPS) and (not p.ground or p.climb is not None or abs(p.y-550)>40):
                return {'t':'map_ack','ok':False,'reason':'portal_wrong_floor','map':p.room}
            if abs(target_index-source_index)!=1:
                return {'t':'map_ack','ok':False,'reason':'invalid_portal','map':p.room}
            if target_index>source_index and p.x<city_world_width(p.room)-125:
                return {'t':'map_ack','ok':False,'reason':'portal_too_far','map':p.room}
            if target_index<source_index and p.x>125:
                return {'t':'map_ack','ok':False,'reason':'portal_too_far','map':p.room}
    elif via!='selector':
        return {'t':'map_ack','ok':False,'reason':'invalid_via','map':p.room}
    target_world=worlds[(p.channel,target)]
    if len(target_world.players)>=MAP_HARD_CAPS[target]:
        return {'t':'map_ack','ok':False,'reason':'map_full','map':p.room}
    if now-p.map_switch_at<1.4:
        return {'t':'map_ack','ok':False,'reason':'cooldown','map':p.room}
    if p.auto_state.enabled:
        return {'t':'map_ack','ok':False,'reason':'auto_active','map':p.room}
    # Map selector is an escape/travel mechanism: allow it while climbing a rope,
    # on a ladder, in midair, during an attack/dash, or immediately after damage.
    # Only genuinely incapacitated or dead characters are rejected.
    if p.dead>0 or p.hp<=0 or p.stun>0 or p.down>0:
        return {'t':'map_ack','ok':False,'reason':'busy','map':p.room}
    for nav in SWAMP_RECOVERY.values():nav.reset(p.id)
    origin=p.world_ref
    origin.shots[:]=[shot for shot in origin.shots if shot.owner!=p.id]
    record_world_event(origin, {'t':'leave','x':round(p.x,1),'y':round(p.y,1),'victim':p.id})
    origin.players.pop(p.id,None)
    hibernate_world(origin)
    target_world.players[p.id]=p
    p.room=target;p.world_ref=target_world
    p.event_cursor=target_world.event_seq
    _world_context.set(target_world)
    wake_world(target_world)
    old_writer=p.snapshot_task
    if old_writer:old_writer.cancel()
    p.snapshot_task=None
    p.buttons=0;p.vx=0;p.vy=0;p.ground=True;p.climb=None;p.guard=False
    p.action='idle';p.action_at=0;p.action_duration=0  # stop mid-cast/air/climb animation on arrival
    # Right-hand portal arrival emerges near left of next map; vice versa.
    p.x=(city_world_width(target)-175 if via=='portal' and target_index<source_index else 175)
    p.y=550
    if target in EXPANSION_MAPS:p.x,p.y=EXPANSION_MAPS[target]['spawn']
    if expansion_link:p.x,p.y=expansion_link['spawn']
    if branch_portal:
        p.x,p.y=((175,550) if target=='granite_ascent_1' else (2225,-700))
    if wall_portal:
        p.x,p.y=wall_portal[3:]
    if summit_ladder:
        p.x,p.y=summit_ladder[5:]
    p.auto_state.enabled=False;p.auto_state.stay_alert=False
    p.auto_state.anchor=None;p.auto_state.goal=None
    p.manual_target_id=None;p.manual_auto_skill=None;p.manual_guard=False
    p.map_switch_at=now
    p.fast_self_epoch+=1;p.fast_self_last=None
    while not p.fast_self_outbox.empty():
        try:p.fast_self_outbox.get_nowait()
        except asyncio.QueueEmpty:break
    while not p.snapshot_outbox.empty():
        try:p.snapshot_outbox.get_nowait()
        except asyncio.QueueEmpty:break
    movement_change_mode(p,'server')
    record_world_event(target_world, {'t':'join','x':round(p.x,1),'y':round(p.y,1),'victim':p.id})
    return {'t':'map_ack','ok':True,**map_payload(target), 'x':p.x,'y':p.y,
            'fastSelfEpoch':p.fast_self_epoch,'moveEpoch':p.move_epoch,
            'channels':channel_status(p.room)}

async def handle_connection(ws):
    guest_id = None
    admitted_world = None
    global snapshot_join_sequence, _pending_joins, _em_auto_canceled
    if _pending_joins >= MAX_PENDING_JOINS:
        await ws.close(code=1013,reason='Server admission busy');return
    _pending_joins += 1
    pending_held = True
    try:
        if ORIGINS and (ws.request.headers.get('Origin') not in ORIGINS):
            await ws.close(code=1008, reason='Origin not allowed');return
        raw = await asyncio.wait_for(ws.recv(), timeout=8)
        _pending_joins -= 1;pending_held = False
        hello = strict_message(raw)
        valid_joins=({'t','avatar'},{'t','avatar','protocol'},{'t','avatar','room'},
                     {'t','avatar','protocol','room'}, {'t','avatar','protocol','room','channel'},
                     {'t','avatar','channel'}, {'t','avatar','protocol','channel'}, {'t','avatar','room','channel'})
        # Stress mode is marked explicitly, opt-in by the operator and bounded
        # by hard caps. This is NOT authentication; do not enable on public
        # servers except for a short supervised load test.
        stress_shape = bool(hello and 'stressTest' in hello)
        if stress_shape:
            valid_joins += tuple(set(fields)|{'stressTest'} for fields in valid_joins)
            valid_joins += tuple(set(fields)|{'stressTest','stressCap'} for fields in valid_joins)
        if not hello or set(hello.keys()) not in valid_joins or hello.get('t') != 'join' or not valid_avatar(hello.get('avatar')) or hello.get('protocol','legacy') not in ('legacy','aoi-delta-v80by','aoi-binary-v80du') or hello.get('room','forest') not in ('forest','movement_lab') or type(hello.get('channel',1)) is not int or hello.get('channel',1) not in CHANNEL_IDS:
            print('JIANGHU_JOIN_REJECT invalid_schema fields=', sorted(hello.keys()) if isinstance(hello,dict) else 'not-dict', 'channel=',hello.get('channel') if isinstance(hello,dict) else None, flush=True)
            await ws.close(code=1008, reason='Invalid guest join');return
        stress_test = False
        if stress_shape and 'stressCap' in hello and (type(hello['stressCap']) is not int or not 1<=hello['stressCap']<=200):
            await ws.close(code=1008,reason='Invalid stress target');return
        if stress_shape:
            if hello.get('stressTest') is not True or not ENABLE_CHANNEL_STRESS:
                print('JIANGHU_STRESS_JOIN_REJECT disabled_or_bad_flag ch=',hello.get('channel'),flush=True)
                await ws.close(code=1008,reason='Stress mode disabled');return
            stress_test = True
        room=hello.get('room','forest')
        channel=hello.get('channel',1)
        if not stress_test and channel not in PUBLIC_CHANNEL_IDS:
            await ws.close(code=1008,reason='Private stress channel');return
        world_ref=worlds[(channel,room)]
        # MAX_GUESTS remains the non-negotiable process-level safety ceiling.
        if len(connected_players) >= MAX_GUESTS:
            await ws.send(json.dumps({'t':'error','message':'เซิร์ฟเวอร์เต็ม'}));await ws.close(code=1013);return
        if stress_test:
            stress_total=sum(p.stress_test for p in connected_players.values())
            stress_here=sum(p.stress_test for p in world_ref.players.values())
            if stress_total>=CHANNEL_STRESS_TOTAL or stress_here>=CHANNEL_STRESS_PER_CHANNEL:
                print('JIANGHU_STRESS_JOIN_REJECT quota ch=',channel,'total=',stress_total,'here=',stress_here,flush=True)
                await ws.send(json.dumps({'t':'error','message':'Stress quota full'}));await ws.close(code=1013);return
            # EI: authoritative per-channel TOTAL target includes humans and other testers.
            # Concurrent guests may not pass even if they read an earlier occupancy.
            if 'stressCap' in hello and len(world_ref.players)>=hello['stressCap']:
                await ws.send(json.dumps({'t':'error','message':'Stress channel target reached'}))
                await ws.close(code=1013,reason='Stress channel target reached');return
        else:
            normal_total=sum(not p.stress_test for p in connected_players.values())
            # The public hard caps remain in force; stress guests take world slots too.
            if normal_total>=CHANNEL_TOTAL_GUEST_CAP:
                await ws.send(json.dumps({'t':'error','message':'เซิร์ฟเวอร์เต็ม'}));await ws.close(code=1013);return
            if len(world_ref.players)>=MAP_HARD_CAPS[room]:
                await ws.send(json.dumps({'t':'error','message':f'CH{channel} แมพนี้เต็ม {MAP_HARD_CAPS[room]}/{MAP_HARD_CAPS[room]}'}))
                await ws.close(code=1013,reason='Map full');return
        admitted_world = world_ref
        _world_context.set(world_ref)
        wake_world(world_ref)
        guest_id = 'g-' + secrets.token_hex(8)
        name = 'Guest-' + guest_id[-4:].upper()
        # All legal spawn points are server-defined, never supplied by client.
        spawn_x = 175 + (len(players) % 8) * 35
        guest_level=1  # same Lv1 start as Offline; ephemeral Guest, no DB character save
        guest_hp=prog.base_hp_for_level(guest_level,hp_reference)
        p = Guest(id=guest_id, x=spawn_x, y=550, hp=guest_hp, max_hp=guest_hp, room=hello.get('room','forest'),
                  avatar=hello['avatar'], ws=ws, level=guest_level, channel=channel, world_ref=world_ref, stress_test=stress_test)
        prog.apply_derived_resources(p,hp_reference,full=True)
        p.protocol_delta=(hello.get('protocol') in ('aoi-delta-v80by','aoi-binary-v80du') or p.room=='movement_lab')
        p.protocol_binary=hello.get('protocol')=='aoi-binary-v80du'
        # Evenly distribute connection slots; no random clumping for first 10 guests.
        p.snapshot_slot=snapshot_join_sequence%STAGGER_SLOTS
        # Background phase is NOT the writer's 100ms send phase. This diagonal
        # layout distributes both 1Hz updates AND each 100ms batch of writers.
        # With 100 sequential joins: 10 Background clients per broadcast,
        # spread across all 10 existing writer slots rather than one burst.
        p.background_phase=((snapshot_join_sequence//10)+(snapshot_join_sequence%10))%10
        snapshot_join_sequence+=1
        p.event_cursor = world_ref.event_seq  # do not replay pre-join events
        players[guest_id] = p
        connected_players[guest_id] = p
        features=['beast-v80bq','progression-v80bs','monster-hpdef-v80bu','auto','auto-stay-v80dh','auto-manual-skills-v80dh','aoi-delta-v80by','input-ack-v80by','cooperative-pve-only-v80ca','responsive-walk-v80ca','jump-rope-visual-v80cb','cast-fx-reliable-v80cb','wire-shot-ids-v80cd','map-climb-verified-v80cd','rtt-probe-v80ce','ladder-ceiling-v80ce','client-perf-v80cl','view-mode-v80dp','view-mode-all-v80dr','bg-stagger-v80ds','aoi-binary-v80du']
        if ENABLE_GUEST_SANDBOX:features.append('sandbox-loadouts-v80bt')
        features.append('movement-lab-room-v80cz')
        if ENABLE_CLIENT_MOVEMENT_AB:features.append('client-movement-ab-v80dx')
        if ENABLE_FAST_SELF_30HZ:features.append('server-fast-self-30hz-v80ec')
        features.append('fixed-channels-v80ee')
        features.append('lazy-map-hibernation-v80ef')
        features.append('bamboo-map-worlds-v1')
        features.append('suburb-gate-7worlds-v1')
        # City V8 uses flat roads; old two-tier handshake retired
        features.append(WORLD_V56['feature'])
        features.extend(('city-master-v1','city-single-floor-v8-v9','peach-exit-map10-v3','forest-fork-map11-v21-clean-ropes','forest-granite-chain-v3-map3-four-long-decks','granite-ascent-v64-single-map','granite-wall-chain-v64-single-ascent-link'))
        if stress_test: features.append('open-channel-stress-v80eh')
        if ENABLE_CHANNEL_STRESS: features.append('stress-occupancy-v80ei')
        features.append('event-journal-v80ek')
        features.append('auto-ack-v80em')
        if ENABLE_EL_SNAPSHOT_SCHED: features.append('writer-sample-phase-v80el')
        await ws.send(json.dumps({'t': 'welcome', 'id': guest_id, 'name': name, 'tickRate': 30, 'snapshotRate': 10, 'guest': True, 'features':features,'mapVersion':'beast-v80bq',**map_payload('forest'),'room':p.room,'channel':p.channel,'channelCaps':{'forest':10,'city':70},'channels':channel_status(p.room),'stressOccupancy':stress_occupancy(p.room) if ENABLE_CHANNEL_STRESS else None,'monsterPresetLevel':MONSTER_PRESET_LEVEL,'expSource':prog.EXP_SOURCE}))
        p.snapshot_task=asyncio.create_task(snapshot_writer(p),name='snapshot-'+guest_id)
        if ENABLE_FAST_SELF_30HZ:
            p.fast_self_task=asyncio.create_task(fast_self_writer(p),name='fastself-'+guest_id)
        event('join', p.x, p.y, victim=p.id)
        async for raw in ws:
            m = strict_message(raw)
            if not m:
                await ws.close(code=1008,reason='Invalid message');break
            # RTT probe is display-only: bounded, rate-limited, never used by
            # movement, damage, rewind or anti-cheat decisions.
            if m.get('t')=='ping':
                nonce=m.get('nonce')
                if set(m)!={'t','nonce'} or type(nonce) is not int or not 0<=nonce<2**31:
                    await ws.close(code=1008,reason='Invalid ping');break
                if not check_rate(p.packet_times,35):
                    await ws.close(code=1008,reason='Ping rate limit');break
                await ws.send(json.dumps({'t':'pong','nonce':nonce},separators=(',',':')))
                continue
            # v8.0CL diagnostic only, never used for movement/combat decisions.
            if m.get('t')=='client_perf':
                names={'t','fps','pingMs','gapP95Ms','gapMaxMs','frameMs'}
                if set(m)==names and time.monotonic()-p.client_perf_at>=8:
                    fields=('fps','gapP95Ms','gapMaxMs','frameMs')
                    valid=all(type(m.get(k)) in (int,float) and math.isfinite(m[k]) and 0<=m[k]<=10000 for k in fields)
                    ping=m.get('pingMs')
                    valid=valid and (ping is None or (type(ping) in (int,float) and math.isfinite(ping) and 0<=ping<=10000))
                    if valid:
                        p.client_perf={k:round(float(m[k]),2) for k in fields}
                        p.client_perf['pingMs']=None if ping is None else round(float(ping),2)
                        p.client_perf_at=time.monotonic()
                continue
            if m.get('t')=='stress_status':
                if set(m)!={'t'}:
                    await ws.close(code=1008,reason='Invalid stress status');break
                if not ENABLE_CHANNEL_STRESS:
                    await ws.send(json.dumps({'t':'stress_status','enabled':False,'reason':'disabled'}));continue
                now=time.monotonic()
                if now-p.stress_status_at<.8:continue
                p.stress_status_at=now
                await ws.send(json.dumps({'t':'stress_status','enabled':True,
                   'channels':stress_occupancy(p.room),
                   'serverGuests':len(connected_players),
                   'maxGuests':MAX_GUESTS,'stressMax':CHANNEL_STRESS_TOTAL},separators=(',',':')))
                continue
            if m.get('t')=='map_change':
                if set(m)!={'t','map','via'} or m.get('map') not in PUBLIC_MAP_IDS or m.get('via') not in ('portal','selector'):
                    await ws.close(code=1008,reason='Invalid map change');break
                # Dedicated map-request limiter, independent of channel list/change.
                # 30 requests / 30 seconds is abuse protection; successful map travel
                # also retains its existing 1.4 s server-side cooldown.
                if not check_rate(p.map_request_times,30,30):
                    await ws.send(json.dumps({'t':'map_ack','ok':False,'reason':'rate_limited','map':p.room}))
                    continue
                prior_snapshot_task=p.snapshot_task
                answer=await switch_map(p,m['map'],m['via'])
                if answer.get('ok') and not answer.get('same'):
                    if prior_snapshot_task:
                        try:await prior_snapshot_task
                        except asyncio.CancelledError:pass
                async with p.ws_send_lock:
                    await ws.send(json.dumps(answer,separators=(',',':')))
                if answer.get('ok') and not answer.get('same'):
                    p.snapshot_task=asyncio.create_task(snapshot_writer(p),name='snapshot-'+p.id)
                continue
            if m.get('t')=='channel_list':
                if set(m)!={'t'}:
                    await ws.close(code=1008,reason='Invalid channel query');break
                if not check_rate(p.channel_switch_times,12,30):
                    # Repeated UI refresh is ignored, never disconnect a player.
                    continue
                await ws.send(json.dumps({'t':'channel_list','channel':p.channel,'channels':channel_status(p.room)},separators=(',',':')))
                continue
            if m.get('t')=='channel_change':
                if set(m)!={'t','channel'} or type(m.get('channel')) is not int or m['channel'] not in CHANNEL_IDS:
                    await ws.close(code=1008,reason='Invalid channel change');break
                if not check_rate(p.channel_switch_times,12,30):
                    await ws.send(json.dumps({'t':'channel_ack','ok':False,'reason':'rate_limited',
                        'channel':p.channel,'channels':channel_status(p.room)},separators=(',',':')))
                    continue
                prior_snapshot_task=p.snapshot_task
                answer=await switch_channel(p,m['channel'])
                if answer.get('ok') and not answer.get('same'):
                    # Ensure prior-channel writer is dead before committing ACK.
                    if prior_snapshot_task:
                        try:await prior_snapshot_task
                        except asyncio.CancelledError:pass
                async with p.ws_send_lock:
                    await ws.send(json.dumps(answer,separators=(',',':')))
                if answer.get('ok') and not answer.get('same'):
                    p.snapshot_task=asyncio.create_task(snapshot_writer(p),name='snapshot-'+p.id)
                continue
            # Only earned points are spendable; never accept client totals/ranks.
            if m.get('t') in ('stat_add','skill_up'):
                t=m['t']
                if (t=='stat_add' and set(m)!={'t','stat','amount'}) or (t=='skill_up' and set(m)!={'t','skill','amount'}):
                    await ws.close(code=1008,reason='Invalid progression command');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='Action rate limit');break
                ok=prog.allocate_stat(p,m.get('stat'),m.get('amount'),hp_reference) if t=='stat_add' else prog.upgrade_skill(p,m.get('skill'),m.get('amount'))
                await ws.send(json.dumps({'t':'progression_ack','ok':ok,'kind':t}))
                continue
            if m.get('t') in ('sandbox_level','gear_preset','gear_affix','gear_enhance','gear_clear','qi_equip','qi_unequip','qi_rank'):
                if not ENABLE_GUEST_SANDBOX:
                    await ws.close(code=1008,reason='QA sandbox disabled');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='Sandbox action rate limit');break
                ok=loadouts.apply_command(p,m)
                if ok:
                    prog.apply_derived_resources(p,hp_reference,full=(m['t']=='gear_preset'))
                    if not loadouts.active_qi(p,1):p.qi_heal_kills=0
                    if not loadouts.active_qi(p,0):p.qi_shield=0
                await ws.send(json.dumps({'t':'sandbox_ack','ok':ok,'kind':m['t']}))
                continue
            if m.get('t')=='auto':
                if set(m) not in ({'t','enabled'},{'t','enabled','seq'}) or type(m.get('enabled')) is not bool or ('seq' in m and (type(m['seq']) is not int or m['seq']<1 or m['seq']>2**53)):
                    await ws.close(code=1008,reason='Invalid AUTO toggle');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='AUTO toggle rate limit');break
                # Reliable WS order + sequence number make duplicate retries idempotent.
                if 'seq' in m and m['seq']<=p.auto_command_seq:
                    async with p.ws_send_lock:
                        await ws.send(json.dumps({'t':'auto_ack','seq':m['seq'],
                            'enabled':p.auto_state.enabled,'revision':p.auto_revision,'ok':True},separators=(',',':')))
                    continue
                if 'seq' in m:p.auto_command_seq=m['seq']
                previous_auto=p.auto_state.enabled
                p.auto_state.enabled=m['enabled'] if p.room in PUBLIC_MAP_IDS else False
                if previous_auto!=p.auto_state.enabled:p.auto_revision+=1
                if not p.auto_state.enabled:
                    for nav in SWAMP_RECOVERY.values():nav.reset(p.id)
                if previous_auto!=p.auto_state.enabled:
                    p.fast_self_last=None
                    while not p.fast_self_outbox.empty():
                        try:p.fast_self_outbox.get_nowait()
                        except asyncio.QueueEmpty:break
                if p.auto_state.enabled and p.movement_mode=='client':
                    await ws.send(json.dumps(movement_change_mode(p,'server'),separators=(',',':')))
                p.buttons=0
                p.manual_guard=False
                p.auto_state.stay_alert=False;p.auto_state.anchor=None;p.auto_state.anchor_evade_side=0
                p.manual_auto_skill=None;p.manual_auto_until=0
                if 'seq' in m:
                    global _em_auto_ack_sent
                    async with p.ws_send_lock:
                        await ws.send(json.dumps({'t':'auto_ack','seq':m['seq'],
                            'enabled':p.auto_state.enabled,'revision':p.auto_revision,
                            'ok':p.room in PUBLIC_MAP_IDS or not m['enabled']},separators=(',',':')))
                    _em_auto_ack_sent+=1
                if p.auto_state.enabled:
                    # Fresh independently randomized destination at the next game tick.
                    p.auto_state.goal=None;p.auto_state.goal_due=0
                    # Spread simultaneously enabled AUTO guests across the three
                    # 30Hz simulation ticks per 100ms decision period. Each
                    # guest still decides every 100ms; this only shifts phase.
                    p.auto_state.next_step=time.monotonic()+(p.snapshot_slot%3)*DT
                continue
            if m.get('t')=='view_mode':
                # Do not trust background declarations for authority or player state.
                # Visibility controls outbound visuals independently of AUTO state.
                if set(m)!={'t','mode'} or m.get('mode') not in ('active','background'):
                    await ws.close(code=1008,reason='Invalid view mode');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='View mode rate limit');break
                p.view_mode=m['mode']
                continue
            if m.get('t')=='auto_stay':
                if set(m)!={'t','enabled'} or type(m.get('enabled')) is not bool:
                    await ws.close(code=1008,reason='Invalid Stay Alert toggle');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='Stay Alert toggle rate limit');break
                requested=m['enabled']
                platform=farm_nav_for(p.room).platform_at(p) if requested else -1
                valid=(not requested or (p.room in PUBLIC_MAP_IDS and p.auto_state.enabled and
                                        platform>=0 and p.dead<=0 and p.hp>0 and p.down<=0))
                if valid:
                    p.auto_state.stay_alert=requested
                    p.auto_state.anchor=({'platform':platform,'x':float(p.x),'y':float(p.y)} if requested else None)
                    p.auto_state.goal=dict(p.auto_state.anchor) if requested else None
                    p.auto_state.goal_due=0;p.auto_state.leg=None
                    p.auto_state.combat_target_id=None;p.auto_state.combat_lock_until=0;p.auto_state.anchor_evade_side=0
                    p.auto_state.next_step=0.0  # React on next simulation tick.
                await ws.send(json.dumps({'t':'auto_stay_ack','ok':valid,'enabled':p.auto_state.stay_alert}))
                continue
            if m.get('t')=='self_stream_mode':
                if set(m)!={'t','mode'} or m.get('mode') not in ('fast','classic'):
                    await ws.close(code=1008,reason='Invalid self stream mode');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='Self stream mode rate');break
                requested=m['mode']
                ok=(requested=='classic' or (ENABLE_FAST_SELF_30HZ and p.movement_mode=='server'))
                if ok:
                    p.fast_self_mode=(requested=='fast')
                    p.fast_self_epoch+=1
                    p.fast_self_last=None
                    while not p.fast_self_outbox.empty():
                        try:p.fast_self_outbox.get_nowait()
                        except asyncio.QueueEmpty:break
                await ws.send(json.dumps({'t':'self_stream_ack','ok':ok,
                    'mode':'fast' if p.fast_self_mode else 'classic',
                    'epoch':p.fast_self_epoch},separators=(',',':')))
                continue
            if m.get('t')=='movement_mode':
                if set(m)!={'t','mode'} or m.get('mode') not in ('client','server'):
                    await ws.close(code=1008,reason='Invalid movement mode');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='Movement toggle rate');break
                requested=m['mode']
                if requested=='client' and (not ENABLE_CLIENT_MOVEMENT_AB or p.auto_state.enabled or p.room in ('city_proto_1','city_inner_1')):
                    await ws.send(json.dumps({'t':'movement_mode_ack','mode':p.movement_mode,'ok':False,'reason':'unavailable'}))
                else:
                    await ws.send(json.dumps({**movement_change_mode(p,requested),'ok':True},separators=(',',':')))
                continue
            if m.get('t')=='movement_sync':
                # EA: reliable control-channel response when a client is stuck
                # waiting for its forced knockback/stun flag to clear. This is
                # NOT a position proposal and never trusts client coordinates.
                if set(m)!={'t','epoch'} or type(m.get('epoch')) is not int:
                    await ws.close(code=1008,reason='Invalid movement sync');break
                if not check_rate(p.movement_sync_times,6):
                    await ws.close(code=1008,reason='Movement sync rate');break
                if m['epoch']!=p.move_epoch or p.movement_mode!='client':continue
                forced=bool(p.kb_time>0 or p.stun>0 or p.down>0 or p.dead>0 or p.hp<=0)
                if not forced and p.move_recovery_armed:
                    # Safe exactly-once resync AFTER a genuine forced movement.
                    # The accepted position is already server-owned; restart
                    # shadow from it to avoid rejecting the first valid landing.
                    p.move_shadow=movement_capture(p)
                    p.move_last_at=time.monotonic()
                    p.move_budget_x=24.0
                    p.move_recovery_armed=False
                await ws.send(json.dumps({'t':'movement_state','epoch':p.move_epoch,
                    'forced':forced,'x':round(p.x,3),'y':round(p.y,3),
                    'vx':round(p.vx,3),'vy':round(p.vy,3),'ground':p.ground,
                    'climb':bool(p.climb),'face':p.face},separators=(',',':')))
                continue
            if m.get('t')=='client_move':
                names={'t','epoch','seq','x','y','vx','vy','ground','climb'}
                valid=(ENABLE_CLIENT_MOVEMENT_AB and set(m)==names and
                       type(m.get('epoch')) is int and type(m.get('seq')) is int and 0<=m['seq']<2**53 and
                       type(m.get('ground')) is bool and type(m.get('climb')) is bool and
                       all(type(m.get(k)) in (int,float) and math.isfinite(m[k]) for k in ('x','y','vx','vy')))
                if not valid:
                    await ws.close(code=1008,reason='Invalid movement report');break
                if not check_rate(p.movement_packet_times,30):
                    await ws.close(code=1008,reason='Movement packet rate');break
                if m['epoch']!=p.move_epoch:continue
                reason=movement_validate(p,m,time.monotonic())
                if reason:
                    p.move_rejects+=1
                    at=time.monotonic()
                    if at-p.move_last_correction>=.08:
                        p.move_last_correction=at
                        await ws.send(json.dumps({'t':'movement_correction','epoch':p.move_epoch,'reason':reason,
                            'x':round(p.x,3),'y':round(p.y,3),'vx':round(p.vx,3),'vy':round(p.vy,3),
                            'ground':p.ground,'climb':bool(p.climb),'face':p.face,'rejected':p.move_rejects},separators=(',',':')))
                continue
            if m.get('t')!='input' or set(m)!={'t','seq','buttons','pressed'}:
                await ws.close(code=1008, reason='Invalid input payload');break
            if not check_rate(p.packet_times, 35):
                await ws.close(code=1008, reason='Packet rate limit');break
            seq, buttons, pressed = m.get('seq'), m.get('buttons'), m.get('pressed')
            if type(seq) is not int or seq <= p.last_seq or seq < 0 or seq > 2**53 or type(buttons) is not int or buttons < 0 or buttons & ~ALLOWED_BUTTONS:
                await ws.close(code=1008, reason='Invalid buttons/sequence');break
            if not isinstance(pressed, list) or len(pressed) > 4 or any(type(a) is not str or a not in ACTION_NAMES for a in pressed) or len(set(pressed)) != len(pressed):
                await ws.close(code=1008, reason='Invalid action');break
            if pressed and not check_rate(p.action_times, 12):
                await ws.close(code=1008, reason='Action rate limit');break
            global perf_in_count
            perf_in_count += 1
            p.last_seq = seq
            # v8.0DH: only explicit manual locomotion cancels AUTO. A skill
            # press (and guard hold) is additive to the server-owned AI.
            # Client input NEVER overrides the AI's movement or goal.
            if p.auto_state.enabled and (buttons & (1|2|4|8)):
                p.auto_state.enabled=False
                for nav in SWAMP_RECOVERY.values():nav.reset(p.id)
                p.auto_revision+=1
                _em_auto_canceled+=1
                async with p.ws_send_lock:
                    await ws.send(json.dumps({'t':'auto_ack','seq':None,'enabled':False,
                        'revision':p.auto_revision,'ok':True,'reason':'manual_movement'},separators=(',',':')))
                p.fast_self_last=None  # resume fast self on first manual movement
                p.auto_state.stay_alert=False;p.auto_state.anchor=None;p.auto_state.anchor_evade_side=0
                p.manual_auto_skill=None;p.manual_auto_until=0
                p.manual_guard=False
            if p.auto_state.enabled:
                p.manual_guard=bool(buttons & 16)
                p.manual_guard_at=time.monotonic()
                for action in pressed:
                    if action in ('attack','aoe','break'):
                        # Latest manual intent wins; bounded one-slot queue,
                        # trusted server deadline, and unchanged skill rules.
                        if p.sp >= prog.SKILL_SP[action]:
                            p.manual_auto_skill=action
                            p.manual_auto_until=time.monotonic()+AUTO_MANUAL_PRIORITY_SEC
                    else:
                        perform_action(p,action)
            else:
                p.buttons=buttons
                p.last_input=time.monotonic()
                if p.movement_mode=='client' and (buttons & 3) in (1,2):
                    p.face=1 if buttons & 2 else -1
                for action in pressed:
                    perform_action(p,action)
                    if p.movement_mode=='client' and action in ('jump','dash') and p.move_shadow is not None:
                        # Accept only server-approved animation impulse into validator.
                        prior=p.move_shadow
                        updated=list(prior)
                        for i,key in enumerate(_MOVE_FIELDS):
                            if key in ('vx','vy','ground','climb','face'):
                                updated[i]=getattr(p,key)
                        p.move_shadow=tuple(updated)
    except (asyncio.TimeoutError, ConnectionClosed):
        pass
    except Exception as exc:
        print('JIANGHU_CONNECTION_EXCEPTION ch=',getattr(admitted_world,'channel',None),
              'guest=',guest_id,'type=',type(exc).__name__,'detail=',str(exc)[:200],flush=True)
        raise
    finally:
        if pending_held:_pending_joins -= 1
        if guest_id and players.get(guest_id) and players[guest_id].ws is ws:
            active=players[guest_id].snapshot_task
            if active:
                active.cancel()
                try:await active
                except asyncio.CancelledError:pass
            fast=players[guest_id].fast_self_task
            if fast:
                fast.cancel()
                try:await fast
                except asyncio.CancelledError:pass
            for nav in SWAMP_RECOVERY.values():nav.reset(guest_id)
            p = players.pop(guest_id)
            connected_players.pop(guest_id,None)
            event('leave', p.x, p.y, victim=guest_id)
            shots[:] = [shot for shot in shots if shot.owner != guest_id]
            hibernate_world(p.world_ref)
        elif admitted_world is not None and not admitted_world.players:
            # E.g. socket died after first-world wake but before actor creation.
            hibernate_world(admitted_world)


def process_request(connection, request):
    if request.path == '/healthz':
        return connection.respond(HTTPStatus.OK, 'wuxia-online v8.0CR network writer stage profile + dense-world AOI index; cooperative-PvE; AOI/delta\n')
    if request.path != '/ws':
        return connection.respond(HTTPStatus.NOT_FOUND, 'Use /ws for WebSockets\n')
    return None


async def main():
    load_from_supabase()
    print('Combat balance: '+source,flush=True)
    ok=prog.load_exp_balance(os.environ.get('SUPABASE_URL','https://uxxkyptoocbswedwizct.supabase.co'),os.environ.get('SUPABASE_PUBLISHABLE_KEY','sb_publishable_GDhK1Y-OrFCwzWRunfc-UQ_56NeDD4M'))
    print('EXP balance: '+prog.EXP_SOURCE,flush=True)
    # EF: each forest starts asleep. Admit first player -> wake with map manifest
    # and timed sleeping capsule; last departure -> release all runtime entities.
    # Default remains uncompressed for like-for-like A/B testing. Enable on
    # Hostatom only after recording a baseline. Browser WebSocket negotiation
    # transparently decompresses frames before application JSON decoding.
    from websockets.extensions.permessage_deflate import ServerPerMessageDeflateFactory
    ws_extensions=([ServerPerMessageDeflateFactory(compress_settings={'level':1,'memLevel':5})]
                   if WS_COMPRESSION=='deflate' else None)
    async with serve(handle_connection, HOST, PORT, max_size=2048, max_queue=16,
                     ping_interval=20, ping_timeout=20, process_request=process_request,
                     compression=None, extensions=ws_extensions):
        print(f'WUXIA online server ready on {HOST}:{PORT} | guest limit {CHANNEL_TOTAL_GUEST_CAP} | WS compression {WS_COMPRESSION} | slots {STAGGER_SLOTS} | background view snapshots {AUTO_BG_SNAP_HZ}Hz | self A/B v8.0EO public CH1-3 + opted-in stress CH1-15 + lazy hibernation + EK stagger/event-journal', flush=True)
        await game_loop()

if __name__ == '__main__':
    asyncio.run(main())

