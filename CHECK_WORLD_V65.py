"""Read-only V65 preflight: run after git pull, before service restart."""
import ast,json,sys,types
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
d=json.loads((P/'world_v56.json').read_text())
assert d['feature']=='world-maps-v65-cave-seams-inland-climb-v1','world_v56.json must be V65'
for p in P.glob('*.py'):ast.parse(p.read_text())
import server as s
import world_physics_v56 as physics
assert s.WORLD_V56['feature']==d['feature']
assert len(s.PUBLIC_MAP_IDS)==34 and len(set(s.PUBLIC_MAP_IDS))==34
assert not d['maps']['granite_inland_1']['downOnly']
assert len(d['maps']['granite_inland_1']['climbs'])==20
m=d['maps']['sword_cave_top'];bridge=m['platforms'][3]
assert (bridge['x'],bridge['x2'],bridge['y'])==(1296,1738,-140)
for x,vx in [(1260,205),(1820,-205)]:
 p=types.SimpleNamespace(x=x,y=-140,vx=vx,vy=0,ground=True,climb=None)
 for _ in range(180):
  previous=p.x;p.x+=p.vx/60;physics.step(p,1/60,m)
  assert abs(p.y+140)<1e-6 and abs(p.x-previous)<10,'Cave seam regression'
assert len(s.MOUNTAIN_MAPS['granite_ascent_1']['platforms'])==11
assert len(s.MOUNTAIN_MAPS['granite_ascent_1']['climbs'])==10
assert s.GRANITE_WALL_PORTALS[('granite_ascent_1','granite_wall_1')][1]==-1850
b=next(q for q in d['maps']['gorge_bridge_2']['platforms'] if q.get('key')=='bridge');assert b.get('continuousDeck')
assert not {'granite_ascent_lower','granite_ascent_upper'}&set(d['maps'])
text=(P/'server.py').read_text();assert 'granite-ascent-v64-single-map' in text and 'granite-wall-chain-v64-single-ascent-link' in text
assert 'forest-fork-map11-v21-clean-ropes' in text and s.ENABLE_FAST_SELF_30HZ
print('V65: syntax/imports, 34 maps, cave seam, inland two-way ladders, prior bridge/ascent geometry passed.')
print('Feature:',d['feature'])
print('Map11 handshake and default Self30Hz retained. This preflight does not test the running service or live gameplay.')
