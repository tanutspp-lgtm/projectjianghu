"""Scoped V67 navigation: contoured floor, real rope intersections, directed jumps.
Movement uses ordinary buttons/actions; combat/goal selection remains farm_auto.
"""
from farm_auto_v80bu import Navigation

def ground_y(m,x):
    for (a,b),(c,d) in zip(m['profile'],m['profile'][1:]):
        if a<=x<=c:
            t=(x-a)/(c-a)
            return b+(d-b)*t*t*(3-2*t)
    return m['profile'][-1][1]

class LateNavigation(Navigation):
    def __init__(self,m):
        self.map=m
        super().__init__([(p['x'],p['x2'],p['y']) for p in m['platforms']],[(c['x'],c['top'],c['bottom']) for c in m['climbs']])
        for t in self.ground:t['y']=ground_y(m,t['x'])
        self.graph=[[] for _ in self.platforms]
        # Include actual intermediate crossing footholds, plus the sloped floor.
        for k,c in enumerate(self.climbs):
            ends=[i for i,p in enumerate(self.platforms) if p['x']+12<=c['x']<=p['x2']-12 and c['top']-2<=(ground_y(m,c['x']) if i==0 else p['y'])<=c['bottom']+2]
            for a in ends:
                for b in ends:
                    if a!=b:self.graph[a].append(dict(to=b,climb=k,cost=1+abs(self.platforms[a]['y']-self.platforms[b]['y'])/175))
        for e in m['navJumps']:
            k=len(self.climbs)
            # Cost anchor only; never registered as a physical climb.
            self.climbs.append(dict(x=e['launch'],top=0,bottom=0,virtual=True))
            self.graph[e['from']].append(dict(e,climb=k,cost=2,kind='jump'))
    def platform_at(self,p):
        if p.climb or not p.ground:return -1
        if abs(p.y-ground_y(self.map,p.x))<17:return 0
        return super().platform_at(p)
    def choose(self,p,state,t,monsters,allow_cast=True):
        buttons,actions=super().choose(p,state,t,monsters,allow_cast)
        leg=state.leg
        if not leg or leg.get('kind')!='jump' or p.climb or p.dead>0 or p.hp<=0 or p.stun>0 or p.down>0 or state.combat_target_id or any(a!='jump' for a in actions):return buttons,actions
        at=self.platform_at(p)
        if at==leg['to']:state.leg=None;return buttons,actions
        if at==leg['from']:
            direction=self.approach(p.x,leg['launch'],3)
            if direction:return direction,[]
            if t-state.last_jump>.8:
                state.last_jump=t
                return (2 if leg['direction']>0 else 1),['jump']
            return 0,[]
        if at<0:return self.approach(p.x,leg['land'],4),[]
        return buttons,actions
