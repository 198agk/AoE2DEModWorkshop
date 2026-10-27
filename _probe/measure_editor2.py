"""Does the editor's "改成" button actually brighten when the player types?

The first attempt set input.value from JS and read the style in the same tick,
which is not how a player uses it and may not be how the browser flushes
:placeholder-shown.  This types with the keyboard and waits a frame.
"""
import json
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1237, "height": 880})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1500)
    pg.click("#nav-editor")
    pg.wait_for_timeout(1200)

    sel = "#editor table.f tbody tr:nth-child(1) td.e input"
    btn = "#editor table.f tbody tr:nth-child(1) td.e button"

    def snap(tag):
        v = pg.evaluate("""([s1, s2]) => {
          const i = document.querySelector(s1), b = document.querySelector(s2);
          if (!i || !b) return {missing: [!!i, !!b]};
          const cs = getComputedStyle(b);
          return {value: i.value, placeholder: i.placeholder,
                  matchesPlaceholderShown: i.matches(':placeholder-shown'),
                  color: cs.color, background: cs.backgroundColor,
                  border: cs.borderColor, weight: cs.fontWeight};
        }""", [sel, btn])
        print(tag, json.dumps(v, ensure_ascii=False))

    snap("rest      ")
    pg.click(sel)
    pg.keyboard.type("999")
    pg.wait_for_timeout(300)
    snap("typed     ")
    pg.fill(sel, "")
    pg.wait_for_timeout(300)
    snap("cleared   ")
    b.close()
