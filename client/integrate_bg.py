from pathlib import Path
from PIL import Image
import numpy as np
import shutil,re,json
work=Path('/mnt/data/forest_bg_v7_9G_work')
bg=work/'assets/backgrounds'
bg.mkdir(parents=True,exist_ok=True)
sources={
 'bg_00_sky.png':'tranquil_azure_sky_with_wispy_clouds.png',
 'bg_01_clouds_source.png':'misty_blue_parallax_cloud_layer.png',
 'bg_02_far_mountains.png':'misty_layered_mountain_panorama.png',
 'bg_03_mid_forest.png':'misty_wuxia_forest_mountain_panorama.png',
 'bg_04_foreground_leaves.png':'misty_forest_foliage_frame.png'
}
for dest,src in sources.items():
 shutil.copy2('/mnt/data/'+src,bg/dest)
# A non-destructive runtime version of the cloud image: alpha-faded horizontal edges so repeating is visually smooth.
im=Image.open(bg/'bg_01_clouds_source.png').convert('RGBA')
a=np.array(im)
h,w=a.shape[:2]
x=np.arange(w,dtype=np.float32)
fade_len=185.0
fade=np.minimum(1,np.minimum((x+0.5)/fade_len,(w-x-0.5)/fade_len))
fade=np.maximum(0,fade)**1.7
a[:,:,3]=np.rint(a[:,:,3].astype(np.float32)*fade[None,:]).clip(0,255).astype(np.uint8)
a[:,:,3][a[:,:,3]<7]=0
Image.fromarray(a,'RGBA').save(bg/'bg_01_clouds_loop.png',optimize=True)
index=work/'index.html'
s=index.read_text()
start=s.index('// Static, code-drawn parallax')
end=s.index('Object.defineProperty(window,\'__wuxiaForestVisualStatus\'',start)
new='''// V7.9G: five actual PNG background planes; foreground is overlaid separately.
// No ground, ropes, platforms or water animation is baked into these backgrounds.
const bgImageManifest = {
  sky:'assets/backgrounds/bg_00_sky.png',
  clouds:'assets/backgrounds/bg_01_clouds_loop.png',
  mountains:'assets/backgrounds/bg_02_far_mountains.png',
  forest:'assets/backgrounds/bg_03_mid_forest.png',
  foliage:'assets/backgrounds/bg_04_foreground_leaves.png'
};
const bgImages = {};
for(const [key,src] of Object.entries(bgImageManifest)){
  const img=new Image();img.decoding='async';img.src=src+'?v=bg-01';bgImages[key]=img;
}
// Mountain/forest strips are not horizontally seamless: pan only inside the actual art.
// Cloud strip has transparent feathered ends; drawing it cyclically produces an unbroken drift.
function loadedBg(k){const im=bgImages[k];return im&&im.complete&&im.naturalWidth>0?im:null}
function drawBackgroundPanorama(key,parallax,baseHeight,baseline){
  const im=loadedBg(key);if(!im)return;
  const scale=Math.max(.82,Math.min(1.25,H/690));
  const maxCam=Math.max(0,worldW-W/scale);
  let outH=Math.max(baseHeight,H*1.09),outW=im.naturalWidth*(outH/im.naturalHeight);
  const requiredWidth=W+maxCam*parallax+24;
  if(outW<requiredWidth){outW=requiredWidth;outH=outW*im.naturalHeight/im.naturalWidth;}
  const x=-cam*parallax;
  ctx.drawImage(im,Math.round(x),Math.round(baseline-outH),Math.ceil(outW),Math.ceil(outH));
}
function drawCloudDrift(){
  const im=loadedBg('clouds');if(!im)return;
  // Image is a transparent cloud overlay, not a second sky rectangle.
  const outH=Math.max(270,H*.49),outW=outH*im.naturalWidth/im.naturalHeight;
  const period=outW;
  const drift=now*5.5+cam*.075;
  let x=-(drift%period);
  if(x>0)x-=period;
  // 3 copies are sufficient for all viewport sizes, with safety on ultra-wide displays.
  for(;x<W;x+=period)ctx.drawImage(im,x,Math.round(H*.065),outW,outH);
}
function forestBg(){
  const sky=loadedBg('sky');
  if(sky)ctx.drawImage(sky,0,0,W,H);
  else {ctx.fillStyle=backgroundGradient;ctx.fillRect(0,0,W,H)}
  drawCloudDrift();
  const scale=Math.max(.82,Math.min(1.25,H/690));
  const footholdScreenY=H-110*scale;
  drawBackgroundPanorama('mountains',.14,460,footholdScreenY+75);
  drawBackgroundPanorama('forest',.29,460,footholdScreenY+75);
  // Gentle atmospheric veil keeps foreground ground tiles readable.
  const fog=ctx.createLinearGradient(0,H*.35,0,H);
  fog.addColorStop(0,'rgba(221,249,242,0)');fog.addColorStop(1,'rgba(211,240,225,.12)');
  ctx.fillStyle=fog;ctx.fillRect(0,H*.35,W,H*.65);
}
function drawForestNearOverlay(){
  const im=loadedBg('foliage');if(!im)return;
  const scale=Math.max(.82,Math.min(1.25,H/690));
  const maxCam=Math.max(0,worldW-W/scale);
  let outH=Math.max(375,H*1.04),outW=im.naturalWidth*(outH/im.naturalHeight);
  const requiredWidth=W+maxCam*.37+30;
  if(outW<requiredWidth){outW=requiredWidth;outH=outW*im.naturalHeight/im.naturalWidth;}
  // Only top/corners, never cover the player's lower-half or skill HUD.
  ctx.save();ctx.beginPath();ctx.rect(0,0,W,H*.58);ctx.clip();
  ctx.globalAlpha=.45;
  ctx.drawImage(im,Math.round(-cam*.37),Math.round(-H*.055),Math.ceil(outW),Math.ceil(outH));
  ctx.restore();
}
Object.defineProperty(window,'__wuxiaBgVisualStatus',{get(){
  const status=Object.fromEntries(Object.entries(bgImages).map(([k,img])=>[k,{loaded:img.complete&&img.naturalWidth>0,width:img.naturalWidth||0,height:img.naturalHeight||0}]));
  return {layers:status,count:Object.values(status).filter(x=>x.loaded).length,total:5,cloudDriftPixelsPerSecond:5.5,backgroundVersion:'v7.9G'};
}});
'''
s=s[:start]+new+s[end:]
old="forestBackLayers.length=0;forestBackLayers.push(createForestBackgroundLayer('far'),createForestBackgroundLayer('mid'),createForestBackgroundLayer('near'))"
if old not in s:raise RuntimeError('resize init not found')
s=s.replace(old,'/* PNG background image planes do not need canvas regeneration on resize. */')
old='drawEffects();drawProjectiles();\n for(const p of particles)'
assert old in s
# Overlay needs to run in screen-space after ctx.restore.
old='ctx.restore();\n ctx.fillStyle=\'#173d376f\';'
assert old in s
s=s.replace(old,'ctx.restore();\n drawForestNearOverlay();\n ctx.fillStyle=\'#173d376f\';',1)
s=s.replace('WUXIA • FLUTE ONLINE v7.9 • FOREST','WUXIA • FLUTE ONLINE v7.9G • FOREST + PARALLAX')
s=s.replace('แผนที่ป่าเขียวชอุ่ม | Tileset v1','ป่าเขียวชอุ่ม | Parallax 5 Layers')
index.write_text(s)
print('index bytes',index.stat().st_size, 'new assets',[(p.name,p.stat().st_size) for p in bg.iterdir()])
