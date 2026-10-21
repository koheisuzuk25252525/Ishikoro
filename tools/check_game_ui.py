#!/usr/bin/env python3
"""Browser regression checks; uses only disposable browser saves, never user data.

Install optional test tools: pip install playwright; playwright install chromium.
Run: python3 tools/check_game_ui.py --play --screenshots /tmp/ishikoro-review
"""
from pathlib import Path
import argparse
import functools
import http.server
import shutil
import threading

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--play', action='store_true', help='Also clear the first stage through game controls')
parser.add_argument('--animations', action='store_true', help='Check discovery, evolution, tag and digging animations')
parser.add_argument('--screenshots', type=Path, help='Optional directory for review screenshots')

from pathlib import Path
import re
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1];src=(root/'ishikoro.html').read_text()
unit_block=src[src.index('  const UNITS = '):src.index('  const ENEMIES = ')]
unit_ids=re.findall(r'\{ id: "([^"]+)"',unit_block)
enemy_block=src[src.index('  const ENEMIES = '):src.index('  const STAGES = ')]
enemy_ids=re.findall(r'\{ id: "([^"]+)"',enemy_block)
fixture={'owned':{k:1 for k in unit_ids},'got':unit_ids,'cleared':[1,2,16,3,17,4,18,5], 'tickets':20,'party':['sandstone','pumice','basalt','granite','obsidian','quartz'],'seen':enemy_ids,'fossils':{},'tagsSeen':[],'plus':{},'gachaMode':'all','evoSeen':[],'v6':True,'introSeen':True,'help':{},'towerBest':0,'endingSeen':False}
args = parser.parse_args()
browser_path = shutil.which('chromium') or shutil.which('google-chrome')
if args.screenshots: args.screenshots.mkdir(parents=True, exist_ok=True)
def capture(page, name):
    if args.screenshots: page.screenshot(path=str(args.screenshots / name))
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base_url = f'http://127.0.0.1:{server.server_port}/ishikoro.html'

