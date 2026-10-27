import sys, os
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"
OUT = r"D:\Software\AI\帝国项目\_shots\v2"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1237, "height": 880})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1800)

    # find the rail nav items
    items = pg.evaluate("""() => {
      return [...document.querySelectorAll('.navitem, nav a, nav button')].map((el,i) => ({
        i, tag: el.tagName, cls: el.className, txt: (el.textContent||'').trim(),
        id: el.id
      }));
    }""")
    print("NAV:", items)

    views = pg.evaluate("""() => [...document.querySelectorAll('.view')].map(el => ({
      id: el.id, cls: el.className, hidden: getComputedStyle(el).display
    }))""")
    print("VIEWS:", views)

    # screenshot each nav target
    for it in items:
        if not it["txt"]:
            continue
        try:
            pg.evaluate("""(idx) => {
              const els = [...document.querySelectorAll('.navitem, nav a, nav button')];
              els[idx].click();
            }""", it["i"])
            pg.wait_for_timeout(700)
            safe = "".join(c if c.isalnum() else "_" for c in it["txt"])[:20]
            path = os.path.join(OUT, "view_%s.png" % safe)
            pg.screenshot(path=path)
            print("shot", path)
        except Exception as e:
            print("skip", it["txt"], e)

    b.close()
