from pathlib import Path
import subprocess, time, json, os
from playwright.sync_api import sync_playwright
P=Path('/mnt/data/forest_bg_v7_9G_work')
qa=P/'QA';qa.mkdir(exist_ok=True)
server=subprocess.Popen(['python','-m','http.server','8997','--bind','127.0.0.1','--directory',str(P)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 time.sleep(.5)
 with sync_playwright() as pl:
  browser=pl.chromium.launch(headless=True, executable_path='/usr/bin/chromium',args=['--disable-dev-shm-usage','--no-sandbox','--disable-gpu'])
  for tag,w,h in [('DESKTOP',1280,720),('MOBILE',844,390)]:
   context=browser.new_context(viewport={'width':w,'height':h},device_scale_factor=1,is_mobile=(tag=='MOBILE'),has_touch=(tag=='MOBILE'))
   page=context.new_page();errors=[];failed=[]
   page.on('pageerror',lambda e: errors.append(str(e)))
   page.on('requestfailed',lambda req: failed.append(req.url))
   page.goto('http://127.0.0.1:8997/',wait_until='domcontentloaded',timeout=45000)
   page.wait_for_function('window.__wuxiaBgVisualStatus && window.__wuxiaBgVisualStatus.count === 5',timeout=35000)
   page.wait_for_function("document.querySelector('#creatorStart').disabled === false",timeout=40000)
   page.locator('#creatorStart').click()
   page.wait_for_timeout(1200)
   out=qa/f'FOREST_PARALLAX_{tag}.png'
   page.screenshot(path=str(out))
   t1=page.evaluate('window.__wuxiaBgVisualStatus')
   p1=page.evaluate('({cam:typeof cam!==\'undefined\'?cam:null, playerX:player.x, frames: typeof measuredFps!==\'undefined\'?measuredFps:null, forest: window.__wuxiaForestVisualStatus})')
   # On desktop measure camera scroll; key right and observe changing camera.
   if tag=='DESKTOP':
    page.keyboard.down('ArrowRight');page.wait_for_timeout(1800);page.keyboard.up('ArrowRight');page.wait_for_timeout(300)
    out2=qa/'FOREST_PARALLAX_DESKTOP_MOVED.png';page.screenshot(path=str(out2))
    p2=page.evaluate('({cam:cam,playerX:player.x,forest:window.__wuxiaForestVisualStatus})')
   else:p2={}
   print(json.dumps({'device':tag,'bgStatus':t1,'initial':p1,'after_move':p2,'errors':errors,'failed':failed,'screenshots':[str(out)]},ensure_ascii=False))
   context.close()
  browser.close()
finally:
 server.terminate();server.wait(timeout=4)
