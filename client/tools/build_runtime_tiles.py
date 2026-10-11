from PIL import Image, ImageFilter, ImageDraw
from pathlib import Path
import numpy as np, json, hashlib
base=Path(__file__).resolve().parent.parent
source=Path(__import__('sys').argv[1]) if len(__import__('sys').argv)>1 else base/'assets'/'forest'/'forest_master_original.png'
out=base/'assets'/'forest'
out.mkdir(parents=True,exist_ok=True)
original=Image.open(source).convert('RGBA')
assert original.size==(1774,887),original.size
# Preserve the exact provided master bytes: never overwrite the source when re-slicing.
a=np.array(original)
manifest={'source':'assets/forest/forest_master_original.png','source_size':[1774,887], 'description':'Game render crops from forest-master. Master stored unmodified. All locations are fixed source pixels. Crops preserve native pixel dimensions except fringe cleanup for game visibility.','assets':{}}
# Crop tight enough to include transparent silhouette, with manually fixed source ranges.
def cut(name,rect):
 x1,y1,x2,y2=rect
 c=a[y1:y2,x1:x2].copy()
 assert c.size and x1>=0 and x2<=1774 and y1>=0 and y2<=887
 # Only delete mostly-transparent RGB chromatic fringe. This leaves opaque illustrated foliage intact.
 rgb=c[:,:,:3].astype(np.int16); alpha=c[:,:,3];
 neon=((rgb[:,:,1] > 180) & (rgb[:,:,1] > (rgb[:,:,0]*1.65)) & (rgb[:,:,2]<150)) | ((rgb[:,:,0]>180)&(rgb[:,:,1]>160)&(rgb[:,:,2]<95)) | ((rgb[:,:,0]>170)&(rgb[:,:,1]<90)&(rgb[:,:,2]<100))
 fringe=(alpha<195)&neon
 alpha[fringe]=0
 alpha[alpha<22]=0
 c[:,:,3]=alpha
 img=Image.fromarray(c,'RGBA')
 img.save(out/(name+'.png'),optimize=True)
 manifest['assets'][name]={'src':f'assets/forest/{name}.png','source_rect':[x1,y1,x2-x1,y2-y1],'size_px':list(img.size),'alpha_bbox':list(img.getbbox() or (0,0,0,0))}

# Original sheet top-left: 8 columns, manually measured per column due imperfect generation.
ground_x=[16,112,208,304,400,496,592,688,788]
ground_rows=[(10,105),(105,217),(217,300),(300,386)]
for row,yr in enumerate(ground_rows):
 for col in range(8):
  cut(f'ground_r{row+1}_c{col+1}', (ground_x[col],yr[0],ground_x[col+1],yr[1]))

platform_x=[877,987,1098,1209,1325,1438,1548,1658,1767]
platform_rows=[(36,126),(126,230),(230,354)]
for row,yr in enumerate(platform_rows):
 for col in range(8):
  cut(f'platform_r{row+1}_c{col+1}',(platform_x[col],yr[0],platform_x[col+1],yr[1]))

# Continuous rope artworks in source are very long; split into repeatable working chunks.
cut('rope_top', (60,425,160,510))
cut('rope_mid', (278,555,326,608))
cut('rope_alt_mid',(467,560,525,613))
cut('rope_bottom',(636,710,741,832))
cut('rope_knotted_mid',(464,650,532,709))
# Bamboo ladder: cap and one rung extracted from same ladder family.
cut('ladder_top',(918,428,1055,494))
cut('ladder_mid',(1106,509,1232,557))
cut('ladder_bottom',(1472,756,1605,826))
cut('ladder_variant_mid',(1293,509,1420,557))
with open(out/'forest_atlas_regions.json','w') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
# Derive a mirrored seamless face tile for the ground's infill, using the same art.
wall=original.crop((131,126,192,198))
from PIL import ImageOps
rock=ImageOps.fit(Image.alpha_composite(Image.new('RGBA',wall.size,(74,96,78,255)),wall),(256,256),method=Image.Resampling.LANCZOS)
for horizontal in (0,1):
 for vertical in (0,1):
  a=rock
  if horizontal:a=ImageOps.mirror(a)
  if vertical:a=ImageOps.flip(a)
  a.save(out/f'rock_face_mirror_{horizontal}{vertical}.png',optimize=True)
print('Generated',len(manifest['assets']),'crops from',source, 'without modifying the master')
for nm in ['ground_r1_c1','ground_r1_c2','platform_r1_c2','platform_r3_c2','ladder_mid','rope_mid']:
 print(nm,manifest['assets'][nm])
