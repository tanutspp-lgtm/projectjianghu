"""Read-only deployment precheck; run inside the existing /opt/jianghu checkout."""
import ast,hashlib,importlib.util,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
required=['compact_wire_v80du','combat_progression_v80bs','sandbox_loadouts_v80bt','monster_hp_def_v80bu','farm_auto_v80bu','websockets']
errors=[]
for name in required:
 if importlib.util.find_spec(name) is None:errors.append('Missing existing dependency: '+name)
for name in ['beast_map_common_v80bq.json','loot_templates_v80bs.json','world_v56.json']:
 p=root/name
 if not p.is_file():errors.append('Missing file: '+name)
 else:json.loads(p.read_text())
for name in ['server.py','world_physics_v56.py','swamp_pit_nav.py']:
 try:ast.parse((root/name).read_text())
 except Exception as e:errors.append(name+': '+str(e))
if errors:
 print('\n'.join(errors));sys.exit(1)
print('Syntax and direct dependencies found. This does not verify the running service, online gameplay, or newer Git changes.')
print('Feature:',json.loads((root/'world_v56.json').read_text())['feature'])

