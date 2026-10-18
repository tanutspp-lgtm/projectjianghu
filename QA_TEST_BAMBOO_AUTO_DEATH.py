"""Isolated deterministic checks. Not a substitute for live deployment QA."""
from pathlib import Path
import ast
from collections import deque
from PIL import Image
root=Path(__file__).resolve().parent
server=(root/'server.py').read_text()
front=(root/'index.html').read_text()
tree=ast.parse(server)
def assignment(name):
 for stmt in tree.body:
  if isinstance(stmt,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in stmt.targets):
   return ast.literal_eval(stmt.value)
 raise AssertionError(name)
maps=assignment('BAMBOO_MAPS')
public=assignment('PUBLIC_MAP_IDS')
assert len(public)==5
assert all(mid in public for mid in maps)
assert 'WORLD_FARM_NAV' in server
assert "map_id: farm_auto.Navigation(BAMBOO_GROUNDS[map_id], BAMBOO_CLIMBS[map_id])" in server
assert 'farm_nav_for(p.room).choose' in server
assert 'platform=farm_nav_for(p.room).platform_at(p)' in server
assert "p.auto_state.enabled=m['enabled'] if p.room in PUBLIC_MAP_IDS else False" in server
assert "'ok':p.room in PUBLIC_MAP_IDS or not m['enabled']" in server
assert 'p.room in PUBLIC_MAP_IDS and p.auto_state.enabled' in server
assert 'const footSink=e.ground?7:0;' in front
assert 'const footSink=(e.ground&&e.dead<=0)?7:0' not in front

for room in public:
 plats=maps[room]['platforms']; climbs=maps[room]['climbs']
 graph=[set() for _ in plats]
 for idx,(x,top,bottom,*_) in enumerate(climbs):
  ends=[i for i,(lo,hi,y) in enumerate(plats) if lo+12<=x<=hi-12 and top-8<=y<=bottom+8]
  assert len(ends)>=2,(room,idx,'unconnected climb')
  for i in ends:
   for j in ends:
    if i!=j:graph[i].add(j)
 reached={0};todo=deque([0]);
 while todo:
  for j in graph[todo.popleft()]:
   if j not in reached:reached.add(j);todo.append(j)
 assert len(reached)==len(plats),(room,reached,len(plats))
 print(f'{room}: {len(plats)} platforms, {len(climbs)} climbs, ALL reachable from ground')

for species in ['bamboo_spirit','bamboo_rabbit','brush_squirrel']:
 for pose in [1,23,22,24]:
  path=root/'assets'/'monsters'/'bamboo'/species/f'pose_{pose:02}.png'
  assert path.exists(),path
  im=Image.open(path)
  assert im.width>50 and im.height>50
 print(species,'stand / down / 3 death poses assets present')
print('PASS: AUTO route graph, public world enable/ack, Stay Alert route, death foot baseline; not end-to-end')
