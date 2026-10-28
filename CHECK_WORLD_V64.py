"""Run after git pull in /opt/jianghu, before restarting jianghu.service."""
import ast,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));d=json.loads((P/'world_v56.json').read_text())
assert d['feature']=='world-maps-v64-single-ascent-bridge-v1','world_v56.json must be V64'
assert not {'granite_ascent_lower','granite_ascent_upper'}&set(d['maps']),'Remove obsolete trial map entries'
for p in P.glob('*.py'):ast.parse(p.read_text())
import server as s
assert s.WORLD_V56['feature']==d['feature']
assert len(s.MOUNTAIN_MAPS['granite_ascent_1']['platforms'])==11,'server.py has old ascent geometry'
assert len(s.MOUNTAIN_MAPS['granite_ascent_1']['climbs'])==10
assert s.GRANITE_WALL_PORTALS[('granite_ascent_1','granite_wall_1')][1]==-1850,'server.py has old portal height'
assert s.GRANITE_WALL_PORTALS[('granite_wall_1','granite_ascent_1')][-1]==-1850
assert len(s.PUBLIC_MAP_IDS)==34 and len(set(s.PUBLIC_MAP_IDS))==34
b=next(q for q in d['maps']['gorge_bridge_2']['platforms'] if q.get('key')=='bridge');assert b.get('continuousDeck')
assert 'continuousDeck' in (P/'world_physics_v56.py').read_text(),'world_physics_v56.py missing bridge fix'
text=(P/'server.py').read_text();assert 'granite-ascent-v64-single-map' in text and 'granite-wall-chain-v64-single-ascent-link' in text
assert 'forest-fork-map11-v21-clean-ropes' in text and s.ENABLE_FAST_SELF_30HZ
print('V64: 34 maps, single replacement ascent, bridge fix, syntax and runtime dependencies passed.')
print('Feature:',d['feature'])
print('Map11 handshake and default Self30Hz retained. Running service / live gameplay not verified by this check.')
