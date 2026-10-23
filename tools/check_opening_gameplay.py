#!/usr/bin/env python3
"""Exercise the real opening, strategy, save, transition and lifecycle paths.

Requires the same Playwright installation as check_game_ui.py. The read-only
probe is injected into the served response only, never into the game file.
All saves belong to disposable browser contexts. No player data is accessed.
"""
from __future__ import annotations

import argparse
import base64
import functools
import http.server
import json
import shutil
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROBE = r"""
window.__gameCheck = () => ({
  screen: currentScreen, stage: stageDef.id, reward: stageDef.reward,
  save: JSON.parse(JSON.stringify(SAVE)), cineTime: cineT,
  suspended: appSuspended, trialLast: TRIAL_LAST, hard: {...HARD},
  stages: STAGES.map(s => ({id:s.id, no:s.no, castle:s.castle, mult:s.mult})),
  game: G && {time:G.clock, over:G.over, paused:G.paused, cinema:G.cinema,
    hp:G.boxHP, max:G.boxMax, castle:G.castleHP, spawn:G.spawnN,
    good:G.batsugun, magma:G.magma, sed:G.sed, help:G.help,
    effects:G.fx.length, review:JSON.parse(JSON.stringify(G.review))}
});
"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class Checks:
    def __init__(self, browser, url, source, output):
        self.browser = browser
        self.url = url
        self.source = source
        self.output = output
        self.results = []
        self.completed = []

    def new_page(self, fixture=None, seed=713, source=None):
        page = self.browser.new_page(
            viewport={"width": 844, "height": 340}, is_mobile=True, has_touch=True
        )
        page.set_default_timeout(6000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        body = (source or self.source).replace(
            "})();\n</script>", PROBE + "\n})();\n</script>", 1
        )
        assert PROBE in body, "Could not install the read-only probe"
        page.route(
            "**/ishikoro.html",
            lambda route: route.fulfill(body=body, content_type="text/html; charset=utf-8"),
        )
        page.add_init_script(
            f"Math.random=(()=>{{let n={seed};return()=>((n=(n*1664525+1013904223)>>>0)/4294967296)}})();"
            "const AC=window.AudioContext;if(AC)window.AudioContext=class extends AC{"
            "constructor(...args){super(...args);window.__testAudio=this;}};"
        )
        page.clock.install()
        page.goto(self.url)
        if fixture is not None:
            page.evaluate(
                "s=>{localStorage.setItem('ishikoroSave2',JSON.stringify(s));"
                "localStorage.setItem('ishikoroHowto3','true')}", fixture
            )
            page.reload()
        return page, errors

    @staticmethod
    def state(page):
        return page.evaluate("__gameCheck()")

    def screenshot(self, page, name):
        if self.output:
            page.screenshot(path=str(self.output / name))

    def passed(self, name):
        self.completed.append(name)
        print("PASS:", name, flush=True)

    def play_battle(self, page, ids=None, evolve=True, limit=220):
        """Fixed-cadence DOM input policy, not a model of a child's play speed.

        Actual pointer checks are used at entry, modal acknowledgements and
        stage transitions. Combat policies call enabled buttons at 500ms steps
        so comparing strategies is not dominated by pointer auto-wait time.
        """
        feedback = []
        for _ in range(limit * 2):
            state = self.state(page)
            game = state["game"]
            if game["over"]:
                return state, feedback
            if page.locator("#cineBtn").is_visible():
                page.locator("#cineBtn").click()
            if not game["cinema"] and not game["paused"]:
                page.evaluate(
                    """({ids,evolve})=>{
                      const buttons=[...document.querySelectorAll('.rock-btn')];
                      if(ids)buttons.sort((a,b)=>ids.indexOf(a.id.slice(7))-ids.indexOf(b.id.slice(7)));
                      for(const button of buttons){
                        if(button.disabled || (ids && !ids.includes(button.id.slice(7))))continue;
                        const changing=button.classList.contains('evolve');
                        if(changing&&!evolve)continue;
                        button.click();
                        if(changing)break;
                      }
                    }""", {"ids": ids, "evolve": evolve}
                )
            page.clock.run_for(500)
            state = self.state(page)
            assert state["game"]["effects"] <= 64, "Unbounded effect count"
            if page.locator("#battleFeedback").is_visible():
                text = page.locator("#battleFeedback").inner_text()
                if text not in feedback:
                    feedback.append(text)
        raise AssertionError(f"Battle did not finish: {self.state(page)}")

    def walkthrough(self):
        page, errors = self.new_page()
        page.locator("#playBtn").click()
        assert self.state(page)["screen"] == "battle"
        assert page.locator("#howtoScreen").is_hidden()
        assert page.locator(".rock-btn").count() == 2
        assert set(self.state(page)["save"]["owned"]) == {"sandstone", "pumice"}
        page.locator("#deploy-sandstone").click()  # A real first touch.
        assert self.state(page)["game"]["spawn"] == 1
        fixtures = {}
        for number, stage_id in enumerate((1, 2, 16), 1):
            assert self.state(page)["stage"] == stage_id
            fixtures[number] = self.state(page)["save"]
            end, _ = self.play_battle(page)
            assert "クリア" in page.locator("#resultTitle").inner_text()
            assert end["game"]["time"] < 180
            assert stage_id in end["save"]["cleared"]
            assert page.locator(".battle-review").inner_text().strip()
            self.results.append({"case": "opening", "stage": number, **end["game"]})
            reward = end["reward"]
            assert end["save"]["owned"][reward] >= 1
            if page.locator("#getScreen").is_visible():
                # Even a queued/programmatic Next cannot bypass the introduction.
                page.evaluate("document.querySelector('[data-result=next]')?.click()")
                assert page.locator("#prepScreen").is_hidden()
                page.locator("#getBtn").click()
            self.screenshot(page, f"opening-{number}-result.png")
            if number < 3:
                page.locator('[data-result="next"]').click()
                page.locator("#prepGo").click()  # Must not be covered by result.
                page.clock.run_for(1000)
                assert page.locator("#getScreen").is_hidden(), "Stale reward popup"
        saved = page.evaluate("localStorage.getItem('ishikoroSave2')")
        page.reload()
        assert page.evaluate("localStorage.getItem('ishikoroSave2')") == saved
        page.locator("#playBtn").click()
        assert page.locator("#mapScreen").is_visible()
        assert not errors, errors
        final_save = self.state(page)["save"]
        page.close()
        self.passed("fresh save: two-touch first deployment, stages 1→2→3, reward/Next order, reload and resume")
        return fixtures, final_save

    def strategies(self, fixtures):
        cases = (
            (2, "light-only", ["pumice"], False, False),
            (2, "sharp-with-front", ["sandstone", "obsidian"], True, True),
            (3, "no-evolution", ["sandstone", "pumice"], False, False),
            (3, "evolution", ["sandstone", "pumice"], True, True),
        )
        for number, name, ids, evolve, expected_win in cases:
            page, errors = self.new_page(fixtures[number])
            page.locator("#playBtn").click()
            page.locator(f'[data-stage="{2 if number == 2 else 16}"]').click()
            page.locator("#prepGo").click()
            end, feedback = self.play_battle(page, ids, evolve)
            won = "クリア" in page.locator("#resultTitle").inner_text()
            assert won == expected_win, (name, end)
            review = page.locator(".battle-review").inner_text()
            if won:
                assert end["game"]["good"] > 0
                assert "きいた" in review, review
            else:
                assert "つぎは" in review or "へんしん" in review or "つれていこう" in review, review
                page.locator('[data-result="help"]').click()
                page.locator("#prepGo").click()
                retry = self.state(page)["game"]
                assert retry["help"] == 1 and retry["max"] == 1875
                assert retry["magma"] >= 270 and retry["sed"] >= 9
            assert not errors, errors
            self.results.append({"case": name, "stage": number, "won": won,
                                 "result_text": review, "feedback": feedback, **end["game"]})
            self.screenshot(page, f"strategy-{name}.png")
            page.close()
            self.passed(f"fixed initial seed 713: stage {number} {name} → {'win' if won else 'loss, help remains usable'}")

    def legacy_saves(self):
        party = ["sandstone", "pumice", "shale", "basalt", "quartz", "granite"]
        legacy = {"owned": {id: 3 for id in party}, "got": party.copy(), "party": party,
                  "cleared": [1, 2], "tickets": 21, "introSeen": True, "v6": True,
                  "futureField": {"keep": 42}}
        page, errors = self.new_page(legacy)
        page.locator("#dataBtn").click()

        def exported():
            code = page.locator("#dataCode").input_value()
            assert code.startswith("ISHI1.")
            return json.loads(base64.b64decode(code[6:]))

        current = exported()
        for key in ("party", "cleared", "tickets", "futureField"):
            assert current[key] == legacy[key]
        assert current["owned"]["obsidian"] == 1
        code = "ISHI1." + base64.b64encode(json.dumps(legacy, ensure_ascii=False).encode()).decode()
        page.locator("#dataIn").fill(code)
        page.locator("#dataLoad").click()
        page.locator("#playBtn").click()  # Old missing stars used to crash here.
        assert page.locator("#mapScreen").is_visible()
        page.locator('#mapScreen [data-go="title"]').click()
        page.locator("#dataBtn").click()
        again = exported()
        assert again["owned"]["obsidian"] == 1 and again["party"] == party
        assert again["futureField"] == legacy["futureField"]
        assert "stars" in again and "found" in again and "help" in again
        preserved = page.evaluate("localStorage.getItem('ishikoroSave2')")
        for invalid in ("ISHI1.bad", "ISHI1." + base64.b64encode(b'{"owned":null,"party":[],"cleared":[]}').decode()):
            page.locator("#dataIn").fill(invalid)
            page.locator("#dataLoad").click()
            assert page.evaluate("localStorage.getItem('ishikoroSave2')") == preserved
        assert not errors, errors
        page.close()
        self.passed("legacy local save and ISHI1 import: defaults, progress, levels, full party, unknown fields, invalid-code preservation")

    def lifecycle(self):
        page, errors = self.new_page()
        page.locator("#playBtn").click()
        for selector in (".rock-btn", "#pauseBtn", "#speedBtn"):
            for box in page.locator(selector).evaluate_all("es=>es.map(e=>e.getBoundingClientRect().toJSON())"):
                assert box["width"] >= 44 and box["height"] >= 44
        assert page.locator("#battleStatus").is_visible()
        page.locator("#deploy-sandstone").click()
        page.clock.run_for(15000)
        assert page.locator("#deploy-sandstone .name").inner_text() == "さがん"
        assert page.locator("#deploy-sandstone .rock-action").inner_text() == "へんしん！"
        assert "けいがん" in page.locator("#deploy-sandstone").get_attribute("aria-label")
        page.locator("#deploy-sandstone").click()
        assert page.locator("#cinema").is_visible()
        page.clock.run_for(250)
        page.evaluate("dispatchEvent(new Event('ishikoro:background'))")
        before = self.state(page)
        page.wait_for_function("__testAudio.state === 'suspended'")
        page.clock.run_for(4000)
        after = self.state(page)
        assert after["game"]["time"] == before["game"]["time"]
        assert after["cineTime"] == before["cineTime"]
        page.evaluate("dispatchEvent(new Event('ishikoro:active'))")
        page.clock.run_for(1200)
        assert self.state(page)["game"]["paused"]
        assert self.state(page)["cineTime"] == before["cineTime"]
        assert page.evaluate("__testAudio.state") == "suspended"
        # Do not lose the pending transformation while reading the portrait book.
        page.set_viewport_size({"width": 390, "height": 760})
        page.locator("#rotateOk").click()
        assert page.locator("#zukanScreen").is_visible()
        page.locator("#zukanBack").click()
        assert page.locator("#rotate").is_visible()
        page.set_viewport_size({"width": 844, "height": 340})
        assert page.locator("#pauseScreen").is_visible()
        assert page.locator("#cinema").is_visible()
        page.locator("#resumeBtn").click()
        page.wait_for_function("__testAudio.state === 'running'")
        page.clock.run_for(3500)
        page.locator("#cineBtn").click()
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
        time = self.state(page)["game"]["time"]
        page.clock.run_for(2000)
        assert self.state(page)["game"]["time"] == time
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))")
        assert page.locator("#pauseScreen").is_visible()
        page.locator("#resumeBtn").click()
        page.clock.run_for(500)
        assert self.state(page)["game"]["time"] > time
        assert not errors, errors
        page.close()
        self.passed("44px targets, explicit evolution, simulated native/browser interruption, WebAudio state, portrait book and gesture-only resume")

    def trial_and_difficulty(self, fixture):
        trial = self.source.replace('const EDITION = "family";', 'const EDITION = "trial";', 1)
        old = json.loads(json.dumps(fixture))
        old["cleared"] = list(range(1, 26))
        page, errors = self.new_page(old, source=trial)
        page.locator("#playBtn").click()
        state = self.state(page)
        locked = state["stages"][state["trialLast"]]["id"]
        assert page.locator(f'[data-stage="{locked}"]').is_disabled()
        # Report the pre-existing boundary rather than quietly rebalance stage 5.
        stages = state["stages"]
        hp_ramp = state["hard"]["hp"] - 1
        previous = stages[3]["mult"] * (1 + hp_ramp * .5)
        following = stages[4]["mult"] * (1 + hp_ramp * .75)
        print(f"RISK (source analysis, not a win/loss test): stage 4→5 enemy HP coefficient +{(following/previous-1)*100:.1f}%; later stages need separate playtesting", flush=True)
        assert not errors, errors
        page.close()
        self.passed("trial boundary still locks the next chapter")

    def stale_digging(self, fixture):
        # The existing 'unfound only' mode guarantees a new stone, so the
        # test actually schedules an introduction before leaving the screen.
        old = json.loads(json.dumps(fixture))
        old["cleared"] = [1, 2, 16, 3, 17, 4, 18, 5]
        old["tickets"] = 20
        old["gachaMode"] = "all"
        page, errors = self.new_page(old)
        page.locator("#playBtn").click()
        page.locator('#mapScreen [data-go="gacha"]').click()
        page.locator('[data-mode="new"]').click()
        count = len(self.state(page)["save"]["owned"])
        page.locator("#digBtn").click()
        assert len(self.state(page)["save"]["owned"]) == count + 1
        page.clock.run_for(2400)
        page.locator('#gachaScreen [data-go="map"]').click()
        page.clock.run_for(1400)
        assert page.locator("#getScreen").is_hidden()
        assert page.locator("#mapScreen").is_visible()
        assert not errors, errors
        page.close()
        self.passed("leaving digging before delayed introduction cannot cover another screen")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=shutil.which("chromium") or shutil.which("google-chrome"),
                headless=True, args=["--no-sandbox"]
            )
            try:
                checks = Checks(browser, f"http://127.0.0.1:{server.server_port}/ishikoro.html",
                                (ROOT / "ishikoro.html").read_text(), args.screenshots)
                fixtures, final_save = checks.walkthrough()
                checks.strategies(fixtures)
                checks.legacy_saves()
                checks.lifecycle()
                checks.trial_and_difficulty(final_save)
                checks.stale_digging(final_save)
                if args.screenshots:
                    (args.screenshots / "gameplay-metrics.json").write_text(json.dumps(
                        {"method": "PC Chromium, virtual game clock; not a human playtest",
                         "completed": checks.completed, "runs": checks.results},
                        ensure_ascii=False, indent=2
                    ) + "\n")
                print(f"Completed {len(checks.completed)} gameplay regression cases.", flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
