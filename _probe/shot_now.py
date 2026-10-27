"""Screenshot the page at its real window width, one file per view.

Numbers come from render_acceptance.py; this is only so a human can look at the
thing the numbers describe.  Kept separate on purpose -- a screenshot shows a
symptom, the gate shows the cause, and neither replaces the other.
"""
import os
import sys
from playwright.sync_api import sync_playwright

URL = os.environ.get("SHOT_URL", "http://127.0.0.1:7811/")
OUT = r"D:\Software\AI\帝国项目\_shots\now"
W = int(os.environ.get("SHOT_W", "1237"))
H = int(os.environ.get("SHOT_H", "880"))

os.makedirs(OUT, exist_ok=True)

VIEWS = sys.argv[1:] or ["home", "mods", "editor", "intents"]

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1800)
    for v in VIEWS:
        try:
            pg.click("#nav-" + v, timeout=2500)
        except Exception:
            pass
        pg.wait_for_timeout(900)
        path = os.path.join(OUT, "%s.png" % v)
        pg.screenshot(path=path)
        print("wrote", path)
    b.close()
