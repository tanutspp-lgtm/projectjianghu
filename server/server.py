"""WUXIA Flute Arena v7.9N authoritative arena server.
Browser inputs are UNTRUSTED. Position, damage, HP, monsters, cooldowns are server-owned.
Runs on Python 3.11+ with websockets>=15.
"""
import asyncio
import json
import math
import os
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Optional

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from auth import AuthenticationError, SupabaseAuthVerifier
from persistence import PersistenceError, build_store_from_environment
from progression import BalanceConfig, Contribution, contribution_shares, scaled_award
from protocol import ALLOWED_BUTTONS, ACTION_NAMES, parse_auth_refresh, parse_input, parse_join, valid_avatar

PORT = int(os.environ.get('PORT', '8765'))
HOST = os.environ.get('HOST', '0.0.0.0')
ORIGINS = tuple(s.strip() for s in os.environ.get('ALLOWED_ORIGINS', '').split(',') if s.strip())
MAX_GUESTS = int(os.environ.get('MAX_GUESTS', '35'))
# Safari and mobile browsers can pause background tabs. Grace permits seamless guest resume.
RESUME_GRACE_SECONDS = 300

WORLD_W = 2060
DT = 1.0 / 30.0
GROUND = [(0, 2060, 550), (170, 850, 390), (1020, 1770, 390), (410, 1070, 235), (1210, 1970, 235)]
CLIMBS = ((510, 235, 550), (1170, 235, 550), (1590, 235, 550))
ATTACKS = {'attack': (0.34, 0.32, 520, 165, 1.45, 1), 'aoe': (0.62, 0.48, 365, 135, 1.15, 99), 'break': (0.52, 0.37, 560, 45, 1.1, 2)}

DATA_ROOT = Path(__file__).resolve().parent.parent / 'database'
_supabase_url = os.environ.get('SUPABASE_URL', '').strip()
_publishable_key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '').strip()
_server_key = (os.environ.get('SUPABASE_SECRET_KEY', '').strip() or os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip())
balance = (BalanceConfig.from_supabase(_supabase_url, _server_key)
           if _supabase_url and _server_key else BalanceConfig.from_csv_directory(DATA_ROOT))
character_store = build_store_from_environment(os.environ, balance)
auth_verifier = SupabaseAuthVerifier(_supabase_url, _publishable_key) if _supabase_url and _publishable_key else None
server_instance_id = secrets.token_hex(8)
pending_persistence_tasks = set()

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
    resume_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    offline_at: float = 0.0
    auto_mode: bool = False
    snapshot_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1))
    sender_task: object = None
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    character_name: str = ''
    level: int = 1
    total_exp: int = 0
    balance_version: str = 'exp_v1'
    auth_expires_at: int = 0

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
    level: int = 1
    life_id: int = 1
    contributions: dict[str, Contribution] = field(default_factory=dict)

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
    pve_only: bool = False

players: dict[str, Guest] = {}
guest_tokens: dict[str, str] = {}
monsters: dict[str, Monster] = {}
shots: list[Shot] = []
events: list[dict] = []
shot_seq = 0
server_step = 0


def spawn_mobs():
    specs = [('m1', 'ฝึกยุทธ์', 740, 390, 1100, True, 2), ('m2', 'หมาป่า', 380, 550, 450, False, 1), ('m3', 'หมาป่า', 1340, 390, 450, False, 1), ('m4', 'หมาป่า', 1630, 235, 450, False, 1), ('m5', 'จอมยุทธ์คู่ซ้อม', 1520, 550, 1100, True, 3)]
    for mid, name, x, y, hp, hum, level in specs:
        monsters[mid] = Monster(id=mid, name=name, x=x, y=y, hp=hp, max_hp=hp, home=x, spawn_y=y, hum=hum, ai_cool=0.5, level=level)


def event(event_type, x, y, **kwargs):
    events.append({'t': event_type, 'x': round(x, 1), 'y': round(y, 1), **kwargs})


def set_action(actor, a, dur):
    actor.action = a
    actor.action_at = 0
    actor.action_duration = dur


def physics(actor, dt):
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
    actor.x = clamp(actor.x, 27, WORLD_W - 27)
    if actor.y > 800:
        actor.y, actor.vy, actor.ground = 550, 0, True
        if isinstance(actor, Guest):
            hurt(actor, 100, actor.x, actor.y - 70, 'fall')


