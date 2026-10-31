"""Read-only pre-restart check for matching V67 world data and scoped navigation."""
from pathlib import Path
import ast,json,sys
root=Path(__file__).resolve().parent
expected='world-maps-v67-late-regions-v1'
for name in ['server.py','world_physics_v56.py','late_map_nav_v67.py']:
 ast.parse((root/name).read_text())
j=json.loads((root/'world_v56.json').read_text());assert j['feature']==expected,j.get('feature')
import server
ids=[mid for mid,m in j['maps'].items() if m.get('region')=='late_v67'];assert len(ids)==8
for mid in ids:
 m=j['maps'][mid];nav=server.farm_nav_for(mid)
 assert len(nav.connected_component(0))==len(m['platforms']),mid
 assert server.city_world_width(mid)==m['worldWidth']
print('V67 syntax, imports, 8 world layouts and AUTO topology passed.')
print('Feature:',expected)
print('This does not verify the running service, online gameplay or newer Git changes.')
