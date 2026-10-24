#!/usr/bin/env python3
"""Play both routes of the standalone adventure in disposable browser contexts."""
from pathlib import Path
import argparse
import re
import xml.etree.ElementTree as ET
import shutil
import http.server
import functools
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
def check_launch_wiring():
    """Check the cross-file launch contract; no Apple SDK is required."""
    project=(ROOT/'Ishikoro.xcodeproj/project.pbxproj').read_text()
    configs=re.findall(r'isa = XCBuildConfiguration; buildSettings = \{(.*?)\}; name = (Debug|Release);',project,re.S)
    debug=[settings for settings,name in configs if name=='Debug']
    assert debug, 'No Debug build configuration'
    assert any(re.search(r'SWIFT_ACTIVE_COMPILATION_CONDITIONS\s*=\s*"[^";]*\bDEBUG\b',settings) for settings in debug), 'Swift #if DEBUG is never enabled: adventure launch would load the original game'
    assert not any(re.search(r'SWIFT_ACTIVE_COMPILATION_CONDITIONS\s*=\s*"[^";]*\bDEBUG\b',settings) for settings,name in configs if name=='Release'), 'Prototype must remain disabled in Release'
    schemes=ROOT/'Ishikoro.xcodeproj/xcshareddata/xcschemes'
    adventure=ET.parse(schemes/'IshikoroAdventure.xcscheme').getroot().find('LaunchAction')
    assert adventure.attrib['buildConfiguration']=='Debug'
    args=adventure.findall('./CommandLineArguments/CommandLineArgument')
    assert any(a.attrib.get('argument')=='--adventure-prototype' and a.attrib.get('isEnabled')=='YES' for a in args)
    normal=ET.parse(schemes/'Ishikoro.xcscheme').getroot().find('LaunchAction')
    assert not normal.findall('./CommandLineArguments/CommandLineArgument')
    assert 'path = prototypes/adventure.html;' in project
    assert (ROOT/'prototypes/adventure.html').is_file()
    print('PASS Debug condition, adventure launch argument, original scheme, Release isolation, prototype resource',flush=True)

def main():
    check_launch_wiring()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshots',type=Path,default=Path('/tmp/ishikoro-adventure'))
    args=parser.parse_args();args.screenshots.mkdir(parents=True,exist_ok=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/prototypes/adventure.html'
    try:
        run(url,args)
    finally:
        server.shutdown();server.server_close()

def run(url,args):
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
        try:
            for size in [(844,390),(1180,780),(390,844)]:
                page=browser.new_page(viewport={'width':size[0],'height':size[1]},is_mobile=True,has_touch=True)
                errors=[];requests=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:requests.append(r.url))
                page.add_init_script("const AC=window.AudioContext;if(AC)window.AudioContext=class extends AC{constructor(...a){super(...a);window.__audio=this;}}")
                page.goto(url)
                page.evaluate("localStorage.setItem('ishikoroSave2','preserved-save');localStorage.setItem('ishikoroMods','preserved-mods')")
                before=page.evaluate('JSON.stringify({...localStorage})')
                page.locator('#start').click()
                if size==(844,390):
                    page.locator('#sound').click()
                    page.wait_for_function("__audio.state==='running'")
                    page.evaluate("dispatchEvent(new Event('ishikoro:background'))")
                    page.wait_for_function("__audio.state==='suspended'")
                    page.evaluate("dispatchEvent(new Event('ishikoro:active'))")
                    assert page.evaluate("__audio.state")=='suspended'
                    page.locator('#sound').click()
                # A failed experiment gives a reason and remains immediately playable.
                page.locator('[data-site="roots"]').click()
                assert 'まだ' in page.locator('#messageTitle').inner_text()
                assert page.locator('#next').is_hidden()
                page.locator('[data-rock="obsidian"]').click();page.locator('[data-site="roots"]').click()
                assert page.locator('#next').is_visible()
                page.locator('#undo').click()
                assert page.locator('#next').is_hidden()
                page.locator('[data-site="roots"]').click()
                page.screenshot(path=str(args.screenshots/f'roots-{size[0]}.png'))
                page.locator('#next').click()
                page.locator('[data-site="wind"]').click()
                assert 'かたさは べつ' in page.locator('#messageTitle').inner_text()
                page.locator('#hint').click();assert page.locator('#explanation').is_visible()
                page.locator('#closeExplanation').click()
                page.locator('#evolve').click()
                assert page.locator('[data-rock="quartzite"]').get_attribute('aria-pressed')=='true'
                page.locator('#undo').click();assert page.locator('[data-rock="sandstone"]').is_visible()
                page.locator('#evolve').click();page.locator('[data-site="wind"]').click()
                assert page.locator('#next').is_visible()
                page.screenshot(path=str(args.screenshots/f'wind-{size[0]}.png'))
                page.locator('#next').click()
                assert page.locator('[data-site="finalWind"]').is_disabled()
                page.set_viewport_size({'width':390,'height':844})
                assert page.locator('#place').inner_text().startswith('03')
                page.set_viewport_size({'width':size[0],'height':size[1]})
                page.locator('[data-rock="obsidian"]').click();page.locator('[data-site="finalRoots"]').click()
                assert page.locator('#next').is_hidden()
                assert page.locator('[data-site="finalWind"]').is_enabled()
                page.locator('[data-rock="quartzite"]').click();page.locator('[data-site="finalWind"]').click()
                page.locator('#next').click()
                assert page.locator('#ending').is_visible()
                assert page.locator('#routes > div').count()==3
                page.screenshot(path=str(args.screenshots/f'ending-{size[0]}.png'))
                page.locator('#restart').click()
                # Every scene also has an alternate solution without transformation.
                for site in ['around','shelter','valley']:
                    page.locator('[data-rock="pumice"]').click()
                    page.locator(f'[data-site="{site}"]').click()
                    page.locator('#next').click()
                assert page.locator('#ending').is_visible()
                assert 'かせき' in page.locator('#notes').inner_text()
                assert page.locator('#routes').inner_text().count('まわりみち')==3
                page.locator('#lookBack').click();page.locator('#undo').click()
                assert page.locator('#next').is_hidden()
                assert before==page.evaluate('JSON.stringify({...localStorage})')
                assert all(r==url for r in requests),requests
                assert not errors,errors
                # Tappable controls meet 44px, including actual map placements.
                for selector in ['.stone','.site','#evolve','#undo','#sound','#hint']:
                    for box in page.locator(selector).evaluate_all('es=>es.filter(e=>!e.hidden).map(e=>e.getBoundingClientRect().toJSON())'):
                        assert box['width']>=44 and box['height']>=44,(selector,box)
                page.screenshot(path=str(args.screenshots/f'play-{size[0]}.png'))
                print('PASS',size,'direct and alternate routes, failure/retry, undo, transformation, hint, replay, original save preserved, offline, 44px targets',flush=True)
                page.close()
        finally:browser.close()
if __name__=='__main__':main()
