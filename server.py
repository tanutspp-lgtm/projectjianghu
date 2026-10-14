"""WUXIA Flute Arena guest-only authoritative arena server.
Browser inputs are UNTRUSTED. Position, damage, HP, monsters, cooldowns are server-owned.
Runs on Python 3.11+ with websockets>=15.
"""
import asyncio
from pathlib import Path
import json
import math
import os
import secrets
import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Optional

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed
import random
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
# 0 = original map levels (1..5); 1..60 = Offline v8.0AO level preset for ALL beasts.
# Deliberately not controlled by any untrusted client; set on the Render service.
MONSTER_PRESET_LEVEL=int(os.environ.get('MONSTER_PRESET_LEVEL','5'))
if not 0<=MONSTER_PRESET_LEVEL<=60:raise ValueError('MONSTER_PRESET_LEVEL must be 0..60')
# QA loadouts are NOT real obtained gear. Keep disabled on public servers.
ENABLE_GUEST_SANDBOX=os.environ.get('ENABLE_GUEST_SANDBOX','0')=='1'
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
    for lo, hi, top in GROUND:
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
    avatar: str = 'male_hair_01_black'
    buttons: int = 0
    last_input: float = field(default_factory=time.monotonic)
    last_seq: int = -1
    packet_times: deque = field(default_factory=deque)
    action_times: deque = field(default_factory=deque)
    level: int = 5  # server-owned guest training level, not client-controlled
    armor_enhance: int = 5  # server-owned reference +5 armor
    last_attack_at: float = -1e9
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
    snapshot_outbox: asyncio.Queue = field(default_factory=lambda:asyncio.Queue(maxsize=1))
    snapshot_task: Optional[asyncio.Task] = None
    snapshot_slot: int = 0  # 0..9, 10ms-phase staggering across each 100ms broadcast cycle
    applied_input_seq: int = -1  # actual command consumed by the authoritative 30Hz simulation
    protocol_delta: bool = False # legacy BX clients still require unfiltered full snapshots
    stable_stats_key: object = None
    stable_derived_stats: object = None
    client_perf: dict = field(default_factory=dict)
    client_perf_at: float = 0.0


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


players: dict[str, Guest] = {}
monsters: dict[str, Monster] = {}
shots: list[Shot] = []
loot_drops: list[dict] = []
LOOT_TEMPLATES=json.loads(Path(__file__).with_name('loot_templates_v80bs.json').read_text(encoding='utf-8'))
LOOT_PICKUP_X=130
LOOT_PICKUP_Y=75
LOOT_OWNER_SEC=60
LOOT_LIFETIME_SEC=180
LOOT_INTRO_SEC=0.98
LOOT_BAG_CAP=48
events: list[dict] = []
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
SPATIAL_CELL = 240

