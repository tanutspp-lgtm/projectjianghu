from pathlib import Path
from playwright.sync_api import sync_playwright
import json,base64
P=Path('/mnt/data/forest_bg_v7_9H_fixed');qa=P/'QA';qa.mkdir(exist_ok=True)
asset_paths=[*P.glob('assets/backgrounds/*.png'),*P.glob('assets/forest/*.png'),*P.glob('characters/female_hair_01_white.png'),P/'characters/male_hair_01_black.png']
assets={p.relative_to(P).as_posix():'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode('ascii') for p in asset_paths}
transparent='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=='
intercept='''<script>const __qaImages = '''+json.dumps(assets)+''';const __imDesc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');Object.defineProperty(HTMLImageElement.prototype,'src',{get(){return __imDesc.get.call(this)},set(v){const key=String(v).split('?')[0];return __imDesc.set.call(this,__qaImages[key]||'''+json.dumps(transparent)+''')}});</script>'''
s=(P/'index.html').read_text().replace('<script>',intercept+'<script>',1)
s=s.replace('function loop(t){', '''window.__qaInspect=function(){return {x:player.x,y:player.y,ground:player.ground,climb:player.climb && {top:player.climb.top,bottom:player.climb.bottom},ladder:climbs.find(c=>c.type==='ladder')}};
window.__qaPos=function(x,y){player.x=x;player.y=y;player.vx=0;player.vy=0;player.ground=true;player.climb=null;player.climbCooldown=0};
function loop(t){''',1)
with sync_playwright() as pl:
 b=pl.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'])
 ctx=b.new_context(viewport={'width':1474,'height':1024},device_scale_factor=1,has_touch=True,is_mobile=True)
 page=ctx.new_page();errs=[]
 page.on('pageerror',lambda e:errs.append(str(e)))
 page.set_content(s,wait_until='domcontentloaded',timeout=90000)
 page.wait_for_function('window.__wuxiaBgVisualStatus && window.__wuxiaBgVisualStatus.count === 5',timeout=30000)
 page.locator('#creatorGender button').filter(has_text='หญิง').click()
 page.locator('#creatorColors button').filter(has_text='ขาว').click()
 page.wait_for_function("document.querySelector('#creatorStart').disabled===false",timeout=30000)
 page.locator('#creatorStart').click()
 page.evaluate('window.__qaPos(660,235)');page.wait_for_timeout(350)
 # Keep character from walking or falling because x660 is on platform (410..1070) y235.
 page.screenshot(path=str(qa/'FOREST_V79H_IPAD_CHARACTER_LEAVES.png'))
 pos=page.evaluate('window.__qaInspect()')
 page.evaluate('window.__qaPos(1170,550)');page.wait_for_timeout(100)
 starting=page.evaluate('window.__qaInspect()')
 page.keyboard.down('ArrowUp');page.wait_for_timeout(1350);page.keyboard.up('ArrowUp')
 after=page.evaluate('window.__qaInspect()');page.wait_for_timeout(250)
 page.screenshot(path=str(qa/'FOREST_V79H_IPAD_LADDER_MID.png'))
 print(json.dumps({'player_on_high_platform':pos,'ladder_start':starting,'ladder_after':after,'errors':errs,'layers':page.evaluate('window.__wuxiaBgVisualStatus.count')},ensure_ascii=False))
 ctx.close();b.close()
