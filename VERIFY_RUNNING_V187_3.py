"""Check patched source and the running existing service; read only."""
from pathlib import Path
import sys,urllib.request,os,ast
root=Path(__file__).resolve().parent
for name in ('server.py','martial_combat_v187.py'):
 text=(root/name).read_text(encoding='utf-8');ast.parse(text)
 if 'martial-guard360-v1873-v1' not in text:sys.exit('Installed file is not V187.3: '+name)
print('Installed files: V187.3')
port=os.environ.get('PORT','8765')
try:
 with urllib.request.urlopen('http://127.0.0.1:'+port+'/healthz',timeout=4) as response:body=response.read(4096).decode()
except Exception as error:sys.exit('Cannot verify running local backend: '+str(error))
print('Running process:',body.strip())
if 'JIANGHU_BACKEND_V187_3' not in body or 'martial-guard360-v1873-v1' not in body:sys.exit('Running backend is not V187.3. Restart the existing game service.')
print('PASS: installed files and running backend both V187.3')
