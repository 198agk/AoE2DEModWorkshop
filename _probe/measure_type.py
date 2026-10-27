"""What the type and density look like at the size the player actually uses.

The gates run at 1237 and 1100 because those were the widths in DESIGN.md §0.
The real window is 1899x1235, and at that width a layout can pass every gate and
still look wrong: a 13px line of Chinese running 1240px wide is ~95 characters,
which is past the point where the eye loses the start of the next line.
"""
import json
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7811/"

JS = r"""() => {
  const px = (v) => parseFloat(v) || 0;
  const box = (el) => { const r = el.getBoundingClientRect();
    return {w: Math.round(r.width), h: Math.round(r.height),
            l: Math.round(r.left), t: Math.round(r.top)}; };
  const cs = (el) => getComputedStyle(el);

  // Characters per line, measured rather than guessed: create a span with the
  // same font and count how many of a representative glyph fit.
  const charsPerLine = (el) => {
    const c = cs(el);
    const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;'
      + 'font:' + c.font;
    probe.textContent = '\u6539\u53d8\u5355\u4f4d\u5c5e\u6027\u7684\u6570\u503c';  // CJK sample
    document.body.appendChild(probe);
    const perGlyph = probe.getBoundingClientRect().width / 10;
    probe.remove();
    const inner = el.clientWidth - px(c.paddingLeft) - px(c.paddingRight);
    return Math.round(inner / perGlyph);
  };

  const out = {};
  const hint = document.querySelector('#view-home .hint');
  const say = document.querySelector('#say');
  const h1 = document.querySelector('header h1');
  const h2 = document.querySelector('#view-home .box > h2');
  const shell = document.querySelector('.shell');
  const rail = document.querySelector('.rail');
  const boxEl = document.querySelector('#view-home .box');

  out.viewport = {w: innerWidth, h: innerHeight};
  out.shell = box(shell);
  out.rail = box(rail);
  out.card = box(boxEl);
  out.title = {size: cs(h1).fontSize, weight: cs(h1).fontWeight, box: box(h1)};
  out.cardTitle = {size: cs(h2).fontSize, weight: cs(h2).fontWeight};
  out.body = {size: cs(hint).fontSize, lineHeight: cs(hint).lineHeight};
  out.lineLength = {
    hintChars: charsPerLine(hint),
    hintWidth: Math.round(hint.getBoundingClientRect().width),
    sayChars: charsPerLine(say),
    sayWidth: Math.round(say.clientWidth)
  };
  // how much horizontal room is the card actually using vs the window
  out.fill = {
    cardOfShell: Math.round(boxEl.getBoundingClientRect().width / shell.getBoundingClientRect().width * 100),
    shellOfWindow: Math.round(shell.getBoundingClientRect().width / innerWidth * 100)
  };
  // vertical: how much of the window has content in it
  const views = [...document.querySelectorAll('.view')];
  const on = views.find(v => v.classList.contains('on'));
  out.vertical = {
    contentBottom: on ? Math.round(on.getBoundingClientRect().bottom) : null,
    windowH: innerHeight,
    emptyBelow: on ? Math.round(innerHeight - on.getBoundingClientRect().bottom) : null
  };
  // type ramp as painted, for the record
  const sizes = {};
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    const c = cs(el);
    if (c.display === 'none' || c.visibility === 'hidden') continue;
    sizes[c.fontSize] = (sizes[c.fontSize] || 0) + 1;
  }
  out.typeRamp = sizes;
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((1899, 1235), (1237, 880)):
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_timeout(1500)
        print("=" * 60)
        print("%dx%d" % (w, h))
        print(json.dumps(pg.evaluate(JS), ensure_ascii=False, indent=1))
        pg.close()
    b.close()
