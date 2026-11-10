"""Check patched source and the running existing service; read only."""
from pathlib import Path
import sys,urllib.request,os,ast
root=Path(__file__).resolve().parent
for name in ('server.py','martial_combat_v187.py'):
 text=(root/name).read_text(encoding='utf-8');ast.parse(text)
 if 'martial-tempo-v1876-v1' not in text:sys.exit('Installed file is not V187.6: '+name)
import json
rules=json.loads((root/'combat_rules_v187.json').read_text())
assert rules['guardMax']==150 and rules['rage']['block']==10 and rules['rage']['hit']==8 and rules['rage']['hurt']==5
assert rules['jianReturnWindow']==2.5
ult=rules['classes']['healer']['ultimate']
assert ult['rageCost']==60 and ult['rageMax']==100 and ult['duration']==.5
assert [t['at'] for t in ult['rageTiers']]==[60,70,80,90,100] and ult['rageTiers'][-1]['stun']==1.2
assert all(c['guardReduction']==.85 for c in rules['classes'].values())
print('Installed files and balance data: V187.6')
port=os.environ.get('PORT','8765')
try:
 with urllib.request.urlopen('http://127.0.0.1:'+port+'/healthz',timeout=4) as response:body=response.read(4096).decode()
except Exception as error:sys.exit('Cannot verify running local backend: '+str(error))
print('Running process:',body.strip())
if 'JIANGHU_BACKEND_V187_6' not in body or 'martial-tempo-v1876-v1' not in body:sys.exit('Running backend is not V187.6. Restart the existing game service.')
print('PASS: installed files and running backend both V187.6')