def hurt(victim, damage, x, y, kind):
    if victim.dead > 0 or victim.inv > 0: return 0
    if isinstance(victim, Guest) and victim.guard and victim.broken <= 0:
        event('block', victim.x, victim.y - 82, victim=victim.id)
        return 0
    hp_before = victim.hp
    victim.hp = max(0, victim.hp - damage)
    victim.stun = 0.25
    victim.inv = .42 if isinstance(victim, Guest) else 0
    event('hit', victim.x, victim.y - 78, victim=victim.id, damage=damage, kind=kind)
    if victim.hp <= 0 and victim.dead <= 0:
        victim.dead = 3.2 if isinstance(victim, Monster) else 2.5
        victim.guard = False
        event('defeat', victim.x, victim.y - 80, victim=victim.id)
    return hp_before - victim.hp


def progression_json(p):
    view = balance.view(p.total_exp)
    return {
        'id': p.character_id,
        'name': p.character_name or ('Guest-' + p.id[-4:].upper()),
        'avatar': p.avatar,
        'level': view.level,
        'totalExp': view.total_exp,
        'currentExp': view.current_exp,
        'expToNext': view.exp_to_next,
        'atCap': view.at_cap,
        'balanceVersion': p.balance_version,
    }


def apply_character_record(p, record):
    view = balance.view(record.total_exp)
    p.user_id = record.user_id
    p.character_id = record.character_id
    p.character_name = record.name
    p.avatar = record.avatar
    p.level = view.level
    p.total_exp = view.total_exp
    p.balance_version = record.balance_version


def track_persistence_task(coroutine):
    task = asyncio.create_task(coroutine)
    pending_persistence_tasks.add(task)
    task.add_done_callback(pending_persistence_tasks.discard)
    return task


async def persist_exp_reward(player_id, user_id, character_id, event_id, amount):
    try:
        record = await character_store.award_exp(user_id, character_id, event_id, amount)
        current = players.get(player_id)
        if current and current.user_id == user_id and current.character_id == character_id:
            apply_character_record(current, record)
    except PersistenceError as exc:
        print(f'EXP persistence failed event={event_id!r}: {exc}', flush=True)


def award_monster_defeat(monster):
    now = time.monotonic()
    shares = contribution_shares(monster.contributions, monster.max_hp, now)
    reward_event_id = f'{server_instance_id}:{monster.id}:{monster.life_id}'
    for player_id, share in shares.items():
        p = players.get(player_id)
        if p is None:
            continue
        amount = scaled_award(balance.kill_award(p.level, monster.level), share)
        if amount <= 0:
            continue
        new_view = balance.apply_award(p.total_exp, amount)
        old_level = p.level
        p.level, p.total_exp = new_view.level, new_view.total_exp
        event('exp', p.x, p.y - 120, victim=p.id, amount=amount, level=p.level)
        if p.level > old_level:
            event('levelup', p.x, p.y - 145, victim=p.id, level=p.level)
        if p.user_id and p.character_id and character_store:
            track_persistence_task(
                persist_exp_reward(p.id, p.user_id, p.character_id, reward_event_id, amount)
            )


def perform_action(p: Guest, action: str, automated=False):
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
        if p.cool <= 0 and p.climb is None:
            p.vx, p.inv, p.cool = p.face * 650, .17, .5
            set_action(p, 'dash', .26)
        return
    if action == 'lock': return  # Lock targets never dictate damage on server.
    if action not in ATTACKS or p.cool > 0 or p.climb is not None or p.guard: return
    global shot_seq
    cooldown, duration, speed, damage, lifespan, pierce = ATTACKS[action]
    p.cool = cooldown
    set_action(p, action, duration)
    shot_seq += 1
    y = p.y - 84 - (3 if action == 'aoe' else 4 if action == 'break' else 0)
    shots.append(Shot(shot_seq, p.id, action, p.x + p.face * 52, y, p.face * speed, damage, lifespan, pierce, pve_only=automated))
    if action == 'aoe': event('cast', p.x, p.y - 34)


