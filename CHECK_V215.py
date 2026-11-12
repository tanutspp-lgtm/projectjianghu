"""Run with the SAME Python/venv as server.py before restart. No DB writes."""
from pathlib import Path
import importlib,json,hashlib,sys
root=Path(__file__).resolve().parent
for name in ['server','owned_equipment_v215','social_v215','sandbox_loadouts_v80bt','martial_combat_v187','combat_collision_v184','character_classes_v181','combat_progression_v80bs']:
 importlib.import_module(name)
import sandbox_loadouts_v80bt as q,owned_equipment_v215 as e,server
assert q.QI_GATES==(10,25,40)
assert server.LOOT_BAG_CAP==e.CAPACITY==100
assert len(e.CAT)==117
assert server.social215.PARTY_CAP==6 and server.social215.GUILD_CAP==24 and server.social215.FRIEND_CAP==50
world=json.loads((root/'world_v56.json').read_text())
assert '175' in world['feature'],world['feature']
assert hasattr(server.martial187,'FALLBACK_FEATURE')
print('V215 FULL dependencies OK | owned gear | bag100 | Qi10/25/40 | social6/24/50 | V213 fallback | World52')
print('Python:',sys.executable)
