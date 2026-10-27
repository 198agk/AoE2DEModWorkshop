"""Draw boxes around the three unfinished things and shoot it.

"Show me where" is a question about pixels, so the answer has to be pixels:
each problem gets a labelled rectangle on the real page at the real window size.
"""
import json
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"
OUT = r"D:\Software\AI\帝国项目\_shots\now"

MARK_CSS = """
.mark {
  position: absolute; z-index: 9999;
  border: 2px solid #cf222e;
  background: rgba(207, 34, 46, .07);
  border-radius: 6px;
  pointer-events: none;
}
.mark::after {
  content: attr(data-tag);
  position: absolute; left: -2px; top: -26px;
  background: #cf222e; color: #fff;
  font: 600 12px/1 system-ui, "Microsoft YaHei", sans-serif;
  padding: 6px 9px; border-radius: 4px; white-space: nowrap;
}
"""

DRAW = """(spots) => {
  document.querySelectorAll('.mark').forEach(n => n.remove());
  const host = document.body;
  for (const s of spots) {
    const el = document.querySelector(s.sel);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    const box = document.createElement('div');
    box.className = 'mark';
    box.setAttribute('data-tag', s.tag);
    Object.assign(box.style, {
      left: (r.left + scrollX) + 'px',
      top: (r.top + scrollY) + 'px',
      width: r.width + 'px',
      height: r.height + 'px'
    });
    host.appendChild(box);
  }
  return document.querySelectorAll('.mark').length;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1899, "height": 1235})
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1600)
    pg.add_style_tag(content=MARK_CSS)

    # ---------- 1: the 15 dead cards ----------
    pg.click("#nav-intents")
    pg.wait_for_timeout(700)
    n = pg.evaluate(DRAW, [
        {"sel": "#intents", "tag": "① 15 张卡，点了没反应（全部 div，无 click）"},
    ])
    print("intents marks:", n)
    pg.screenshot(path=OUT + r"\mark_intents.png")

    # ---------- 2: the empty lower half of home ----------
    pg.click("#nav-home")
    pg.wait_for_timeout(700)
    spots = [
        {"sel": "#preview", "tag": "② 主区到这里就没了，下方 600px 全空"},
    ]
    pg.evaluate(DRAW, spots)
    # a box for the empty region itself
    pg.evaluate("""() => {
      const last = document.querySelector('#view-home .box:last-child');
      const r = last.getBoundingClientRect();
      const box = document.createElement('div');
      box.className = 'mark';
      box.setAttribute('data-tag', '② 下方全空：页面 1235px 高，内容到 610px 结束');
      Object.assign(box.style, {
        left: (r.left + scrollX) + 'px',
        top: (r.bottom + 16 + scrollY) + 'px',
        width: r.width + 'px',
        height: (innerHeight - r.bottom - 40) + 'px'
      });
      document.body.appendChild(box);
    }""")
    pg.screenshot(path=OUT + r"\mark_home.png")

    # ---------- 3: recycle bin has no entry ----------
    pg.click("#nav-mods")
    pg.wait_for_timeout(900)
    pg.evaluate(DRAW, [
        {"sel": "#mods .mod:first-child .remove",
         "tag": "③ 只能「放进回收站」，界面上没有「回收站在哪 / 怎么拿回来」"},
    ])
    # does any element mention the bin as an entry point?
    found = pg.evaluate("""() => {
      const words = ['回收站', '恢复', '还原'];
      const hits = [];
      for (const el of document.querySelectorAll('button, a')) {
        const t = (el.textContent || '').trim();
        if (words.some(w => t.includes(w))) hits.push(t);
      }
      return hits;
    }""")
    print("bin-related buttons:", json.dumps(found, ensure_ascii=False))
    pg.screenshot(path=OUT + r"\mark_mods.png")

    # ---------- the real geometry ----------
    geo = pg.evaluate("""() => ({
      vw: innerWidth, vh: innerHeight,
      docH: document.documentElement.scrollHeight,
      contentBottom: Math.round(document.querySelector('#view-mods .box').getBoundingClientRect().bottom),
      shellW: Math.round(document.querySelector('.shell').getBoundingClientRect().width)
    })""")
    print("geometry", json.dumps(geo))
    b.close()
