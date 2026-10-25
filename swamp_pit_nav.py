"""Server-side local recovery route; emits inputs, never writes actor position.
Call at the existing AUTO 10 Hz cadence, before the general route chooser.
Coordinates come from assembly geometry.json; offset_y permits game-world shifts.
"""
from dataclasses import dataclass
import hashlib
import json
import math

LEFT, RIGHT, UP = 1, 2, 4

@dataclass(frozen=True)
class Decision:
    buttons: int
    actions: tuple = ()
    phase: str = ''
    side: str = ''

@dataclass
class Route:
    side: str
    phase: str
    progress_at: float
    last_x: float
    last_y: float

class PitNavigator:
    def __init__(self, geometry, offset_y=0):
        self.offset_y = offset_y
        self.pit = geometry['pit']
        self.floor = self.pit['bottomY'] + offset_y
        self.bank = self.floor - self.pit['depth']
        self.routes = {}  # Per actor, never shared transient route state.
        self.ropes = {}
        center = (self.pit['left'] + self.pit['right']) / 2
        for side in ('left', 'right'):
            candidates = []
            for c in geometry['climbs']:
                if abs(c['bottom'] - self.pit['bottomY']) > 1:
                    continue
                if (c['x'] < center) != (side == 'left'):
                    continue
                for p in geometry['platforms']:
                    if p['x'] + 28 < c['x'] < p['x2'] - 28 and abs(p['y'] - c['top']) < 1:
                        candidates.append(c)
            if not candidates:
                raise ValueError('Missing supported recovery rope: ' + side)
            c = min(candidates, key=lambda c: c['bottom'] - c['top'])
            self.ropes[side] = (c['x'], c['top'] + offset_y, c['bottom'] + offset_y)
        self.feature = 'swamp-pit-nav-v1-' + hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest()[:12]

    def reset(self, actor_id):
        self.routes.pop(actor_id, None)

    @staticmethod
    def toward(x, target, tolerance=8):
        return LEFT if x > target + tolerance else RIGHT if x < target - tolerance else 0

    def choose(self, actor, goal, now):
        """goal is a server-owned (x,y) destination. None => normal navigation.
        Return None to delegate combat/navigation; otherwise hold returned buttons.
        Caller resets on AUTO disable, map change, logout and death.
        """
        key = actor.id
        if not all(math.isfinite(v) for v in (actor.x, actor.y, now)):
            self.reset(key)
            return Decision(0, phase='invalid_position')
        if getattr(actor, 'dead', 0) > 0:
            self.reset(key)
            return None
        if any(getattr(actor, n, 0) > 0 for n in ('stun', 'down', 'kb_time', 'broken')):
            return Decision(0, phase='interrupted')
        if goal is None or len(goal) != 2 or not all(math.isfinite(v) for v in goal):
            self.reset(key)
            return None
        gx, gy = goal
        left, right = self.pit['left'], self.pit['right']
        route = self.routes.get(key)
        # Hand control back only after landing beyond the rounded pit rim.
        if actor.ground and actor.y <= self.bank + 3 and (actor.x < left - 28 or actor.x > right + 28):
            self.reset(key)
            return None
        if route is None:
            # A destination in the bottom of the pit remains a normal combat goal.
            if left < gx < right and gy > self.bank + 20:
                return None
            if not (left - 8 <= actor.x <= right + 8 and actor.y > self.bank + 5):
                return None
            if gx <= left:
                side = 'left'
            elif gx >= right:
                side = 'right'
            else:
                side = min(self.ropes, key=lambda s: abs(actor.x - self.ropes[s][0]))
            route = Route(side, 'approach', now, actor.x, actor.y)
            self.routes[key] = route
        rx, top, bottom = self.ropes[route.side]
        if abs(actor.x - route.last_x) + abs(actor.y - route.last_y) > 3:
            route.progress_at, route.last_x, route.last_y = now, actor.x, actor.y
        if now - route.progress_at > 3:
            # Re-evaluate approach after displacement; do not teleport or auto-jump.
            route.phase = 'approach'
            route.progress_at = now
        if actor.climb is not None:
            if abs(actor.climb[0] - rx) > 1:
                # A pre-existing legitimate rope has control; let normal nav finish.
                self.reset(key)
                return None
            route.phase = 'climb'
            return Decision(UP, phase='climb', side=route.side)
        if actor.ground and abs(actor.y - top) < 6:
            route.phase = 'leave_ledge'
        elif actor.ground and actor.y >= self.floor - 6:
            route.phase = 'approach'
        if route.phase == 'leave_ledge':
            # Both ledges sit 70px ABOVE the bank. Walk off outward and land;
            # a jump is unnecessary. Never walk back into the pit at rope top.
            dest = left - 60 if route.side == 'left' else right + 60
            return Decision(self.toward(actor.x, dest, 3), phase='leave_ledge', side=route.side)
        if not actor.ground:
            return Decision(0, phase='wait_landing', side=route.side)
        buttons = self.toward(actor.x, rx, 17)
        if buttons:
            return Decision(buttons, phase='approach', side=route.side)
        if getattr(actor, 'climb_cd', 0) > 0:
            return Decision(0, phase='wait_rope_cooldown', side=route.side)
        return Decision(UP, phase='grab_rope', side=route.side)

class SwampNavigation:
    """Adapter for existing farm_nav_for(room).choose interface.
    base remains the existing farm_auto.Navigation instance. goal_provider MUST
    return an authoritative destination from that navigation's actual goal state.
    No client-supplied goal or arbitrary monster chase is introduced here.
    """
    def __init__(self, base, recovery, goal_provider):
        self.base, self.recovery, self.goal_provider = base, recovery, goal_provider

    def __getattr__(self, name):
        return getattr(self.base, name)

    def choose(self, actor, state, now, monsters, allow_cast=True):
        goal = self.goal_provider(actor, state)
        decision = self.recovery.choose(actor, goal, now)
        if decision is not None:
            return decision.buttons, list(decision.actions)
        return self.base.choose(actor, state, now, monsters, allow_cast=allow_cast)

class MultiPitNavigator:
    """One map may contain several distinct mud depressions."""
    def __init__(self, geometry, offset_y=0):
        self.parts = [PitNavigator({**geometry, 'pit':p}, offset_y) for p in geometry['pits']]
        self.offset_y = offset_y
        self.active = {}

    def reset(self, actor_id):
        self.active.pop(actor_id, None)
        for nav in self.parts:
            nav.reset(actor_id)

    def choose(self, actor, goal, now):
        if actor.id in self.active:
            nav = self.parts[self.active[actor.id]]
            decision = nav.choose(actor, goal, now)
            if decision is None:
                self.reset(actor.id)
            return decision
        for i,nav in enumerate(self.parts):
            p = nav.pit
            if p['left']-8 <= actor.x <= p['right']+8:
                decision = nav.choose(actor, goal, now)
                if decision is not None:
                    self.active[actor.id] = i
                return decision
        return None
