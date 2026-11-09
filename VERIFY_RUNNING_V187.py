"""Read-only distinction between installed files and the running local service."""
from pathlib import Path
import sys,urllib.request,os,ast
root=Path(__file__).resolve().parent
for name in ('server.py','character_classes_v181.py','combat_collision_v184.py','martial_combat_v187.py'):
    text=(root/name).read_text(encoding='utf-8');ast.parse(text)
    if name=='server.py' and 'martial-combat-v187-v1' not in text:sys.exit('Installed server.py is not V187')
print('Installed files: V187')
port=os.environ.get('PORT','8765')
try:
    with urllib.request.urlopen('http://127.0.0.1:'+port+'/healthz',timeout=4) as response:body=response.read(4096).decode()
except Exception as error:sys.exit('Cannot verify running local backend: '+str(error))
print('Running process:',body.strip())
if 'JIANGHU_BACKEND_V187' not in body:sys.exit('Running process is not V187. Restart the existing game service.')
print('PASS: installed files and running backend both V187')
