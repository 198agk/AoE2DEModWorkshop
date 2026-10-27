"""Screenshot the rail with the object-list band filled in.

The rail's third band only has content once a player has saved sentences, and
the real recipes.json on this machine is empty.  Rather than writing test data
into the player's file, this intercepts /api/recipes in the browser and serves
three fake rows -- the point is to see the band's layout at 400px tall, not to
prove the save button works (design_acceptance.py covers the API).
"""
import os
import sys
import json
from playwright.sync_api import sync_playwright

URL = os.environ.get("SHOT_URL", "http://127.0.0.1:7811/")
OUT = r"D:\Software\AI\帝国项目\_shots\now"
W = int(os.environ.get("SHOT_W", "1237"))
H = int(os.environ.get("SHOT_H", "880"))

FAKE = {"ok": True, "file": "(intercepted)", "recipes": [
    {"name": "弓手多两条命", "sentences": [
        "弓箭手生命值改成 60", "弓箭手造价减少 10 木材"], "count": 2,
     "saved_at": "2026-10-26 21:04", "note": ""},
    {"name": "城堡便宜一点", "sentences": [
        "城堡造价减少 50 石头", "城堡建造时间减少 30 秒"], "count": 2,
     "saved_at": "2026-10-25 18:12", "note": ""},
    {"name": "测试用三句", "sentences": [
        "剑士攻击力加 2", "剑士生命值加 10", "剑士移动速度加 0.1"],
     "count": 3, "saved_at": "2026-10-24 09:30", "note": ""},
]}

os.makedirs(OUT, exist_ok=True)
VIEWS = sys.argv[1:] or ["home", "mods"]

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.route("**/api/recipes",
             lambda r: r.fulfill(status=200,
                                content_type="application/json",
                                body=json.dumps(FAKE, ensure_ascii=False)))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1600)
    for v in VIEWS:
        try:
            pg.click("#nav-" + v, timeout=2500)
        except Exception:
            pass
        pg.wait_for_timeout(800)
        path = os.path.join(OUT, "rail-%s.png" % v)
        pg.screenshot(path=path)
        print("wrote", path)
    # Measure the three rail bands so the numbers travel with the picture.
    box = pg.evaluate("""() => {
      const g = (s) => { const n = document.querySelector(s);
        if (!n) return null; const r = n.getBoundingClientRect();
        return [Math.round(r.top), Math.round(r.height)]; };
      return {rail: g('.rail'), nav: g('.railnav'),
              group: g('.railgroup'), list: g('#rail-recent'),
              foot: g('.railfoot'),
              rows: document.querySelectorAll('#rail-recent .rrow').length,
              scrollH: (document.querySelector('#rail-recent')||{}).scrollHeight};
    }""")
    print("geometry", json.dumps(box))
    b.close()
