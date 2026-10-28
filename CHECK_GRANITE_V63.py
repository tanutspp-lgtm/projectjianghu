"""Run inside /opt/jianghu before restarting the existing service."""
from pathlib import Path
import ast,json,sys
P=Path(__file__).resolve().parent
d=json.loads((P/'world_v56.json').read_text())
assert d['feature']=='world-maps-v63-granite-pair-connected-v1','Wrong world feature'
ids=['granite_ascent_lower','granite_ascent_upper']
for id in ids:
 m=d['maps'][id];assert len(m['platforms'])==11 and len(m['climbs'])==10
 for c in m['climbs']:
  for y in [c['top'],c['bottom']]:assert any(p['y']==y and p['x']+24<c['x']<p['x2']-24 for p in m['platforms']),(id,c)
for link in [l for l in d['links'] if l['from'] in ids or l['to'] in ids]:
 assert link['from'] in ids and link['to'] in ids,'Unexpected connection to old route'
 for id,point in [(link['from'],link['exit']),(link['to'],link['spawn'])]:
  x,y=point;assert any(p['y']==y and p['x']+24<x<p['x2']-24 for p in d['maps'][id]['platforms']),'Unsupported portal endpoint'
for name in ['server.py','world_physics_v56.py']:
 p=P/name;assert p.exists(),'Missing existing runtime: '+name;ast.parse(p.read_text())
server=(P/'server.py').read_text();assert 'EXPANSION_MAPS' in server and "WORLD_V56['links']" in server and "WORLD_V56['feature']" in server,'Existing runtime requires review; do not restart yet'
assert 'forest-fork-map11-v21-clean-ropes' in server,'Map11 feature must remain enabled'
print('V63 map data, portal endpoints and existing Python syntax passed.')
print('This does not verify the running service or live online gameplay.')
