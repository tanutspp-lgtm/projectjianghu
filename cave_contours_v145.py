"""Natural cave collision; scoped to caveContours maps. Shared explicit world contours."""
import math
HEIGHT=123.26
AIR_HEIGHT=115.2

def head_height(grounded):return HEIGHT if grounded else AIR_HEIGHT

def height(points,x):
    if x<=points[0][0]:return points[0][1]
    for (a,b),(c,d) in zip(points,points[1:]):
        if x<=c:
            t=(x-a)/(c-a);return b+(d-b)*t*t*(3-2*t)
    return points[-1][1]

def platform_y(p,x):return height(p['profile'],x) if p.get('profile') else p['y']

def polygon_intervals(points,x):
    ys=[]
    for a,b in zip(points,points[1:]+points[:1]):
        if min(a[0],b[0])<=x<max(a[0],b[0]):
            ys.append(a[1]+(x-a[0])/(b[0]-a[0])*(b[1]-a[1]))
    ys.sort()
    return list(zip(ys[::2],ys[1::2]))

def intervals(m,x):
    out=[(-10000,height(m['caveRoof'],x))]
    for p in m['platforms']:
        if not p.get('oneWay') and p.get('solidBounds',{}).get('left',p['x'])<x<p.get('solidBounds',{}).get('right',p['x2']):
            if p.get('bodyPolygon') and (x<p['x']+p['rockEnds']['left']['edgeWidth'] or x>p['x2']-p['rockEnds']['right']['edgeWidth']):
                side='left' if x<p['x']+p['rockEnds']['left']['edgeWidth'] else 'right'
                out.extend(polygon_intervals(p['bodyEndPolygons'][side],x));continue
            a=platform_y(p,x);b=height(p['bottomProfile'],x)
            shaft=next((s for s in m['caveShafts'] if abs(x-s['x'])<s['width']/2-7 and s['top']<b and s['bottom']>a),None)
            if shaft:
                if shaft['top']>a:out.append((a,min(b,shaft['top'])))
                if shaft['bottom']<b:out.append((max(a,shaft['bottom']),b))
            else:out.append((a,b))
    for r in m.get('sideRock',()):
        if r['x']<x<r['x2']:out.append((r['top'],r['bottom']))
    return out

def overlaps(m,x,y,grounded=True):return any(y>a+.2 and y-head_height(grounded)<b-.2 for xx in (x,) for a,b in intervals(m,xx))

def body_overlap(m,x,y,h=HEIGHT):return any(y>a+.1 and y-h<b-.1 for xx in (x-20,x,x+20) for a,b in intervals(m,xx))

def step(p,dt,m):
    p.x=max(27,min(m['worldWidth']-27,p.x))
    if p.climb is not None:return
    h=head_height(p.ground)
    ox=p.x-p.vx*dt;oy=p.y;was=p.ground
    support=next((q for q in m['platforms'] if q['x']+7<ox<q['x2']-7 and abs(platform_y(q,ox)-oy)<3),None) if was else None
    follow=support is not None and support['x']+8<p.x<support['x2']-8 and p.vy>=0
    if follow:p.y=platform_y(support,p.x);p.vy=0;p.ground=True;return
    if m.get('rockEndsV147'):
        if p.x!=ox and not body_overlap(m,ox,oy,h) and body_overlap(m,p.x,oy,h):
            safe,blocked=ox,p.x
            for _ in range(20):
                mid=(safe+blocked)/2
                if body_overlap(m,mid,oy,h):blocked=mid
                else:safe=mid
            p.x=safe;p.vx=0
    else:
        # Legacy cave rectangle collision stays unchanged outside V147 maps.
        for r in list(m['platforms'])+list(m.get('sideRock',())):
            if r.get('oneWay'):continue
            a=r['x'];b=r['x2'];edge=a if p.vx>0 else b
            roof=platform_y(r,edge) if 'y' in r else r['top']
            base=height(r['bottomProfile'],edge) if 'bottomProfile' in r else r['bottom']
            if oy>roof+.1 and oy-h<base-.1:
                if p.vx>0 and ox+20<=a+.01 and p.x+20>a:p.x=a-20;p.vx=0
                elif p.vx<0 and ox-20>=b-.01 and p.x-20<b:p.x=b+20;p.vx=0
    p.vy+=1400*dt;p.y+=p.vy*dt;p.ground=False
    if p.vy>=0:
        floors=[platform_y(q,p.x) for q in m['platforms'] if q['x']+8<p.x<q['x2']-8 and oy<=platform_y(q,p.x)+7 and p.y>=platform_y(q,p.x)]
        if floors:p.y=min(floors);p.vy=0;p.ground=True
    else:
        ceilings=[b for xx in (p.x-18,p.x,p.x+18) for a,b in intervals(m,xx) if oy-h>=b-.01 and p.y-h<=b]
        if ceilings:p.y=max(ceilings)+h;p.vy=0
    if p.y>850:p.x,p.y=m['spawn'];p.vx=p.vy=0;p.ground=True;p.climb=None
