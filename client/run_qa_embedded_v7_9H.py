from pathlib import Path
from playwright.sync_api import sync_playwright
import json,base64,re,time
P=Path('/mnt/data/forest_bg_v7_9H_fixed')
qa=P/'QA';qa.mkdir(exist_ok=True)
asset_paths=[*P.glob('assets/backgrounds/*.png'),*P.glob('assets/forest/*.png'),P/'characters/male_hair_01_black.png']
asset_paths=[p for p in asset_paths if p.is_file()]
# All important assets load locally via embedded data: URLs in this *QA-only* document.
assets={p.relative_to(P).as_posix():'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode('ascii') for p in asset_paths}
transparent='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=='
intercept='''<script>
const __qaImages = '''+json.dumps(assets)+''';
const __imDesc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
Object.defineProperty(HTMLImageElement.prototype,'src',{
get(){return __imDesc.get.call(this)},
set(v){const key=String(v).split('?')[0];return __imDesc.set.call(this,__qaImages[key]||DEFAULT)}
});
</script>'''
intercept=intercept.replace('\u001bDEFAULT\u001b',json.dumps(transparent))
html=(P/'index.html').read_text().replace('<script>',intercept+'<script>',1)
html=html.replace('function loop(t){', 'window.__qaMovePlayer=function(x){player.x=x;player.y=550;player.vx=0;player.vy=0;player.ground=true};function loop(t){',1)
print('QA local inline html size',round(len(html)/1024/1024,2),'MiB', 'image count',len(assets),flush=True)
with sync_playwright() as pl:
 b=pl.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--disable-dev-shm-usage','--no-sandbox','--disable-gpu'])
 for tag,w,h in [('DESKTOP',1280,720),('MOBILE',844,390)]:
  ctx=b.new_context(viewport={'width':w,'height':h},device_scale_factor=1,has_touch=(tag=='MOBILE'),is_mobile=(tag=='MOBILE'))
  page=ctx.new_page();errs=[]
  page.on('pageerror',lambda e: errs.append(str(e)))
  page.set_content(html,wait_until='domcontentloaded',timeout=60000)
  try:
   page.wait_for_function('window.__wuxiaBgVisualStatus && window.__wuxiaBgVisualStatus.count===5',timeout=20000)
   page.wait_for_function("document.querySelector('#creatorStart').disabled===false",timeout=20000)
   page.locator('#creatorStart').click();page.wait_for_timeout(1200)
   out=qa/f'FOREST_PARALLAX_{tag}.png';page.screenshot(path=str(out))
   d=page.evaluate('({bg:window.__wuxiaBgVisualStatus,forest:window.__wuxiaForestVisualStatus})')
   if tag=='DESKTOP':
    page.evaluate('window.__qaMovePlayer(1550)');page.wait_for_timeout(350)
    page.screenshot(path=str(qa/'FOREST_PARALLAX_DESKTOP_MOVED.png'))
    d['after_move']=page.evaluate('window.__wuxiaBgVisualStatus')
   print(json.dumps({'device':tag,'state':d,'js_errors':errs,'image':str(out)},ensure_ascii=False),flush=True)
  except Exception as e:
   print('QA_FAIL',tag,repr(e), 'page errors', errs,flush=True)
   page.screenshot(path=str(qa/f'FOREST_PARALLAX_{tag}_FAIL.png'))
  ctx.close()
 b.close()
