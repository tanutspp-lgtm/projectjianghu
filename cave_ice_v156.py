"""Authoritative falling cave ice. No client hit reports or clocks are trusted."""
import json
import math
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name('cave_ice_v156.json').read_text())
FEATURE = CONFIG['feature']
SITES = CONFIG['maps']

def frame(site, time):
    g, v = CONFIG['gravity'], CONFIG['initialVelocity']
    travel = site['floorY'] - site['ceilingY'] - site['length']
    fall = (math.sqrt(v*v+2*g*travel)-v)/g
    phase = (time+site['offset']) % site['period']
    begin = CONFIG['hangSeconds']+CONFIG['warningSeconds']
    return phase, begin, fall

def sweep(site, time, dt):
    phase, begin, fall = frame(site, time)
    a, b = max(begin, phase-max(0, min(.1, dt))), min(begin+fall, phase)
    if b <= a:
        return None
    def y(t):
        return site['ceilingY']+CONFIG['initialVelocity']*t+.5*CONFIG['gravity']*t*t
    return {'cycle': math.floor((time+site['offset'])/site['period']),
            'top': y(a-begin), 'bottom': y(b-begin)+site['length'],
            'halfWidth': max(6, site['length']*.22)}

def tick_player(p, now, dt, emit):
    """Called after authoritative movement; emit is the existing world event writer."""
    if p.room not in SITES:
        if hasattr(p, 'ice_previous_pose'):
            p.ice_previous_pose = None
        return None
    prev = getattr(p, 'ice_previous_pose', None)
    p.ice_previous_pose = (p.room, p.x, p.y, now)
    if getattr(p, 'ice_recovering', False) and p.down > 0:
        p.ice_safe_until = max(p.ice_safe_until, now+p.down+CONFIG['recoverySeconds'])
    elif getattr(p, 'ice_recovering', False):
        p.ice_recovering = False
    if p.dead > 0 or p.hp <= 0 or p.inv > 0 or p.down > 0 or now < getattr(p, 'ice_safe_until', 0):
        return None
    ox, oy = (prev[1], prev[2]) if prev and prev[0] == p.room and now-prev[3] < .15 else (p.x, p.y)
    if not hasattr(p, 'ice_hits'):
        p.ice_hits = {}
    for site in SITES[p.room]:
        hit = sweep(site, now, dt)
        key = (p.room, site['id'])
        if (not hit or p.ice_hits.get(key) == hit['cycle'] or
                max(ox, p.x)+18 < site['x']-hit['halfWidth'] or
                min(ox, p.x)-18 > site['x']+hit['halfWidth'] or
                max(oy, p.y) < hit['top'] or min(oy, p.y)-123.26 > hit['bottom']):
            continue
        p.ice_hits[key] = hit['cycle']
        damage = p.max_hp*CONFIG['damageMaxHp']
        p.hp = max(0, p.hp-damage)  # fixed MaxHP fraction: bypass DEF, guard and qi shield
        p.down = CONFIG['downSeconds']
        p.ice_safe_until = now+p.down+CONFIG['recoverySeconds']
        p.ice_recovering = True
        p.guard = False
        p.stun = 0
        p.kb_time = 0
        p.vx = 0
        p.action, p.action_at, p.action_duration = 'hit', 0, p.down
        if p.climb is not None:
            p.climb, p.climb_cd, p.ground, p.vy = None, max(p.climb_cd, .5), False, 90
        p.last_damage_at = now
        emit('hit', p.x, p.y-78, victim=p.id, damage=damage, kind='cave_ice', critical=False)
        if p.hp <= 0:
            p.dead = 2.5
            emit('defeat', p.x, p.y-80, victim=p.id)
        return damage
    return None