def server_auto_step(p: Guest):
    """Official opt-in auto-PvE. Never accepts coordinates, damage or targets from clients.
    Movement is computed using ordinary server speed and physics. Auto shots cannot hit players.
    """
    if not p.auto_mode or p.ws is None: return
    p.buttons = 0
    if p.dead > 0 or p.hp <= 0 or p.down > 0 or p.stun > 0 or p.broken > 0 or p.climb is not None:
        return
    eligible = [m for m in monsters.values() if m.dead <= 0 and m.hp > 0
                and abs(m.y - p.y) < 42 and abs(m.x - p.x) < 700]
    eligible.sort(key=lambda m: (abs(m.x - p.x), m.id))
    if not eligible: return
    m = eligible[0]
    # Do not cross a drop-off or chase mobs on a different platform.
    floor = next(((lo, hi) for lo, hi, top in GROUND if abs(top-p.y)<8 and lo+12<p.x<hi-12 and lo+12<m.x<hi-12), None)
    if floor is None: return
    gap = m.x - p.x
    distance = abs(gap)
    direction = 1 if gap >= 0 else -1
    if distance > 320:
        if floor[0]+45 < p.x+direction*7 < floor[1]-45:
            p.buttons = 2 if direction>0 else 1
        return
    if distance < 145:
        if floor[0]+45 < p.x-direction*7 < floor[1]-45:
            p.buttons = 1 if direction>0 else 2
        return
    # Stop and face the PvE target, not a client selected player target.
    p.face = direction
    if p.cool > 0 or p.guard: return
    if m.guard and m.broken <= 0:
        perform_action(p, 'break', automated=True)
    elif sum(1 for other in eligible if abs(other.x-m.x)<125) > 1:
        perform_action(p, 'aoe', automated=True)
    else:
        perform_action(p, 'attack', automated=True)


def update_guest(p: Guest, dt, tick_now):
    for v in ('cool', 'inv', 'stun', 'down', 'broken', 'climb_cd'):
        setattr(p, v, max(0, getattr(p, v) - dt))
    p.action_at += dt
    if tick_now - p.last_input > .55 and not p.auto_mode:
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
            p.ground = True
            event('respawn', p.x, p.y, victim=p.id)
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
    if near and axis and not p.guard and p.climb_cd <= 0:
        p.climb = near
        p.x, p.vx, p.vy, p.ground = near[0], 0, 0, False
    if p.climb is not None:
        cx, top, bottom = p.climb
        old_y = p.y
        p.y = clamp(p.y + axis * 175 * dt, top, bottom)
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
            p.vx = 205 * move
    elif p.action != 'dash' or p.action_at > .26:
        p.vx *= max(0, 1 - 12 * dt)
    if p.guard: p.vx = 0
    p.x += p.vx * dt
    if p.ground and move: p.walk_dist += abs(p.vx * dt)
    physics(p, dt)


def update_mob(m, dt):
    if m.dead > 0:
        m.dead -= dt
        if m.dead <= 0:
            m.hp, m.x, m.y, m.vx, m.vy, m.stun, m.down, m.broken, m.guard = m.max_hp, m.home, m.spawn_y, 0, 0, 0, 0, 0, False
            # Clamp the death timer: a negative value is truthy in JavaScript and hid respawned mobs.
            m.dead = 0.0
            m.ground = True
            m.life_id += 1
            m.contributions.clear()
        return
    m.stun = max(0, m.stun - dt)
    m.down = max(0, m.down - dt)
    m.broken = max(0, m.broken - dt)
    m.ai_cool = max(0, m.ai_cool - dt)
    m.decision = max(0, m.decision - dt)
    attack_timer_before = m.attack_time
    m.attack_time = max(0, m.attack_time - dt)
    same_level = [p for p in players.values() if p.ws is not None and p.dead <= 0 and abs(p.y - m.y) < 55 and abs(p.x - m.x) < 230]
    same_level.sort(key=lambda p: abs(p.x - m.x))
    near = same_level[0] if same_level else None
    if m.decision <= 0:
        m.decision = .7 + (secrets.randbelow(40) / 100)
        m.guard = bool(m.hum and near and m.broken <= 0 and m.down <= 0 and secrets.randbelow(100) < 30)
        if near: m.vx = (1 if near.x > m.x else -1) * (0 if m.guard else 55)
        else: m.vx = secrets.choice((-35, 0, 35))
    if m.down > 0 or m.stun > 0 or m.broken > 0: m.vx = 0
    elif near and m.ai_cool <= 0 and not m.guard and abs(m.x - near.x) < 97:
        m.ai_cool = 1.15 + secrets.randbelow(60)/100
        m.attack_time = .38
        m.vx = 0
    # Strike once on crossing the 0.10 s marker (robust to 30 Hz tick rounding).
    if attack_timer_before > .10 >= m.attack_time and near and abs(m.x - near.x) < 110:
        if near.guard and near.broken <= 0: event('block', near.x, near.y - 82, victim=near.id)
        else:
            hurt(near, 100 if m.hum else 70, near.x, near.y - 80, 'monster')
            if near.dead <= 0 and secrets.randbelow(100) < 18:
                near.down = 1.35
                if near.climb:
                    near.climb, near.climb_cd, near.vy = None, .6, 90
    if m.guard: m.vx = 0
    m.x += m.vx * dt
    physics(m, dt)
    if m.x > m.home + 260 or m.x < m.home - 260: m.vx = -m.vx
    if near: m.face = -1 if near.x < m.x else 1


