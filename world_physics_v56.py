"""V56 map collision only. The existing input, combat and tick schedulers own actors."""
import math

def ground_y(m,x):
    if 'profile' not in m:return None
    y=550
    smooth=lambda t:t*t*(3-2*t)
    for (a,b),(c,d) in zip(m['profile'],m['profile'][1:]):
        if a<=x<=c:
            y=b+(d-b)*smooth((x-a)/(c-a));break
    for p in m['pits']:
        if p['left']<=x<=p['right']:
            t=(x-p['left'])/50 if x<p['left']+50 else (p['right']-x)/50 if x>p['right']-50 else 1
            y+=p['depth']*smooth(t)
    return y

def step(p,dt,m):
    p.x=max(27,min(m['worldWidth']-27,p.x))
    if p.climb is not None:return
    old_x=p.x-p.vx*dt;old_y=p.y;was_ground=p.ground
    gy=ground_y(m,p.x);previous_ground=ground_y(m,old_x)
    if m['kind']=='swamp':
        in_pit=any(q['left']<=old_x<=q['right'] for q in m['pits'])
        follow_slope=was_ground and abs(old_y-previous_ground)<3 and not in_pit
        dx=p.x-old_x
        if not follow_slope and abs(dx)>1e-9:
            safe=old_x
            for i in range(1,math.ceil(abs(dx)/2)+1):
                probe=old_x+dx*i/math.ceil(abs(dx)/2)
                if old_y>ground_y(m,probe)+.01:
                    blocked=probe
                    for _ in range(24):
                        middle=(safe+blocked)/2
                        if old_y>ground_y(m,middle)+.01:blocked=middle
                        else:safe=middle
                    p.x=safe;p.vx=0;gy=ground_y(m,p.x)
                    break
                safe=probe
    solids=m.get('solids',())
    hits=[r for r in solids if p.y>r['y']+.001 and p.y-123.26<r['y']+r['h']-.001 and p.x+20>r['x'] and p.x-20<r['x']+r['w']]
    if hits:
        if p.vx>0:p.x=min(r['x']-20 for r in hits)
        elif p.vx<0:p.x=max(r['x']+r['w']+20 for r in hits)
        p.vx=0
    p.vy+=1400*dt;p.y+=p.vy*dt;p.ground=False
    if m['kind']=='swamp' and was_ground and abs(old_y-previous_ground)<3 and p.vy>=0 and p.y>=gy-18:
        p.y=gy;p.vy=0;p.ground=True
    elif p.vy>=0:
        floors=[q['y'] for q in m['platforms'] if not q.get('contourGround') and q['x']+8<p.x<q['x2']-8 and old_y<=q['y']+7 and p.y>=q['y']]
        if gy is not None and old_y<=gy+7 and p.y>=gy:floors.append(gy)
        if floors:p.y=min(floors);p.vy=0;p.ground=True
    if solids and p.vy<0:
        ceiling=[r for r in solids if p.x+20>r['x'] and p.x-20<r['x']+r['w'] and old_y-123.26>=r['y']+r['h']-.01 and p.y-123.26<=r['y']+r['h']]
        if ceiling:p.y=max(r['y']+r['h'] for r in ceiling)+123.26;p.vy=0
    if m['kind']=='swamp' and p.y>gy:
        p.y=gy;p.vy=0;p.ground=True
    if p.y>850:
        p.x,p.y=m['spawn'];p.vx=p.vy=0;p.ground=True;p.climb=None

def portal_at(link,p):
    return p.ground and p.climb is None and abs(p.x-link['exit'][0])<link['radius'] and abs(p.y-link['exit'][1])<22 and (not link.get('intent') or bool(p.buttons&4))


def dismount(m,cx,y,offset):
    if m is None:return cx+offset
    q=next((q for q in m['platforms'] if abs(q['y']-y)<1 and q['x']<=cx+8 and q['x2']>=cx-8),None)
    return max(q['x']+24,min(q['x2']-24,cx+offset)) if q else cx+offset

