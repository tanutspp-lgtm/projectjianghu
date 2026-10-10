"""WUXIA Flute Arena guest-only authoritative arena server.
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
from typing import Optional

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

PORT = int(os.environ.get('PORT', '8765'))
HOST = os.environ.get('HOST', '0.0.0.0')
ORIGINS = tuple(s.strip() for s in os.environ.get('ALLOWED_ORIGINS', '').split(',') if s.strip())
MAX_GUESTS = int(os.environ.get('MAX_GUESTS', '35'))
WORLD_W = 2060
DT = 1.0 / 30.0
GROUND = [(0, 2060, 550), (170, 850, 390), (1020, 1770, 390), (410, 1070, 235), (1210, 1970, 235)]
CLIMBS = ((510, 235, 550), (1170, 235, 550), (1590, 235, 550))
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

players: dict[str, Guest] = {}
monsters: dict[str, Monster] = {}
shots: list[Shot] = []
events: list[dict] = []
shot_seq = 0
server_step = 0


def spawn_mobs():
    specs = [('m1', 'ฝึกยุทธ์', 740, 390, 1100, True), ('m2', 'หมาป่า', 380, 550, 450, False), ('m3', 'หมาป่า', 1340, 390, 450, False), ('m4', 'หมาป่า', 1630, 235, 450, False), ('m5', 'จอมยุทธ์คู่ซ้อม', 1520, 550, 1100, True)]
    for mid, name, x, y, hp, hum in specs:
        monsters[mid] = Monster(id=mid, name=name, x=x, y=y, hp=hp, max_hp=hp, home=x, spawn_y=y, hum=hum, ai_cool=0.5)


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
    if victim.dead > 0 or victim.inv > 0: return
    if isinstance(victim, Guest) and victim.guard and victim.broken <= 0:
        event('block', victim.x, victim.y - 82, victim=victim.id)
        return
    victim.hp = max(0, victim.hp - damage)
    victim.stun = 0.25
    victim.inv = .42 if isinstance(victim, Guest) else 0
    event('hit', victim.x, victim.y - 78, victim=victim.id, damage=damage, kind=kind)
    if victim.hp <= 0 and victim.dead <= 0:
        victim.dead = 3.2 if isinstance(victim, Monster) else 2.5
        victim.guard = False
        event('defeat', victim.x, victim.y - 80, victim=victim.id)


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
    shots.append(Shot(shot_seq, p.id, action, p.x + p.face * 52, y, p.face * speed, damage, lifespan, pierce))
    if action == 'aoe': event('cast', p.x, p.y - 34)


def update_guest(p: Guest, dt, tick_now):
    for v in ('cool', 'inv', 'stun', 'down', 'broken', 'climb_cd'):
        setattr(p, v, max(0, getattr(p, v) - dt))
    p.action_at += dt
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
            m.ground = True
        return
    m.stun = max(0, m.stun - dt)
    m.down = max(0, m.down - dt)
    m.broken = max(0, m.broken - dt)
    m.ai_cool = max(0, m.ai_cool - dt)
    m.decision = max(0, m.decision - dt)
    attack_timer_before = m.attack_time
    m.attack_time = max(0, m.attack_time - dt)
    same_level = [p for p in players.values() if p.dead <= 0 and abs(p.y - m.y) < 55 and abs(p.x - m.x) < 230]
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
        hurt(victim, s.damage, s.x, s.y, s.kind)
        s.pierce -= 1
        return s.pierce <= 0
    if victim.guard and victim.broken <= 0:
        event('block', victim.x, victim.y - 82, victim=victim.id)
        return True
    if not is_mob and victim.inv > 0: return False
    dmg = int(s.damage * (0.78 if not is_mob else 1))
    hurt(victim, dmg, s.x, s.y, s.kind)
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
        victims = [*monsters.values(), *players.values()]
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
    return {'id': a.id, 'x': round(a.x, 2), 'y': round(a.y, 2), 'vx': round(a.vx, 2), 'vy': round(a.vy, 2),
            'face': a.face, 'hp': a.hp, 'max': a.max_hp, 'guard': a.guard, 'down': round(a.down, 2), 'dead': round(a.dead, 2),
            'stun': round(a.stun, 2), 'inv': round(a.inv, 2), 'climb': bool(a.climb), 'frame': actor_frame(a, server_step), 'action': a.action}


def snapshot():
    return json.dumps({'t': 'snapshot', 'tick': server_step, 'players': [{**actor_json(p), 'avatar': p.avatar} for p in players.values()],
                       'mobs': [{**actor_json(m), 'name': m.name, 'hum': m.hum} for m in monsters.values()],
                       'shots': [{'id': s.id, 'kind': s.kind, 'x': round(s.x, 1), 'y': round(s.y, 1), 'dir': 1 if s.vx >= 0 else -1} for s in shots],
                       'events': events[:80]}, separators=(',', ':'))


async def game_loop():
    global server_step
    next_tick = time.monotonic()
    while True:
        next_tick += DT
        tick_now = time.monotonic()
        server_step += 1
        for p in list(players.values()): update_guest(p, DT, tick_now)
        for m in monsters.values(): update_mob(m, DT)
        update_shots(DT)
        if server_step % 3 == 0 and players:
            snap = snapshot()
            await asyncio.gather(*(p.ws.send(snap) for p in list(players.values())), return_exceptions=True)
            events.clear()
        elif server_step % 3 == 0: events.clear()
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
    try:
        if ORIGINS and (ws.request.headers.get('Origin') not in ORIGINS):
            await ws.close(code=1008, reason='Origin not allowed');return
        raw = await asyncio.wait_for(ws.recv(), timeout=8)
        hello = strict_message(raw)
        if not hello or set(hello.keys()) != {'t', 'avatar'} or hello.get('t') != 'join' or not valid_avatar(hello.get('avatar')):
            await ws.close(code=1008, reason='Invalid guest join');return
        if len(players) >= MAX_GUESTS:
            await ws.send(json.dumps({'t': 'error', 'message': 'ห้องเต็ม ลองใหม่ภายหลัง'}));await ws.close(code=1013);return
        guest_id = 'g-' + secrets.token_hex(8)
        name = 'Guest-' + guest_id[-4:].upper()
        # All legal spawn points are server-defined, never supplied by client.
        spawn_x = 175 + (len(players) % 8) * 35
        p = Guest(id=guest_id, x=spawn_x, y=550, hp=1200, max_hp=1200, avatar=hello['avatar'], ws=ws)
        players[guest_id] = p
        await ws.send(json.dumps({'t': 'welcome', 'id': guest_id, 'name': name, 'tickRate': 30, 'snapshotRate': 10, 'guest': True}))
        event('join', p.x, p.y, victim=p.id)
        async for raw in ws:
            m = strict_message(raw)
            if not m or m.get('t') != 'input' or set(m.keys()) != {'t', 'seq', 'buttons', 'pressed'}:
                await ws.close(code=1008, reason='Invalid input payload');break
            if not check_rate(p.packet_times, 35):
                await ws.close(code=1008, reason='Packet rate limit');break
            seq, buttons, pressed = m.get('seq'), m.get('buttons'), m.get('pressed')
            if type(seq) is not int or seq <= p.last_seq or seq < 0 or seq > 2**53 or type(buttons) is not int or buttons < 0 or buttons & ~ALLOWED_BUTTONS:
                await ws.close(code=1008, reason='Invalid buttons/sequence');break
            if not isinstance(pressed, list) or len(pressed) > 4 or any(a not in ACTION_NAMES for a in pressed) or len(set(pressed)) != len(pressed):
                await ws.close(code=1008, reason='Invalid action');break
            if pressed and not check_rate(p.action_times, 12):
                await ws.close(code=1008, reason='Action rate limit');break
            p.last_seq = seq
            p.buttons = buttons
            p.last_input = time.monotonic()
            # Only validated intent is accepted; server owns all results.
            for action in pressed: perform_action(p, action)
    except (asyncio.TimeoutError, ConnectionClosed):
        pass
    finally:
        if guest_id and players.get(guest_id) and players[guest_id].ws is ws:
            p = players.pop(guest_id)
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
    async with serve(handle_connection, HOST, PORT, max_size=2048, max_queue=16, ping_interval=20, ping_timeout=20, process_request=process_request, compression=None):
        print(f'WUXIA online server ready on {HOST}:{PORT} | guest limit {MAX_GUESTS}', flush=True)
        await game_loop()

if __name__ == '__main__':
    asyncio.run(main())