def apply_shot(s, victim, is_mob):
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
        applied = hurt(victim, s.damage, s.x, s.y, s.kind)
        if is_mob and applied:
            contribution = victim.contributions.setdefault(s.owner, Contribution())
            contribution.damage += applied
            contribution.last_hit_at = time.monotonic()
            if victim.dead > 0:
                award_monster_defeat(victim)
        s.pierce -= 1
        return s.pierce <= 0
    if victim.guard and victim.broken <= 0:
        event('block', victim.x, victim.y - 82, victim=victim.id)
        return True
    if not is_mob and victim.inv > 0: return False
    dmg = int(s.damage * (0.78 if not is_mob else 1))
    applied = hurt(victim, dmg, s.x, s.y, s.kind)
    if is_mob and applied:
        contribution = victim.contributions.setdefault(s.owner, Contribution())
        contribution.damage += applied
        contribution.last_hit_at = time.monotonic()
        if victim.dead > 0:
            award_monster_defeat(victim)
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
        victims = [*monsters.values(), *((p for p in players.values() if p.ws is not None) if not s.pve_only else ())]
        victims = [v for v in victims if v.dead <= 0 and v.id != s.owner and abs(v.y - s.y - 78) < 95 and abs(v.x - s.x) < (60 if s.kind == 'aoe' else 36)]
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
    payload = {'id': a.id, 'x': round(a.x, 2), 'y': round(a.y, 2), 'vx': round(a.vx, 2), 'vy': round(a.vy, 2),
            'face': a.face, 'hp': a.hp, 'max': a.max_hp, 'guard': a.guard, 'down': round(a.down, 2), 'dead': round(a.dead, 2),
            'stun': round(a.stun, 2), 'inv': round(a.inv, 2), 'climb': bool(a.climb), 'frame': actor_frame(a, server_step), 'action': a.action, 'auto': isinstance(a, Guest) and a.auto_mode}
    if isinstance(a, Guest):
        payload['character'] = progression_json(a)
        payload['name'] = a.character_name or ('Guest-' + a.id[-4:].upper())
        payload['guest'] = a.user_id is None
    if isinstance(a, Monster):
        payload['level'] = a.level
    return payload


def snapshot():
    return json.dumps({'t': 'snapshot', 'tick': server_step, 'players': [{**actor_json(p), 'avatar': p.avatar} for p in players.values() if p.ws is not None],
                       'mobs': [{**actor_json(m), 'name': m.name, 'hum': m.hum} for m in monsters.values()],
                       'shots': [{'id': s.id, 'kind': s.kind, 'x': round(s.x, 1), 'y': round(s.y, 1), 'dir': 1 if s.vx >= 0 else -1} for s in shots],
                       'events': events[:80]}, separators=(',', ':'))


async def snapshot_sender(p, ws):
    """One outgoing writer per connection; slow background tabs cannot stall world ticks."""
    try:
        while p.ws is ws:
            snap = await p.snapshot_queue.get()
            await asyncio.wait_for(ws.send(snap), timeout=8)
    except asyncio.CancelledError:
        raise
    except (ConnectionClosed, asyncio.TimeoutError, OSError):
        try:
            await ws.close(code=1011, reason='Snapshot transport stalled')
        except (ConnectionClosed, OSError):
            pass


def publish_snapshot(snap):
    # Drop stale pictures of the world; preserve only the newest state for each tab.
    for p in list(players.values()):
        if p.ws is None:
            continue
        if p.snapshot_queue.full():
            try: p.snapshot_queue.get_nowait()
            except asyncio.QueueEmpty: pass
        try: p.snapshot_queue.put_nowait(snap)
        except asyncio.QueueFull: pass


