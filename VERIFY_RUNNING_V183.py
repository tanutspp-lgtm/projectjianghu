"""Read-only distinction between installed files and the running local service."""
from pathlib import Path
import sys,urllib.request,os,ast
root=Path(__file__).resolve().parent
for name in ('server.py','character_classes_v181.py'):
    text=(root/name).read_text(encoding='utf-8');ast.parse(text)
    if name=='server.py' and 'classes-v183-combat-v1' not in text:sys.exit('Installed server.py is not V183')
print('Installed files: V183')
port=os.environ.get('PORT','8765')
try:
    with urllib.request.urlopen('http://127.0.0.1:'+port+'/healthz',timeout=4) as response:body=response.read(4096).decode()
except Exception as error:sys.exit('Cannot verify running local backend: '+str(error))
print('Running process:',body.strip())
if 'JIANGHU_BACKEND_V183' not in body:sys.exit('Running process is not V183. Restart the existing game service.')
print('PASS: installed files and running backend both V183')
