"""Server-owned AUTO: independent 120s tile destination + local monster combat.
No client coordinates/targets/path inputs. Ground 25%, floating 75% when both
exist; recompute movement route after knockback, not a new destination.
"""
from dataclasses import dataclass, field
import heapq
import math
import random

DESTINATION_SECONDS=120.0
GROUND_WEIGHT=0.25
TILE_WIDTH=64
EDGE=32

@dataclass
class State:
    enabled:bool=False
    goal:dict|None=None
    goal_due:float=0.0
    route_seed:float=field(default_factory=lambda:random.random()*999)
    patrol_x:float|None=None
    patrol_due:float=0.0
    last_attack:float=-1e9
    last_jump:float=-1e9
    next_step:float=0.0
    leg:dict|None=None
    changes:int=0
    unreachable:int=0
    combat_target_id:str|None=None
    combat_lock_until:float=0.0

class Navigation:
    def __init__(self,platforms,climbs):
        self.platforms=[dict(x=float(p[0]),x2=float(p[1]),y=float(p[2])) for p in platforms]
        self.climbs=[dict(x=float(c[0]),top=float(c[1]),bottom=float(c[2])) for c in climbs]
        self.ground=[];self.upper=[]
        valid=[p for p in self.platforms if p['x2']-p['x']>=54]
        bottom=max((p['y'] for p in valid),default=None)
        for i,p in enumerate(self.platforms):
            if p not in valid:continue
            guard=min(EDGE,(p['x2']-p['x'])/3)
            lo=p['x']+guard;hi=p['x2']-guard
            count=max(1,math.ceil((hi-lo)/TILE_WIDTH))
            for t in range(count):
                tile=dict(platform=i,x=lo+(t+.5)*(hi-lo)/count,y=p['y'])
                (self.ground if abs(p['y']-bottom)<14 else self.upper).append(tile)
        self.graph=[[] for _ in self.platforms]
        for k,c in enumerate(self.climbs):
            ends=[i for i,p in enumerate(self.platforms) if p['x']+12<=c['x']<=p['x2']-12 and c['top']-8<=p['y']<=c['bottom']+8]
            for a in range(len(ends)):
                for b in range(a+1,len(ends)):
                    i,j=ends[a],ends[b]
                    cost=1+abs(self.platforms[i]['y']-self.platforms[j]['y'])/175
                    self.graph[i].append(dict(to=j,climb=k,cost=cost))
                    self.graph[j].append(dict(to=i,climb=k,cost=cost))

    def platform_at(self,p):
        if p.climb or not p.ground:return -1
        best=-1;diff=float('inf')
        for i,s in enumerate(self.platforms):
            if s['x']+5<=p.x<=s['x2']-5:
                d=abs(s['y']-p.y)
                if d<17 and d<diff:best=i;diff=d
        return best

    def connected_component(self,start):
        if start<0:return set(range(len(self.platforms)))
        seen={start};todo=[start]
        while todo:
            for link in self.graph[todo.pop()]:
                if link['to'] not in seen:seen.add(link['to']);todo.append(link['to'])
        return seen

    def pick_goal(self,at=-1,avoid_platform=None,avoid_x=None):
        viable=self.connected_component(at)
        ground=[t for t in self.ground if t['platform'] in viable]
        upper=[t for t in self.upper if t['platform'] in viable]
        # On arrival draw another STANDABLE reachable tile, not a tiny patrol
        # step around the same spot. Keep the 25/75 ground/upper probability
        # whenever both pools have eligible distant candidates.
        if avoid_platform is not None and avoid_x is not None:
            far=lambda tiles:[t for t in tiles if t['platform']!=avoid_platform or
                              abs(t['x']-avoid_x)>=96]
            far_ground,far_upper=far(ground),far(upper)
            if far_ground or far_upper:ground,upper=far_ground,far_upper
        if ground and upper:return dict(random.choice(ground if random.random()<GROUND_WEIGHT else upper))
        pool=ground or upper
        return dict(random.choice(pool)) if pool else None

    def route_next(self,start,goal,seed):
        if start<0 or goal<0 or start==goal:return None
        best={start:0.0};prior={};pq=[(0.0,start)];visited=set()
        while pq:
            cost,at=heapq.heappop(pq)
            if at in visited:continue
            visited.add(at)
            if at==goal:break
            for link in self.graph[at]:
                c=self.climbs[link['climb']]
                dx=abs((self.platforms[at]['x']+self.platforms[at]['x2'])/2-c['x'])
                bias=(math.sin(seed*13.31+link['climb']*7.4+at*4.1)+1)*.12
                nc=cost+link['cost']+dx/260+bias
                if nc<best.get(link['to'],float('inf')):
                    best[link['to']]=nc;prior[link['to']]=dict(link,**{'from':at})
                    heapq.heappush(pq,(nc,link['to']))
        if goal not in prior:return None
        cur=goal
        while prior[cur]['from']!=start:cur=prior[cur]['from']
        return prior[cur]

    @staticmethod
    def approach(x,to,margin=17):
        return 2 if x<to-margin else 1 if x>to+margin else 0

    def choose(self,p,state,t,monsters):
        if not state.enabled:return 0,[]
        if state.goal is None or t>=state.goal_due:
            state.goal=self.pick_goal(self.platform_at(p));state.goal_due=t+DESTINATION_SECONDS
            state.leg=None;state.patrol_x=None;state.patrol_due=0
            state.route_seed=random.random()*999;state.changes+=1
        if p.dead>0 or p.hp<=0:return 0,[]
        at=self.platform_at(p)
        # An arrived bot commits to a fresh tile even if monsters are standing
        # on its destination. Combat still uses the ordinary legal cooldowns.
        if at>=0 and state.goal is not None and at==state.goal['platform'] and abs(p.x-state.goal['x'])<=27:
            state.goal=self.pick_goal(at,avoid_platform=at,avoid_x=p.x)
            state.goal_due=t+DESTINATION_SECONDS
            state.leg=None;state.patrol_x=None;state.patrol_due=0
            state.route_seed=random.random()*999;state.changes+=1
        # Prefer legitimate same-platform targets encountered along the travel route.
        if at>=0 and p.stun<=0 and p.down<=0 and not p.climb:
            nearby=[m for m in monsters.values() if m.dead<=0 and m.hp>0 and abs(m.y-p.y)<55 and
                     abs(m.x-p.x)<305 and self.platform_at(m)==at]
            if nearby:
                # Hold target briefly: crowded mobs must not make AUTO flip sides every 33ms.
                m=next((mob for mob in nearby if mob.id==state.combat_target_id),None) if t<state.combat_lock_until else None
                if m is None:
                    m=min(nearby,key=lambda mob:abs(mob.x-p.x))
                    state.combat_target_id=m.id
                state.combat_lock_until=t+0.75
                dx=m.x-p.x;distance=abs(dx)
                if distance>265:return (2 if dx>0 else 1),[]
                # No backwards movement in melee range: that caused a deterministic
                # left/right ping-pong at the attack threshold, not real lag.
                # Ignore tiny target-side oscillations while monsters overlap.
                if abs(dx)>24:p.face=1 if dx>0 else -1
                if t-state.last_attack>=.37 and p.cool<=0 and p.sp>=0:
                    state.last_attack=t
                    return 0,['attack']
                return 0,[]
            state.combat_target_id=None
        goal=state.goal
        if goal is None:return 0,[]
        if p.climb:
            leg=state.leg
            if not leg:return 0,[]
            target=self.platforms[leg['to']];c=self.climbs[leg['climb']]
            # Intermediate landing: jump sideways before passing the platform.
            intermediate=abs(target['y']-c['top'])>10 and abs(target['y']-c['bottom'])>10
            climb_up=target['y']<p.y
            # Mid-rope platforms require a real jump-off in BOTH directions.
            # When descending jump ABOVE the platform top; ascending jump BELOW it.
            # The old logic only handled climbing up, so descending bots bounced
            # top->bottom->top forever while trying to reach the middle tier.
            takeoff=(target['y']+32<=p.y<=target['y']+58) if climb_up else (target['y']-65<=p.y<=target['y']-30)
            if intermediate and takeoff and t-state.last_jump>1.25:
                state.last_jump=t
                side=1 if target['x2']-c['x']>=c['x']-target['x'] else -1
                p.face=side
                return 0,['jump']
            return (4 if climb_up else 8),[]
        if at<0:return 0,[]
        if state.leg and state.leg['to']==at:state.leg=None
        if at==goal['platform']:
            state.leg=None
            return self.approach(p.x,goal['x']),[]
        if not state.leg or state.leg['from']!=at:
            state.leg=self.route_next(at,goal['platform'],state.route_seed)
            if not state.leg:
                state.unreachable+=1
                # Real obstacle/path failure, not a monster-density re-evaluation.
                # Avoid futile twitching; wait for next 120s goal.
                return 0,[]
        c=self.climbs[state.leg['climb']]
        direction=self.approach(p.x,c['x'])
        if direction:return direction,[]
        target=self.platforms[state.leg['to']]
        return (4 if target['y']<p.y else 8),[]