async def game_loop():
    global server_step
    next_tick = time.monotonic()
    while True:
        next_tick += DT
        tick_now = time.monotonic()
        server_step += 1
        for p in list(players.values()):
            if p.ws is not None:
                if p.auto_mode: server_auto_step(p)
                update_guest(p, DT, tick_now)
        for m in monsters.values(): update_mob(m, DT)
        update_shots(DT)
        if server_step % 3 == 0:
            if any(p.ws is not None for p in players.values()): publish_snapshot(snapshot())
            events.clear()
        if server_step % 30 == 0:
            for guest_id, p in list(players.items()):
                if p.ws is not None and p.auth_expires_at and time.time() >= p.auth_expires_at:
                    track_persistence_task(p.ws.close(code=4001, reason='Access token expired'))
                if p.ws is None and p.offline_at and tick_now - p.offline_at > RESUME_GRACE_SECONDS:
                    players.pop(guest_id, None)
                    guest_tokens.pop(p.resume_token, None)
        await asyncio.sleep(max(0, next_tick - time.monotonic()))
        if time.monotonic() - next_tick > .4: next_tick = time.monotonic()

def strict_message(raw):
    try: m = json.loads(raw)
    except (json.JSONDecodeError, TypeError): return None
    if not isinstance(m, dict): return None
    return m


def check_rate(q, rate, window=1):
    now = time.monotonic()
    q.append(now)
    while q and q[0] < now - window: q.popleft()
    return len(q) <= rate


