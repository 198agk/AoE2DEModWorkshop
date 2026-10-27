"""How much of the #say placeholder is actually clipped?

`saying "6 example lines" is a claim about text that must be readable; the
textarea is 132px tall and the hint text has six lines in it, so measure the
overflow instead of trusting the comment next to the rule.
"""
import json
from playwright.sync_api import sync_playwright

JS = """() => {
  const t = document.querySelector('#say');
  const cs = getComputedStyle(t);
  const lines = (t.placeholder || '').split('\\n').length;
  const lh = parseFloat(cs.lineHeight);
  const pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  return {
    lines: lines,
    lineHeight: lh,
    clientH: t.clientHeight,
    scrollH: t.scrollHeight,
    overflow: t.scrollHeight - t.clientHeight,
    needed: Math.ceil(lines * lh + pad + 2)
  };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1237, "height": 880})
    pg.goto("http://127.0.0.1:7811/", wait_until="networkidle")
    pg.wait_for_timeout(1500)
    print(json.dumps(pg.evaluate(JS), ensure_ascii=False, indent=1))
    b.close()
