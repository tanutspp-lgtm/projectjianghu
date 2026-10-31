"""Read-only V66 preflight; run after git pull, before restart."""
import ast,json,sys,types
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));d=json.loads((P/'world_v56.json').read_text())
assert d['feature']=='world-maps-v66-inland-cave-return-v1','world_v56.json must be V66'
for p in P.glob('*.py'):ast.parse(p.read_text())
import server as s
import world_physics_v56 as physics
assert s.WORLD_V56['feature']==d['feature']
assert len(s.PUBLIC_MAP_IDS)==34 and len(set(s.PUBLIC_MAP_IDS))==34
m=d['maps']['granite_inland_1'];assert not m['downOnly'] and len(m['climbs'])==20
link=next(l for l in d['links'] if l['from']=='granite_inland_1' and l['to']=='sword_cave_top')
assert link['exit']==[1360,-4250] and link['spawn']==[2180,-140] and link['intent'] and link['radius']==48
out=next(l for l in d['links'] if l['from']=='sword_cave_top' and l['to']=='granite_inland_1')
assert out['spawn']==[1240,-4250]
p=types.SimpleNamespace(x=1360,y=-4250,ground=True,climb=None,buttons=0)
assert not physics.portal_at(link,p);p.buttons=4;assert physics.portal_at(link,p)
p.x=1240;assert not physics.portal_at(link,p)
for x,vx in [(1260,205),(1820,-205)]:
 p=types.SimpleNamespace(x=x,y=-140,vx=vx,vy=0,ground=True,climb=None)
 for _ in range(180):
  previous=p.x;p.x+=p.vx/60;physics.step(p,1/60,d['maps']['sword_cave_top'])
  assert abs(p.y+140)<1e-6 and abs(p.x-previous)<10
assert len(s.MOUNTAIN_MAPS['granite_ascent_1']['platforms'])==11
assert len(s.MOUNTAIN_MAPS['granite_ascent_1']['climbs'])==10
assert next(q for q in d['maps']['gorge_bridge_2']['platforms'] if q.get('key')=='bridge').get('continuousDeck')
assert 'forest-fork-map11-v21-clean-ropes' in (P/'server.py').read_text() and s.ENABLE_FAST_SELF_30HZ
print('V66: imports/syntax, two-way cave links, safe arrival, prior cave seam/bridge/climbs and 34 maps passed.')
print('Feature:',d['feature'])
print('This does not verify the running service or remote gameplay.')