async def handle_connection(ws):
    guest_id = None
    p = None
    try:
        if ORIGINS and (ws.request.headers.get('Origin') not in ORIGINS):
            await ws.close(code=1008, reason='Origin not allowed');return
        raw = await asyncio.wait_for(ws.recv(), timeout=8)
        join = parse_join(strict_message(raw))
        if join is None:
            await ws.close(code=1008, reason='Invalid join');return

        identity = None
        record = None
        if join.authenticated:
            if auth_verifier is None or character_store is None:
                await ws.send(json.dumps({'t': 'error', 'message': 'เซิร์ฟเวอร์ยังไม่ได้ตั้งค่าระบบบัญชี'}))
                await ws.close(code=1013, reason='Account service unavailable');return
            try:
                identity = await auth_verifier.verify(join.access_token)
            except AuthenticationError:
                await ws.close(code=1008, reason='Invalid or expired account token');return
            try:
                record = await character_store.load_or_create_character(
                    identity.user_id,
                    join.avatar,
                    join.character_name or 'จอมยุทธ์',
                )
            except PersistenceError:
                await ws.send(json.dumps({'t': 'error', 'message': 'โหลดตัวละครถาวรไม่สำเร็จ กรุณาลองใหม่'}))
                await ws.close(code=1013, reason='Character persistence unavailable');return
            existing = next((item for item in players.values() if item.user_id == identity.user_id), None)
            if existing is not None:
                if existing.ws is not None:
                    await ws.close(code=1013, reason='Account already active');return
                p = existing
                p.offline_at = 0.0
                apply_character_record(p, record)
                p.auth_expires_at = identity.expires_at
        elif join.resume and join.resume in guest_tokens:
            old = players.get(guest_tokens[join.resume])
            if old is not None:
                if old.ws is not None:
                    await ws.close(code=1013, reason='Previous guest connection still active');return
                if old.user_id is not None or old.avatar != join.avatar:
                    await ws.close(code=1008, reason='Resume identity mismatch');return
                if old.offline_at and time.monotonic() - old.offline_at <= RESUME_GRACE_SECONDS:
                    p = old
                    p.offline_at = 0.0
        if sum(1 for a in players.values() if a.ws is not None) >= MAX_GUESTS:
            await ws.send(json.dumps({'t': 'error', 'message': 'ห้องเต็ม ลองใหม่ภายหลัง'}))
            await ws.close(code=1013);return
        if p is None:
            guest_id = 'g-' + secrets.token_hex(8)
            spawn_x = 175 + (sum(1 for a in players.values() if a.ws is not None) % 8) * 35
            p = Guest(id=guest_id, x=spawn_x, y=550, hp=1200, max_hp=1200, avatar=join.avatar)
            if record is not None:
                apply_character_record(p, record)
                p.auth_expires_at = identity.expires_at
            players[guest_id] = p
            guest_tokens[p.resume_token] = guest_id
        guest_id = p.id
        p.ws = ws
        p.last_input = time.monotonic()
        p.last_seq = -1
        p.buttons = 0
        p.guard = False
        p.vx = 0
        p.packet_times.clear()
        p.action_times.clear()
        p.snapshot_queue = asyncio.Queue(maxsize=1)
        name = p.character_name or ('Guest-' + guest_id[-4:].upper())
        features = ['auto', 'exp']
        if p.user_id:
            features.append('account')
        await ws.send(json.dumps({'t': 'welcome', 'id': guest_id, 'name': name,
                                  'tickRate': 30, 'snapshotRate': 10, 'guest': p.user_id is None,
                                  'resume': p.resume_token, 'features': features,
                                  'character': progression_json(p)}))
        p.sender_task = asyncio.create_task(snapshot_sender(p, ws))
        event('join', p.x, p.y, victim=p.id)
        async for raw in ws:
            m = strict_message(raw)
            if not m or not check_rate(p.packet_times, 35):
                await ws.close(code=1008, reason='Bad message / rate limit');break
            if m.get('t') == 'auto':
                if set(m.keys()) != {'t','enabled'} or type(m.get('enabled')) is not bool:
                    await ws.close(code=1008, reason='Invalid auto toggle');break
                if not check_rate(p.action_times, 6):
                    await ws.close(code=1008, reason='Auto toggle rate limit');break
                p.auto_mode = m['enabled']
                p.buttons = 0
                p.guard = False
                continue
            if m.get('t') == 'auth_refresh':
                token = parse_auth_refresh(m)
                if token is None or p.user_id is None or auth_verifier is None:
                    await ws.close(code=1008, reason='Invalid auth refresh');break
                try:
                    refreshed = await auth_verifier.verify(token)
                except AuthenticationError:
                    await ws.close(code=4001, reason='Account token refresh failed');break
                if refreshed.user_id != p.user_id:
                    await ws.close(code=1008, reason='Account identity changed');break
                p.auth_expires_at = refreshed.expires_at
                continue
            parsed_input = parse_input(m, p.last_seq)
            if parsed_input is None:
                await ws.close(code=1008, reason='Invalid input payload');break
            seq, buttons, pressed = parsed_input
            if pressed and not check_rate(p.action_times, 12):
                await ws.close(code=1008, reason='Action rate limit');break
            p.last_seq = seq
            if p.auto_mode and (buttons or pressed):
                p.auto_mode = False  # Manual override ends AUTO, still runs validated inputs.
            if not p.auto_mode:
                p.buttons = buttons
            p.last_input = time.monotonic()
            for action in pressed: perform_action(p, action)
    except asyncio.TimeoutError:
        print('Guest handshake timed out', flush=True)
    except ConnectionClosed as exc:
        print(f'Guest connection closed code={exc.code} reason={exc.reason!r}', flush=True)
    finally:
        if guest_id and players.get(guest_id) and players[guest_id].ws is ws:
            p = players[guest_id]
            p.ws = None
            p.auto_mode = False  # A disconnected Guest cannot farm in background.
            p.offline_at = time.monotonic()
            p.buttons = 0
            p.guard = False
            p.vx = 0
            if p.sender_task:
                p.sender_task.cancel()
                p.sender_task = None
            event('leave', p.x, p.y, victim=guest_id)
            shots[:] = [shot for shot in shots if shot.owner != guest_id]

def process_request(connection, request):
    if request.path == '/healthz':
        return connection.respond(HTTPStatus.OK, 'wuxia-online ok\n')
    if request.path != '/ws':
        return connection.respond(HTTPStatus.NOT_FOUND, 'Use /ws for WebSockets\n')
    return None


async def main():
    spawn_mobs()
    async with serve(handle_connection, HOST, PORT, max_size=16384, max_queue=16, ping_interval=25, ping_timeout=120, process_request=process_request, compression=None):
        account_mode = 'enabled' if auth_verifier and character_store else 'guest-only'
        print(f'WUXIA online server ready on {HOST}:{PORT} | limit {MAX_GUESTS} | accounts {account_mode}', flush=True)
        await game_loop()

if __name__ == '__main__':
    asyncio.run(main())