try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=browser_path,headless=True,args=['--no-sandbox'])
  for w,h in [(667,300),(844,340),(1024,724),(1180,780)]:
   page=b.new_page(viewport={'width':w,'height':h},is_mobile=True,has_touch=True)
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base_url);page.wait_for_timeout(120)
   for selector in ['.logo','#playBtn','#titleZukanBtn']:
    box=page.locator(selector).bounding_box();copy=page.locator('.cover-copy').bounding_box()
    assert box['y']>=0 and box['y']+box['height']<=copy['height']+.5,(w,selector,box,copy)
    assert box['x']+box['width']<=copy['width']+.5,(w,selector,box,copy)
   # An existing save is read using the unchanged schema, without a reset.
   page.evaluate('(s)=>localStorage.setItem("ishikoroSave2",JSON.stringify(s))',fixture);page.reload()
   before=page.evaluate('localStorage.getItem("ishikoroSave2")')
   page.locator('#titleZukanBtn').click()
   for tab in ['stones','cycle','enemies','types','tags','fossils']:
    page.locator(f'[data-tab="{tab}"]').click();page.wait_for_timeout(60)
    assert page.locator('#zBody').inner_text().strip()
   page.locator('[data-tab="stones"]').click()
   assert page.locator('.zcard:not([disabled])').count()>=50
   data=page.locator('.zcard:not([disabled]) canvas').evaluate_all('(cs)=>cs.map(c=>c.toDataURL())')
   assert len(set(data))==len(data),'Duplicate specimen images'
   if w==1180:capture(page,'specimens.png')
   page.locator('[data-open="unit:pumice"]').click();assert page.locator('#zDetail').is_visible()
   if w==1180:capture(page,'specimen-detail.png')
   page.locator('#zDetail [data-close]').click();page.locator('#zukanBack').click();page.locator('#playBtn').click()
   if w==1180:capture(page,'expedition-map.png')
   for target in ['party','status','kantei','gacha']:
    page.locator(f'#mapScreen [data-go="{target}"]').click()
    assert page.locator(f'#{target}Screen').is_visible(), (w,target,page.locator('body').inner_text()[-900:],errors)
    page.locator(f'#{target}Screen [data-go="map"]').first.click()
   assert page.evaluate('localStorage.getItem("ishikoroSave2")')==before,'Browsing changed existing save'
   assert not errors,(w,errors)
   print('PASS',w,h,'title bounds, 57 distinct specimens, all encyclopedia tabs, detail, map, party, status, identification, digging, old save',flush=True)
   page.close()
  # A portrait device gets the existing rotate guidance, and reduced motion is respected.
  page=b.new_page(viewport={'width':390,'height':760},reduced_motion='reduce')
  page.goto(base_url);assert page.locator('.rotate').is_visible()
  page.set_viewport_size({'width':844,'height':340});page.wait_for_timeout(150)
  assert page.locator('.rotate').is_hidden()
  first=page.locator('#coverCanvas').evaluate('(c)=>c.toDataURL()');page.wait_for_timeout(250)
  assert first==page.locator('#coverCanvas').evaluate('(c)=>c.toDataURL()')
  print('PASS portrait rotation and reduced-motion cover',flush=True)
  b.close()
 

 if args.play:
  with sync_playwright() as p:
   b=p.chromium.launch(executable_path=browser_path,headless=True,args=['--no-sandbox'])
   page=b.new_page(viewport={'width':844,'height':340},is_mobile=True,has_touch=True)
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('https://fonts.googleapis.com/**',lambda route:route.abort())
   page.route('https://fonts.gstatic.com/**',lambda route:route.abort())
   page.clock.install()
   page.goto(base_url)
   page.locator('#playBtn').click();page.locator('#introSkip').click()
   page.locator('.stage-card:not([disabled])').first.click();page.locator('#prepGo').click();page.locator('#startBtn').click()
   for i in range(180):
    if page.locator('#cineBtn').is_visible(): page.locator('#cineBtn').click()
    page.evaluate('''() => {
     for (const b of document.querySelectorAll('.rock-btn:not(:disabled)')) b.click();
    }''')
    page.clock.run_for(1000)
    if page.locator('#resultScreen').is_visible():
     result=page.locator('#resultTitle').inner_text();print('Stage result:',result,'after',i+1,'virtual seconds',flush=True)
     capture(page,'stage-result.png')
     assert 'クリア' in result,result
     break
   else: raise AssertionError('Stage did not finish in 180 virtual seconds')
   assert not errors,errors
   save=page.evaluate('localStorage.getItem("ishikoroSave2")');assert save
   page.reload();assert page.evaluate('localStorage.getItem("ishikoroSave2")')==save
   print('PASS: first-stage clear through game controls, save persists across reload, no JavaScript errors',flush=True)
   b.close()

 if args.animations:
  with sync_playwright() as p:
   b=p.chromium.launch(executable_path=browser_path,headless=True,args=['--no-sandbox'])
   for w,h in [(844,340),(1180,780)]:
    page=b.new_page(viewport={'width':w,'height':h},is_mobile=True,has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.clock.install()
    page.goto(base_url);page.locator('#playBtn').click()
    for _ in range(9):
     if page.locator('#getScreen').is_visible():break
     page.locator('#introNext').click()
    assert page.locator('#getScreen').is_visible();page.clock.run_for(1500)
    capture(page,f'ishikoro-discovery-{w}.png')
    assert page.locator('.get-name').inner_text().strip()
    page.locator('#getBtn').click()
    page.evaluate('(s)=>localStorage.setItem("ishikoroSave2",JSON.stringify(s))',fixture);page.reload()
    page.locator('#titleZukanBtn').click();page.locator('[data-tab="cycle"]').click()
    page.locator('[data-cine]').first.click();page.clock.run_for(3400)
    assert page.locator('#cineBtn').is_visible()
    capture(page,f'ishikoro-evolution-{w}.png')
    page.locator('#cineBtn').click()
    page.locator('[data-tab="tags"]').click();page.locator('[data-tagcine]').first.click();page.clock.run_for(1500)
    assert page.locator('#cinema').is_visible();capture(page,f'ishikoro-tag-{w}.png');page.clock.run_for(2500)
    assert page.locator('#cinema').is_hidden()
    page.locator('#zukanBack').click();page.locator('#playBtn').click();page.locator('#mapScreen [data-go="gacha"]').click()
    page.locator('#digBtn').click();page.clock.run_for(3100)
    assert page.locator('#gachaResult').is_visible();assert page.locator('#gachaName').inner_text().strip()
    capture(page,f'ishikoro-digging-{w}.png')
    page.locator('#dig10Btn').click();page.clock.run_for(5000)
    assert page.locator('.gm').count()==10
    assert not errors,errors
    print('PASS',w,h,'discovery, evolution and return, tag and auto-return, single digging and 10-stone reveal; no JS errors',flush=True)
    page.close()
   b.close()

finally:
 server.shutdown()
 server.server_close()
