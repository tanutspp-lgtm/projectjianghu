"""Write a new server file with ONLY Map 11 geometry and capability updated.
Usage: python merge_map11_v21.py /path/to/current/server.py /path/to/server.map11-v20.py
The source file is never overwritten. Review the diff before deployment.
"""
import ast,json,sys,difflib
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit(__doc__)
src,dst=map(Path,sys.argv[1:])
if src.resolve()==dst.resolve() or dst.exists():raise SystemExit('Output must be a new file, different from source.')
text=src.read_text();tree=ast.parse(text);geo=json.loads(Path(__file__).with_name('map11_geometry_v21.json').read_text())
targets=[]
for node in tree.body:
 if isinstance(node,ast.Assign):
  for target in node.targets:
   if isinstance(target,ast.Subscript) and isinstance(target.value,ast.Name) and target.value.id=='BAMBOO_MAPS' and isinstance(target.slice,ast.Constant) and target.slice.value=='forest_fork_11':targets.append(node)
if len(targets)!=1:raise SystemExit('Expected one Map 11 assignment. No output written; manual merge required.')
node=targets[0];oldmap=ast.literal_eval(node.value)
oldmap['platforms']=[(p['x'],p['x2'],p['y']) for p in geo['platforms']]
oldmap['climbs']=[(c['x'],c['top'],c['bottom'],c['type']) for c in geo['climbs']]
lines=text.splitlines(True);lines[node.lineno-1:node.end_lineno]=["BAMBOO_MAPS['forest_fork_11'] = "+repr(oldmap)+'\n']
new=''.join(lines)
oldcaps=["'forest-fork-map11-v20-v19b'","'forest-fork-map11-tileset-v3'"];newcap="'forest-fork-map11-v21-clean-ropes'"
if newcap not in new:
 hits=[cap for cap in oldcaps if new.count(cap)==1]
 if len(hits)!=1:raise SystemExit('Expected exactly one known Map 11 capability (V20 or V3). No output written; manual merge required.')
 new=new.replace(hits[0],newcap)
ast.parse(new);compile(new,str(dst),'exec')
dst.write_text(new)
patch=''.join(difflib.unified_diff(text.splitlines(True),new.splitlines(True),fromfile=str(src),tofile=str(dst)))
Path(str(dst)+'.patch').write_text(patch)
print('Created',dst,'and review diff',str(dst)+'.patch')
print('Original server preserved. Nothing deployed or restarted.')
