"""Mirrors combat_collision_v184.js: physical hit height plus terrain visibility."""
import math
EPS=1e-7

def profile_edges(points,out):
    for (a,b),(c,d) in zip(points,points[1:]):
        n=max(1,math.ceil((c-a)/8));px,py=a,b
        for k in range(1,n+1):
            t=k/n;x=a+(c-a)*t;y=b+(d-b)*t*t*(3-2*t)
            out.append((px,py,x,y));px,py=x,y

def compile_geometry(platforms,profile=None,solids=(),contains=None):
    edges=[];rects=() if contains else solids
    for p in platforms:
        if p.get('contourGround') and profile:continue
        if contains and not p.get('oneWay') and not p.get('smallLedge'):continue
        if p.get('profile'):profile_edges(p['profile'],edges)
        else:edges.append((p['x'],p['y'],p['x2'],p['y']))
    if profile and not contains:profile_edges(profile,edges)
    for q in rects:
        x,y=q['x'],q['y'];x2,y2=x+q['w'],y+q['h']
        edges.extend(((x,y,x2,y),(x2,y,x2,y2),(x2,y2,x,y2),(x,y2,x,y)))
    return dict(edges=edges,rects=rects,contains=contains,surfaces=list(platforms)+([dict(x=profile[0][0],x2=profile[-1][0],profile=profile)] if profile else []))

def blocked(x0,y0,x1,y1,g):
    dx,dy=x1-x0,y1-y0
    if abs(dx)+abs(dy)<EPS:return False
    left,right=sorted((x0,x1));top,bottom=sorted((y0,y1))
    for a,b,c,d in g['edges']:
        if max(a,c)<left or min(a,c)>right or max(b,d)<top or min(b,d)>bottom:continue
        ex,ey,rx,ry=c-a,d-b,a-x0,b-y0;den=dx*ey-dy*ex
        if abs(den)<EPS:
            if abs(rx*dy-ry*dx)<EPS and min(right,max(a,c))-max(left,min(a,c))>EPS:return True
            continue
        t=(rx*ey-ry*ex)/den;u=(rx*dy-ry*dx)/den
        if EPS<t<1-EPS and -EPS<=u<=1+EPS:return True
    if any(q['x']+EPS<x1<q['x']+q['w']-EPS and q['y']+EPS<y1<q['y']+q['h']-EPS for q in g['rects']):return True
    if g['contains']:
        steps=max(1,math.ceil(math.hypot(dx,dy)/8))
        for k in range(1,steps+1):
            if g['contains'](x0+dx*k/steps,y0+dy*k/steps):return True
    return False

def radius(shot):
    return 22 if shot.mode=='melee' else 10 if shot.profession=='healer' else 18 if shot.profession=='tang' else 28

def height(s,x):
    p=s.get('profile')
    if not p:return s['y']
    if x<=p[0][0]:return p[0][1]
    for (a,b),(c,d) in zip(p,p[1:]):
        if x<=c:
            t=(x-a)/(c-a);return b+(d-b)*t*t*(3-2*t)
    return p[-1][1]

def can_reach(x0,y0,foot,victim,g):
    if foot is not None and victim.ground and abs(victim.y-foot)>16:
        same=any(s['x']<=x0<=s['x2'] and s['x']<=victim.x<=s['x2'] and abs(height(s,x0)-foot)<3 and abs(height(s,victim.x)-victim.y)<3 for s in g['surfaces'])
        if not same and blocked(x0,foot-1,victim.x,victim.y-1,g):return False
    return not blocked(x0,y0,victim.x,victim.y-43,g)

def can_hit(shot,victim,g):
    h=123.26 if victim.hum else 90;ry=radius(shot)
    if shot.y+ry<victim.y-h or shot.y-ry>victim.y-6:return False
    return can_reach(shot.launch_x184 if shot.launch_x184 is not None else shot.x,
                     shot.launch_y184 if shot.launch_y184 is not None else shot.y,shot.launch_foot184,victim,g)