def index_players_by_x():
    # Share one indexed player roster across 20 beasts; combat remains authoritative.
    cells = defaultdict(list)
    for p in players.values():
        if p.dead<=0:
            cells[int(p.x // SPATIAL_CELL)].append(p)
    return cells

def candidate_players_by_x(m, grid):
    if grid is None:
        return players.values()  # direct unit calls still work without an index
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
                     playerCount=len(players),monsterCount=len(monsters),
                     eventLoopLagP95Ms=p95(lags),eventLoopLagMaxMs=peak(lags),
                     snapshotEncodeP95Ms=p95(encodes),snapshotEncodeMaxMs=peak(encodes))
    perf_in_count=0;perf_out_bytes=0;perf_last_report=now



def report_performance_to_render(now):
    """Emit one compact, structured, anonymous JSON line every 15s.
    Read these with Render list_logs text='JIANGHU_DIAG' and compare with CPU metrics.
    No external IO here beyond a bounded print; no database dependency in game loop.
    """
    global _diag_last, _diag_process_cpu, _diag_sent, _diag_overwritten
    if now-_diag_last<DIAG_WINDOW_SEC:return
    window=now-_diag_last
    cpu_delta=time.process_time()-_diag_process_cpu
    _diag_last=now;_diag_process_cpu=time.process_time()
    active=[p.client_perf for p in players.values() if p.client_perf and now-p.client_perf_at<35]
    sends=sorted(_diag_send_durations)
    def percentile(a, ratio):
        return round(a[min(len(a)-1,int((len(a)-1)*ratio))],2) if a else None
    data={
        'v':'v8.0CL','boot':_diag_boot,'ts':int(time.time()),'windowSec':round(window,1),
        'guests':len(players),'autoGuests':sum(bool(p.auto_state.enabled) for p in players.values()),
        'monsters':len(monsters),'cpuCorePct':round(100*cpu_delta/max(.001,window),1),
        'tickP95Ms':perf_data['tickP95Ms'],'tickMaxMs':perf_data['tickMaxMs'],
        'loopP95Ms':perf_data['eventLoopLagP95Ms'],'loopMaxMs':perf_data['eventLoopLagMaxMs'],
        'encodeP95Ms':perf_data['snapshotEncodeP95Ms'],'encodeMaxMs':perf_data['snapshotEncodeMaxMs'],
        'snapSent':_diag_sent,'snapOverwritten':_diag_overwritten,
        'wsSendP95Ms':percentile(sends,0.95),'wsSendMaxMs':percentile(sends,1.0),
        'txKiBs':perf_data['txKiBPerSec'],'rxInputsSec':perf_data['rxInputsPerSec'],
        'browserCount':len(active),'browserFpsMin':min((a['fps'] for a in active),default=None),
        'browserPingMsP95':percentile(sorted(a['pingMs'] for a in active if a['pingMs'] is not None),0.95),
        'browserSnapGapP95Ms':percentile(sorted(a['gapP95Ms'] for a in active),0.95),
        'browserSnapGapMaxMs':max((a['gapMaxMs'] for a in active),default=None),
        'browserFrameMsP95':percentile(sorted(a['frameMs'] for a in active),0.95),
    }
    # No telemetry is written to Supabase until a separate authenticated storage path exists.
    print('JIANGHU_DIAG '+json.dumps(data,separators=(',',':')),flush=True)
    _diag_sent=0;_diag_overwritten=0;_diag_send_durations.clear()


# NOTE: The OFFLINE JavaScript spawner remains the source of truth for this test-map
# manifest. Regenerate the JSON when changing the map; never accept client spawn data.
BEAST_AGGRO=280
BEAST_CHASE_SPEED=112
BEAST_PATROL_SPEED=BEAST_CHASE_SPEED*0.65
RESPAWN_WAVE_SEC=7.56
RESPAWN_MIN_SEC=5.0
SERVER_BORN=time.monotonic()

def next_respawn_delay():
    elapsed=time.monotonic()-SERVER_BORN
    wave=math.ceil((elapsed+RESPAWN_MIN_SEC+1e-7)/RESPAWN_WAVE_SEC)*RESPAWN_WAVE_SEC
    return max(RESPAWN_MIN_SEC,wave-elapsed)

def supported(m, x=None):
    x=m.x if x is None else x
    return any(abs(m.y-y)<12 and lo+20<x<hi-20 for lo,hi,y in GROUND)

def own_lane(m):
    return next(((lo,hi,y) for lo,hi,y in GROUND if abs(m.y-y)<12 and lo+12<m.x<hi-12),None)

def reachable_player(m,p):
    lane=own_lane(m)
    if not lane or p.dead>0 or p.climb or not lane[0]+12<p.x<lane[1]-12:return False
    if p.ground:return abs(p.y-m.y)<12
    return m.y-128<=p.y<=m.y+22

def spawn_mobs():
    monsters.clear()
    for index,slot in enumerate(MAP_DATA['slots']):
        species=slot['kind']
        assert species in ('boar','wolf')
        x,y=float(slot['x']),float(slot['y'])
        mid=slot['id']
        level=MONSTER_PRESET_LEVEL or min(5,1+index%5)
        max_hp,defense=monster_balance.preset(level,False)
        monsters[mid]=Monster(id=mid,name='หมูป่า' if species=='boar' else 'หมาป่า',
            x=x,y=y,hp=max_hp,max_hp=max_hp,defense=defense,home=x,spawn_y=y,hum=False,
            level=level,zone_mode='common',species=species,
            slot=mid,pouncer=slot.get('pouncer',False),bite_ready_at=time.monotonic()+.45,
            patrol_dir=-1 if index%2 else 1,patrol_until=0,spawn_at=time.monotonic())


def event(event_type, x, y, **kwargs):
    events.append({'t': event_type, 'x': round(x, 1), 'y': round(y, 1), **kwargs})


def set_action(actor, a, dur):
    actor.action = a
    actor.action_at = 0
    actor.action_duration = dur


def physics(actor, dt):
    # v8.0CI: Resolve horizontal world-wall collision BEFORE ground support.
    # Dash can move > one collider margin in a single 30Hz server tick. If
    # can_stand sees the out-of-bounds x before clamping, a grounded character
    # may miss the one-way floor and fall underneath it permanently.
    actor.x = clamp(actor.x, 27, WORLD_W - 27)
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


def hurt(victim, damage, x, y, kind,critical=False):
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
    event('hit', victim.x, victim.y - 78, victim=victim.id, damage=damage, kind=kind,critical=critical)
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
    global shot_seq
    cooldown, duration, speed, _, lifespan, pierce = ATTACKS[action]
    damage,critical=prog.roll_attack(p,action,hp_reference)
    p.sp-=prog.SKILL_SP[action]
    p.cool = cooldown
    set_action(p, action, duration)
    shot_seq += 1
    y = p.y - 84 - (3 if action == 'aoe' else 4 if action == 'break' else 0)
    shots.append(Shot(shot_seq, p.id, action, p.x + p.face * 52, y, p.face * speed, damage, lifespan, pierce, critical=critical))
    # Every confirmed cast has a short-lived visual trace even when the actual
    # server-owned projectile hits a mob before the next 10Hz snapshot.
    event('cast',p.x,p.y-34,kind=action,owner=p.id,shotId=str(shot_seq),
          shotX=round(p.x+p.face*52,1),shotY=round(y,1),shotDir=p.face,
          shotSpeed=speed)


def update_guest(p: Guest, dt, tick_now):
    p.applied_input_seq=p.last_seq  # ack only after simulation consumes this input
    for v in ('cool', 'inv', 'stun', 'down', 'broken', 'climb_cd'):
        setattr(p, v, max(0, getattr(p, v) - dt))
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
    near = next((c for c in CLIMBS if abs(c[0] - p.x) < 36 and c[1] - 8 <= p.y <= c[2] + 12), None)
    axis = int(bool(p.buttons & 8)) - int(bool(p.buttons & 4))
    # v8.0CE: Holding UP on the upper platform must never re-capture
    # the ladder and start a fresh upward climb through open air.
    # Players can still intentionally press DOWN to descend from the landing.
    if near and axis < 0 and p.ground and p.y <= near[1] + 6:
        near = None
    if near and axis and not p.guard and p.climb_cd <= 0:
        p.climb = near
        p.x, p.vx, p.vy, p.ground = near[0], 0, 0, False
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
            p.climb, p.climb_cd, p.y, p.x, p.ground = None, .28, top, cx + 47, True
        elif axis > 0 and p.y >= bottom - 1:
            p.climb, p.climb_cd, p.y, p.x, p.ground = None, .28, bottom, cx + 45, True
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
            m.patrol_phase='idle';m.patrol_until=t+.18+random.random()*.23
            return 0
        m.patrol_dir=direction
        m.patrol_goal_x=goal
        m.patrol_until=t+duration
        m.patrol_phase='walk'
    direction=m.patrol_dir
    if t>=m.patrol_until or (m.x>=m.patrol_goal_x if direction>0 else m.x<=m.patrol_goal_x):
        m.patrol_phase='idle';m.patrol_until=t+.35+random.random()*.55
        return 0
    if not supported(m,m.x+direction*26):
        m.patrol_dir=-direction
        m.patrol_phase='idle';m.patrol_until=t+.18+random.random()*.23
        return 0
    return direction*BEAST_PATROL_SPEED


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
            m.aggro_until=0;m.patrol_phase='choose';m.patrol_until=0;m.last_combat=False;m.mark_stacks.clear()
            m.spawn_at=t
        return
    m.stun=max(0,m.stun-dt)
    m.down=max(0,m.down-dt)
    m.broken=max(0,m.broken-dt)
    # Spatial grid reduces the candidate roster; no change to hit detection.
    p=min((p for p in candidate_players_by_x(m,player_grid)
           if reachable_player(m,p) and abs(p.x-m.x)<BEAST_AGGRO+65),
          key=lambda p:abs(p.x-m.x),default=None)
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
    if not stopped and m.bite_started_at<0 and engage and m.ground and t>=m.bite_ready_at and abs(dx)<72 and abs(dy)<62:
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
            m.last_combat=False;m.patrol_phase='choose'
        m.vx=mob_patrol(m,t)
    if m.vx:
        direction=1 if m.vx>0 else -1
        if not supported(m,m.x+direction*26):m.vx=0
        else:m.face=direction
    m.x+=m.vx*dt
    physics(m,dt)
    if abs(m.x-m.home)>380:
        m.x=m.home+380*(1 if m.x>m.home else -1)
        m.vx=0
    # Bites have an animation wind-up, with real contact damage only after impact.
    if m.bite_started_at>0 and not m.bite_hit_done and t-m.bite_started_at>=.19:
        m.bite_hit_done=True
        if p and p.dead<=0 and abs(p.x-m.x)<60 and abs(p.y-m.y)<60 and p.inv<=0:
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
    valid=[y for lo,hi,y in GROUND if lo+12<x<hi-12 and y>=m.y-22]
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
        for p in players.values():
            if p.dead>0 or p.hp<=0 or len(p.inventory)>=LOOT_BAG_CAP:continue
            if t<drop['privateUntil'] and p.id!=drop['ownerId']:continue
            if abs(p.x-drop['x'])>LOOT_PICKUP_X or abs(p.y-drop['y'])>LOOT_PICKUP_Y:continue
            entry={'uid':'bag-'+secrets.token_hex(8),'item_id':drop['item_id'],'obtainedAt':int(time.time()*1000)}
            p.inventory.append(entry)
            event('loot_pickup',drop['x'],drop['y'],victim=p.id,item_id=drop['item_id'])
            # Updated bag is sent only to the owner, never copied into public snapshots.
            # The socket event is queued outside the synchronous world update.
            loot_drops.remove(drop)
            break


def grant_monster_kill(s,m):
    killer=players.get(s.owner)
    if killer is None:return
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
    previous_alive=victim.hp>0 and victim.dead<=0
    actual=mitigate(damage,victim.defense) if is_mob else damage
    hurt(victim,actual,s.x,s.y,s.kind,critical=s.critical)
    if previous_alive and is_mob and victim.hp<=0:grant_monster_kill(s,victim)
    return actual


def bonus_hit(killer, victim, raw,kind='qi_echo'):
    """Qi bonus is a real server-side damage event; never trust client hits."""
    if victim.dead>0 or victim.hp<=0:return 0
    value=mitigate(prog.jsround(raw),victim.defense)  # same DEF/(250+DEF) as Offline
    victim.hp=max(0,victim.hp-value)
    victim.stun=max(victim.stun,.2)
    victim.vx=0
    victim.bite_started_at=-1e9
    event('hit',victim.x,victim.y-78,victim=victim.id,damage=value,kind=kind)
    if victim.hp<=0:
        victim.dead=next_respawn_delay();victim.guard=False
        event('defeat',victim.x,victim.y-80,victim=victim.id)
        grant_monster_kill(type('Owner',(),{'owner':killer.id})(),victim)
    return value


def apply_qi_on_primary_hit(shot,victim,damage):
    killer=players.get(shot.owner)
    if not killer or not isinstance(victim,Monster):return
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


def update_shots(dt):
    active = []
    for s in shots:
        s.life -= dt
        s.x += s.vx * dt
        if s.life <= 0 or s.x < -80 or s.x > WORLD_W + 80: continue
        # PvE only. Player bodies are not candidates: projectiles pass through
        # all Guests, including their guards and overlapping farming positions.
        victims = [v for v in monsters.values() if v.dead <= 0 and abs(v.y - s.y - 78) < 95 and abs(v.x - s.x) < (60 if s.kind == 'aoe' else 36)]
        victims.sort(key=lambda v: abs(v.x - s.x))
        consumed = False
        for v in victims:
            if apply_shot(s, v, isinstance(v, Monster)):
                consumed = True
                break
        if not consumed: active.append(s)
    shots[:] = active


def actor_frame(a, tick):
    if a.dead > 0: return 18 if a.ground else 16
    if a.down > 0: return 17 if a.ground else 16
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


def actor_json(a):
    return {'id': a.id, 'level': a.level if isinstance(a,(Guest,Monster)) else 1, 'x': round(a.x, 2), 'y': round(a.y, 2), 'vx': round(a.vx, 2), 'vy': round(a.vy, 2),
            'face': a.face, 'hp': a.hp, 'max': a.max_hp, 'ground': a.ground, 'guard': a.guard, 'down': round(a.down, 2), 'dead': round(a.dead, 2),
            'stun': round(a.stun, 2), 'inv': round(a.inv, 2), 'climb': bool(a.climb), 'frame': actor_frame(a, server_step), 'action': a.action,
            **({'defense':a.defense} if isinstance(a,Monster) else {'lastAppliedSeq':a.applied_input_seq})}


def derived_for_snapshot(p):
    # Dirty-signature cache: recompute expensive gear/qi/derived totals only
    # after server-owned level/stat/qi/equipment state changes, not every 100ms.
    sig=(p.level,p.test_level,tuple(p.stats[k] for k in prog.STAT_KEYS),
         tuple(p.qi_equipped),tuple(sorted((k,tuple(sorted(v.items()))) for k,v in p.qi_ranks.items())),
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
            'auto':p.auto_state.enabled,'autoTarget':(dict(p.auto_state.goal) if p.auto_state.enabled and p.auto_state.goal else None),
            'autoTargetSeconds':round(max(0,p.auto_state.goal_due-time.monotonic()),1) if p.auto_state.enabled else 0,
            'sandboxAvailable':ENABLE_GUEST_SANDBOX,'inputAck':p.applied_input_seq,'performance':perf_data.copy(),**(loadouts.private_snapshot(p) if ENABLE_GUEST_SANDBOX else {})}


# v8.0BY network scalability: one server-owned world sample per 100ms.
# AOI is strictly visual; hit detection and rewards still use ALL server actors.
AOI_RADIUS=int(os.environ.get('AOI_RADIUS','950'))
if AOI_RADIUS<700 or AOI_RADIUS>6000:raise ValueError('AOI_RADIUS must be 700..6000')
DELTA_REFRESH_TICKS=150 # 5 seconds at 30Hz, periodic full keyframe self-heals missed state.


def snapshot():
    """Shared immutable-by-convention world state; no per-guest JSON on the tick path."""
    moment=time.monotonic()
    return {'t':'snapshot','tick':server_step,
            'players':[{**actor_json(p),'avatar':p.avatar} for p in players.values()],
            'mobs':[{**actor_json(m),'name':m.name,'hum':m.hum,'species':m.species,
                     'biteAge':round(max(0,moment-m.bite_started_at),3) if m.bite_started_at>0 else -1,
                     'spawnId':m.slot} for m in monsters.values()],
            'loot':[{'id':d['id'],'item_id':d['item_id'],'x':d['x'],'y':d['y'],
                     'ownerId':d['ownerId'],'privateFor':round(max(0,d['privateUntil']-moment),1),
                     'expiresIn':round(max(0,d['expiresAt']-moment),1)} for d in loot_drops],
            'shots':[{'id':str(s.id),'kind':s.kind,'x':round(s.x,1),'y':round(s.y,1),
                      'dir':1 if s.vx>=0 else -1} for s in shots],
            'events':events[:80]}


def aoi_view(world,p):
    """Send a generous world-space window. Never let a client choose their AOI origin."""
    cx=p.x
    radius=AOI_RADIUS
    view={}
    for field in ('players','mobs','shots','loot'):
        # Keep ranged projectile and enemy telegraphs visible slightly outside AOI.
        extra=200 if field in ('mobs','shots') else 0
        view[field]={e['id']:e for e in world[field]
                     if (field=='players' and e['id']==p.id) or abs(e['x']-cx)<=radius+extra}
    return view


def encode_aoi_delta(world,p,previous,last_full_tick,prev_private=None,prev_inventory=None):
    """Diff from LAST SUCCESSFULLY SENT packet, not the newest queued packet.
    Dropped mailbox packets can't corrupt the next delta's baseline.
    """
    current=aoi_view(world,p)
    full=previous is None or world['tick']-last_full_tick>=DELTA_REFRESH_TICKS
    result={'t':'snapshot','tick':world['tick']}
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
                    patch={'id':key}
                    for attr,value in item.items():
                        if attr!='id' and old.get(attr)!=value:patch[attr]=value
                    if len(patch)>1:changed.append(patch)
            result[kind]=changed
            missing=[key for key in before if key not in entities]
            if missing:result['removed'+kind.capitalize()]=missing
    result['events']=[e for e in world['events'] if e.get('victim')==p.id or
                       e.get('owner')==p.id or abs(float(e.get('x',p.x))-p.x)<=AOI_RADIUS+200]
    priv=private_progression(p)
    priv['inputAck']=current['players'][p.id]['lastAppliedSeq']
    if full or prev_private is None:
        result['self']=priv
    else:
        result['self']={k:v for k,v in priv.items() if prev_private.get(k)!=v}
    inv=[dict(e) for e in p.inventory] # isolated ownership snapshot; no alias mutations
    if full or prev_inventory!=inv:
        result['inventory']=inv
    return (json.dumps(result,separators=(',',':')),current,
            (world['tick'] if full else last_full_tick),priv,inv)


async def snapshot_writer(p: Guest):
    """Stagger 10Hz sending, serialize/diff per client in that phase (not game tick).
    Bounded one-snapshot mailbox; one slow socket cannot block simulation.
    """
    previous=None;last_full_tick=-1;prev_private=None;prev_inventory=None
    try:
        while True:
            world=await p.snapshot_outbox.get()
            period=.1;offset=p.snapshot_slot*.01
            wait=(offset-(time.monotonic()%period))%period
            if wait>.001:await asyncio.sleep(wait)
            # Consume the newest world, if producer overran our send slot.
            while not p.snapshot_outbox.empty():
                try:world=p.snapshot_outbox.get_nowait()
                except asyncio.QueueEmpty:break
            encode_start=time.monotonic()
            if p.protocol_delta:
                packet,current,full_tick,priv,inv=encode_aoi_delta(world,p,previous,last_full_tick,prev_private,prev_inventory)
            else:
                # Legacy clients receive original full-world shape until upgraded.
                old={**world,'self':private_progression(p),'inventory':p.inventory}
                packet=json.dumps(old,separators=(',',':'))
                current,full_tick,priv,inv=None,-1,None,None
            perf_encodes.append(time.monotonic()-encode_start)
            try:
                send_start=time.monotonic()
                await asyncio.wait_for(p.ws.send(packet),timeout=1.5)
                global _diag_sent
                _diag_sent+=1
                _diag_send_durations.append((time.monotonic()-send_start)*1000)
                global perf_out_bytes
                perf_out_bytes += len(packet.encode('utf-8'))
                previous,last_full_tick=current,full_tick
                prev_private,prev_inventory=priv,inv
            except (asyncio.TimeoutError,ConnectionClosed,OSError):
                try:await p.ws.close(code=1011,reason='Snapshot send timeout')
                except Exception:pass
                return
    except asyncio.CancelledError:return


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
    global server_step
    next_tick=time.monotonic()
    while True:
        next_tick+=DT
        tick_now=time.monotonic()
        # Tick P95 excludes the snapshot_writer coroutine. Measure scheduling
        # lag separately so 30-socket bottlenecks become observable.
        perf_loop_lags.append(min(3.0,max(0.0,tick_now-(next_tick-DT))))
        server_step+=1
        for p in list(players.values()):
            if p.auto_state.enabled:
                # Keep authoritative physics at 30Hz; decisions at <=10Hz.
                # Movement remains held between decisions, no browser AI.
                if tick_now >= p.auto_state.next_step:
                    buttons,actions=FARM_NAV.choose(p,p.auto_state,tick_now,monsters)
                    p.buttons=buttons
                    p.auto_state.next_step=tick_now+.1
                    for action in actions:perform_action(p,action)
                p.last_input=tick_now
            update_guest(p,DT,tick_now)
        grid=index_players_by_x()
        for m in monsters.values():update_mob(m,DT,grid)
        update_shots(DT)
        advance_loot()
        if server_step%3==0 and players:
            world=snapshot()
            for p in list(players.values()):
                if p.snapshot_task is not None and not p.snapshot_task.done():
                    queue_latest_snapshot(p,world)
            events.clear()
        elif server_step%3==0:events.clear()
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


async def handle_connection(ws):
    guest_id = None
    global snapshot_join_sequence
    try:
        if ORIGINS and (ws.request.headers.get('Origin') not in ORIGINS):
            await ws.close(code=1008, reason='Origin not allowed');return
        raw = await asyncio.wait_for(ws.recv(), timeout=8)
        hello = strict_message(raw)
        if not hello or set(hello.keys()) not in ({'t', 'avatar'},{'t','avatar','protocol'}) or hello.get('t') != 'join' or not valid_avatar(hello.get('avatar')) or hello.get('protocol','legacy') not in ('legacy','aoi-delta-v80by'):
            await ws.close(code=1008, reason='Invalid guest join');return
        if len(players) >= MAX_GUESTS:
            await ws.send(json.dumps({'t': 'error', 'message': 'ห้องเต็ม ลองใหม่ภายหลัง'}));await ws.close(code=1013);return
        guest_id = 'g-' + secrets.token_hex(8)
        name = 'Guest-' + guest_id[-4:].upper()
        # All legal spawn points are server-defined, never supplied by client.
        spawn_x = 175 + (len(players) % 8) * 35
        guest_level=1  # same Lv1 start as Offline; ephemeral Guest, no DB character save
        guest_hp=prog.base_hp_for_level(guest_level,hp_reference)
        p = Guest(id=guest_id, x=spawn_x, y=550, hp=guest_hp, max_hp=guest_hp,
                  avatar=hello['avatar'], ws=ws, level=guest_level)
        prog.apply_derived_resources(p,hp_reference,full=True)
        p.protocol_delta=(hello.get('protocol')=='aoi-delta-v80by')
        # Evenly distribute connection slots; no random clumping for first 10 guests.
        p.snapshot_slot=snapshot_join_sequence%10
        snapshot_join_sequence+=1
        players[guest_id] = p
        features=['beast-v80bq','progression-v80bs','monster-hpdef-v80bu','auto','aoi-delta-v80by','input-ack-v80by','cooperative-pve-only-v80ca','responsive-walk-v80ca','jump-rope-visual-v80cb','cast-fx-reliable-v80cb','wire-shot-ids-v80cd','map-climb-verified-v80cd','rtt-probe-v80ce','ladder-ceiling-v80ce','client-perf-v80cl']
        if ENABLE_GUEST_SANDBOX:features.append('sandbox-loadouts-v80bt')
        await ws.send(json.dumps({'t': 'welcome', 'id': guest_id, 'name': name, 'tickRate': 30, 'snapshotRate': 10, 'guest': True, 'features':features,'mapVersion':'beast-v80bq','mapClimbs':[{'x':x,'top':t,'bottom':b} for x,t,b in CLIMBS],'monsterPresetLevel':MONSTER_PRESET_LEVEL,'expSource':prog.EXP_SOURCE}))
        p.snapshot_task=asyncio.create_task(snapshot_writer(p),name='snapshot-'+guest_id)
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
                if set(m)!={'t','enabled'} or type(m.get('enabled')) is not bool:
                    await ws.close(code=1008,reason='Invalid AUTO toggle');break
                if not check_rate(p.action_times,12):
                    await ws.close(code=1008,reason='AUTO toggle rate limit');break
                p.auto_state.enabled=m['enabled']
                p.buttons=0
                if p.auto_state.enabled:
                    # Fresh independently randomized destination at the next game tick.
                    p.auto_state.goal=None;p.auto_state.goal_due=0;p.auto_state.next_step=0
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
            # Manual movement/attacks cancel AUTO; inert heartbeats do not.
            if p.auto_state.enabled and (buttons or pressed):p.auto_state.enabled=False
            if not p.auto_state.enabled:
                p.buttons = buttons
                p.last_input = time.monotonic()
                for action in pressed: perform_action(p, action)
    except (asyncio.TimeoutError, ConnectionClosed):
        pass
    finally:
        if guest_id and players.get(guest_id) and players[guest_id].ws is ws:
            active=players[guest_id].snapshot_task
            if active:
                active.cancel()
                try:await active
                except asyncio.CancelledError:pass
            p = players.pop(guest_id)
            event('leave', p.x, p.y, victim=guest_id)
            shots[:] = [shot for shot in shots if shot.owner != guest_id]


def process_request(connection, request):
    if request.path == '/healthz':
        return connection.respond(HTTPStatus.OK, 'wuxia-online v8.0CL render diagnostic telemetry + v8.0CI wall-dash collision; cooperative-PvE; AOI/delta\n')
    if request.path != '/ws':
        return connection.respond(HTTPStatus.NOT_FOUND, 'Use /ws for WebSockets\n')
    return None


async def main():
    load_from_supabase()
    print('Combat balance: '+source,flush=True)
    ok=prog.load_exp_balance(os.environ.get('SUPABASE_URL','https://uxxkyptoocbswedwizct.supabase.co'),os.environ.get('SUPABASE_PUBLISHABLE_KEY','sb_publishable_GDhK1Y-OrFCwzWRunfc-UQ_56NeDD4M'))
    print('EXP balance: '+prog.EXP_SOURCE,flush=True)
    spawn_mobs()
    async with serve(handle_connection, HOST, PORT, max_size=2048, max_queue=16, ping_interval=20, ping_timeout=20, process_request=process_request, compression=None):
        print(f'WUXIA online server ready on {HOST}:{PORT} | guest limit {MAX_GUESTS}', flush=True)
        await game_loop()

if __name__ == '__main__':
    asyncio.run(main())
