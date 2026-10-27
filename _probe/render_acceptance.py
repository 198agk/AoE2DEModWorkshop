"""Render-level acceptance for the workshop page -- the half a text gate cannot see.

Why this exists next to `design_acceptance.py`: that file greps the CSS text.
A text gate can prove "no hex literal"; it cannot prove "the unit list stops at
the card it lives in", "this metadata is readable on a selected row", or "this
arrow is a legal hit target".  Measured 2026-10-26: the text gate was 12/12
green while the live page had a 14000px list inside a 660px box and 454
unreadable text runs.

Each check below asks the browser and prints a measured number, never a verdict.

  R1  a child's box escapes its card, with no scroll container to explain it
  R2  two interactive elements overlap
  R3  rendered font-size census (text nodes actually painted, not declarations)
  R4  contrast, WCAG AA, against the background really behind the glyphs
  R5  hit target under 24x24, counting a negative-inset ::before/::after
  R6  focusable control that no :focus / :focus-visible rule matches
  R7  input with no accessible name (a placeholder is not a name)
  R8  scrollable region that overflows
  R9  page shows a horizontal scrollbar
  R10 an element's text is clipped without ellipsis or wrap

Both widths are real: 1237px is today's window, 1100px the next breakpoint down.

Usage
    py -X utf8 _probe/render_acceptance.py
    py -X utf8 _probe/render_acceptance.py --json out.json
    py -X utf8 _probe/render_acceptance.py http://127.0.0.1:7811/

Budgeted like design_acceptance.py: R3 allows the four token sizes, everything
else is zero.  A check fails only when it exceeds its budget, and every line
prints the number it measured.
"""
import json
import sys

from playwright.sync_api import sync_playwright

DEFAULT_URL = "http://127.0.0.1:7811/"
WIDTHS = (1237, 1100)

# The contract's own numbers, so a budget change is a DESIGN.md change.
BUDGET = {
    "R1": 0,
    "R2": 0,
    "R3": 4,     # --fs-micro / --fs-body / --fs-title / --fs-display
    "R4": 0,
    "R5": 0,
    "R6": 0,
    "R7": 0,
    "R8": None,  # reported, not budgeted: some overflow is the design
    "R9": 0,
    "R10": 0,
}

JS = r"""
() => {
  const name = el => (el.tagName.toLowerCase()
      + (el.id ? '#' + el.id : '')
      + (el.className && typeof el.className === 'string'
         ? '.' + el.className.trim().split(/\s+/).join('.') : '')).slice(0, 64);
  const visible = el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };
  const out = {};

  // ---- R1 ------------------------------------------------------------------
  // A child clipped by a scroll container between it and the card is by design:
  // list panes scroll.  Only an escape nothing explains is a layout leak.
  const scrollAncestor = (el, stop) => {
    let e = el.parentElement;
    while (e && e !== stop) {
      const s = getComputedStyle(e);
      if (/auto|scroll|hidden/.test(s.overflowY + s.overflowX)) return e;
      e = e.parentElement;
    }
    return null;
  };
  const esc = [];
  document.querySelectorAll('.box').forEach(card => {
    const c = card.getBoundingClientRect();
    const cs = getComputedStyle(card);
    card.querySelectorAll('*').forEach(el => {
      if (!visible(el) || scrollAncestor(el, card)) return;
      const r = el.getBoundingClientRect();
      const dy = Math.round(r.bottom - (c.bottom - parseFloat(cs.paddingBottom || 0)));
      const dx = Math.round(r.right - (c.right - parseFloat(cs.paddingRight || 0)));
      if (dy > 2 || dx > 2) esc.push({card: name(card), el: name(el),
        dy: dy, dx: dx, h: Math.round(r.height)});
    });
  });
  esc.sort((a, b) => b.dy - a.dy);
  out.R1_escapes = esc.slice(0, 10);
  out.R1_count = esc.length;

  // ---- R2 ------------------------------------------------------------------
  const inter = [...document.querySelectorAll('button, a, input, select, textarea, [role=switch]')]
    .filter(visible);
  const over = [];
  for (let i = 0; i < inter.length; i++) {
    for (let j = i + 1; j < inter.length; j++) {
      const a = inter[i].getBoundingClientRect(), b = inter[j].getBoundingClientRect();
      const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ox > 2 && oy > 2) over.push({a: name(inter[i]), b: name(inter[j]),
        ox: Math.round(ox), oy: Math.round(oy)});
    }
  }
  out.R2_overlaps = over.slice(0, 10);
  out.R2_count = over.length;

  // ---- R3 ------------------------------------------------------------------
  const sizes = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    if (!el || !visible(el)) continue;
    const fs = getComputedStyle(el).fontSize;
    sizes.set(fs, (sizes.get(fs) || 0) + 1);
  }
  out.R3_fontSizes = [...sizes.entries()].sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));
  out.R3_count = out.R3_fontSizes.length;

  // ---- R4 ------------------------------------------------------------------
  const parse = c => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(x => parseFloat(x));
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  };
  const lum = ({r, g, b}) => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const bgOf = el => {
    let e = el;
    while (e) {
      const c = parse(getComputedStyle(e).backgroundColor);
      if (c && c.a > 0.5) return c;
      e = e.parentElement;
    }
    return {r: 255, g: 255, b: 255, a: 1};
  };
  const ratio = (f, b) => {
    const L1 = lum(f), L2 = lum(b);
    return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
  };
  const low = [];
  const w2 = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while ((n = w2.nextNode())) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    if (!el || !visible(el)) continue;
    const cs = getComputedStyle(el);
    const fg = parse(cs.color);
    if (!fg) continue;
    const bg = bgOf(el);
    const r = ratio(fg, bg);
    const px = parseFloat(cs.fontSize);
    const bold = parseInt(cs.fontWeight, 10) >= 600;
    const need = (px >= 24 || (px >= 18.66 && bold)) ? 3 : 4.5;
    if (r < need) low.push({el: name(el), txt: n.textContent.trim().slice(0, 24),
      ratio: Math.round(r * 100) / 100, need: need, px: px, color: cs.color,
      bg: 'rgb(' + bg.r + ',' + bg.g + ',' + bg.b + ')'});
  }
  out.R4_lowContrast = low.slice(0, 12);
  out.R4_count = low.length;

  // ---- R5 ------------------------------------------------------------------
  // ::before/::after with a NEGATIVE inset paints outside the layout box and
  // still receives the click, so the drawn box is the honest hit target.  A
  // pseudo positioned with `inset: 0` stays inside and must not shrink it.
  const hitBox = el => {
    const r = el.getBoundingClientRect();
    let t = r.top, b = r.bottom, l = r.left, ri = r.right;
    for (const pseudo of ['::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (!cs || cs.content === 'none') continue;
      const d = (cs.inset || '').split(' ').map(v => parseFloat(v));
      if (!d.length || d.some(v => isNaN(v) || v > 0)) continue;
      t += d[0];
      ri -= d.length > 1 ? d[1] : d[0];
      b -= d.length > 2 ? d[2] : d[0];
      l += d.length > 3 ? d[3] : (d.length > 1 ? d[1] : d[0]);
    }
    return {w: Math.round(ri - l), h: Math.round(b - t)};
  };
  const small = [];
  document.querySelectorAll('button, a, [role=switch], .switch').forEach(el => {
    if (!visible(el)) return;
    const s = hitBox(el);
    if (s.w < 24 || s.h < 24) small.push({el: name(el), w: s.w, h: s.h,
      txt: (el.textContent || '').trim().slice(0, 10)});
  });
  out.R5_smallTargets = small.slice(0, 12);
  out.R5_count = small.length;

  // ---- R6 ------------------------------------------------------------------
  // Ask the cascade, not the source: does any focus rule match this element?
  const focusRules = [];
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    for (const rule of rules || []) {
      if (rule.selectorText && /focus/.test(rule.selectorText)) focusRules.push(rule.selectorText);
    }
  }
  const noRing = [], rings = [];
  document.querySelectorAll('button, a, input, select, textarea, [role=switch]').forEach(el => {
    if (!visible(el)) return;
    let hit = false;
    for (const sel of focusRules) {
      for (const one of sel.split(',')) {
        const bare = one.trim().replace(/::?(focus-visible|focus-within|focus)/g, '').trim();
        if (!bare) continue;
        try { if (el.matches(bare)) { hit = true; break; } } catch (e) {}
      }
      if (hit) break;
    }
    (hit ? rings : noRing).push(name(el));
  });
  out.R6_noFocusRule = noRing.slice(0, 12);
  out.R6_count = noRing.length;
  out.R6_focusRules = focusRules.slice(0, 8);

  // ---- R7 ------------------------------------------------------------------
  const unnamed = [];
  document.querySelectorAll('input, select, textarea').forEach(el => {
    if (!visible(el)) return;
    const id = el.id;
    const hasLabel = id && document.querySelector('label[for="' + id + '"]');
    const hasAria = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
    if (!hasLabel && !hasAria) unnamed.push({el: name(el),
      ph: (el.getAttribute('placeholder') || '').slice(0, 16), id: id});
  });
  out.R7_unnamed = unnamed.slice(0, 15);
  out.R7_count = unnamed.length;

  // ---- R8 ------------------------------------------------------------------
  const scrollers = [];
  document.querySelectorAll('*').forEach(el => {
    if (!visible(el)) return;
    const cs = getComputedStyle(el);
    if (!/auto|scroll/.test(cs.overflowY) && !/auto|scroll/.test(cs.overflowX)) return;
    if (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2) {
      scrollers.push({el: name(el), sh: el.scrollHeight, ch: el.clientHeight,
        sw: el.scrollWidth, cw: el.clientWidth, ov: cs.overflowY + '/' + cs.overflowX});
    }
  });
  out.R8_scrollers = scrollers.slice(0, 10);
  out.R8_count = scrollers.length;

  // ---- R9 ------------------------------------------------------------------
  out.R9_docScrollW = Math.round(document.documentElement.scrollWidth);
  out.R9_clientW = Math.round(document.documentElement.clientWidth);
  out.R9_count = out.R9_docScrollW > out.R9_clientW + 1 ? 1 : 0;

  // ---- R10 -----------------------------------------------------------------
  // Text that overflows its own box with no ellipsis and no wrap is silently
  // unreadable.  This is the check that would have caught a 12px label inside a
  // 40px cell.
  const clipped = [];
  document.querySelectorAll('*').forEach(el => {
    if (!visible(el)) return;
    if (el.children.length) return;
    const cs = getComputedStyle(el);
    if (cs.overflow !== 'hidden' && cs.overflow !== 'clip') return;
    if (el.scrollWidth > el.clientWidth + 2
        && cs.textOverflow !== 'ellipsis'
        && cs.whiteSpace !== 'normal') {
      clipped.push({el: name(el), txt: (el.textContent || '').trim().slice(0, 20),
        sw: el.scrollWidth, cw: el.clientWidth});
    }
  });
  out.R10_clipped = clipped.slice(0, 10);
  out.R10_count = clipped.length;

  out.docHeight = Math.round(document.documentElement.scrollHeight);
  out.viewport = Math.round(document.documentElement.clientWidth);
  return out;
}
"""


def run(url=DEFAULT_URL, widths=WIDTHS):
    report = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in widths:
            pg = b.new_page(viewport={"width": w, "height": 880})
            pg.goto(url, wait_until="networkidle")
            pg.wait_for_timeout(1500)
            d = pg.evaluate(JS)
            d["width"] = w
            report[str(w)] = d
            pg.close()
        b.close()
    return report


def report_text(rep):
    lines = []
    reds = 0
    for w, d in rep.items():
        lines.append("=" * 72)
        lines.append("viewport %spx   doc height %s" % (w, d["docHeight"]))

        def verdict(key, n):
            nonlocal reds
            budget = BUDGET.get(key)
            if budget is None:
                return ""
            if n <= budget:
                return "  ok"
            reds += 1
            return "  RED (budget %d)" % budget

        lines.append("R1 escapes card        : %d%s" % (d["R1_count"], verdict("R1", d["R1_count"])))
        for e in d["R1_escapes"][:5]:
            lines.append("     %-40s in %-18s +%dpx" % (e["el"], e["card"], e["dy"]))
        lines.append("R2 interactive overlap : %d%s" % (d["R2_count"], verdict("R2", d["R2_count"])))
        for e in d["R2_overlaps"][:4]:
            lines.append("     %s X %s" % (e["a"], e["b"]))
        lines.append("R3 rendered font sizes : %d %s%s"
                     % (d["R3_count"], [s for s, _ in d["R3_fontSizes"]],
                        verdict("R3", d["R3_count"])))
        lines.append("R4 contrast failures   : %d%s" % (d["R4_count"], verdict("R4", d["R4_count"])))
        for e in d["R4_lowContrast"][:6]:
            lines.append("     %-26s %-18s %.2f needs %.1f  %s on %s"
                         % (e["el"], e["txt"], e["ratio"], e["need"], e["color"], e["bg"]))
        lines.append("R5 hit target under 24 : %d%s" % (d["R5_count"], verdict("R5", d["R5_count"])))
        for e in d["R5_smallTargets"][:6]:
            lines.append("     %-26s %sx%s %s" % (e["el"], e["w"], e["h"], e["txt"]))
        lines.append("R6 no focus rule       : %d%s" % (d["R6_count"], verdict("R6", d["R6_count"])))
        for e in d["R6_noFocusRule"][:5]:
            lines.append("     %s" % e)
        lines.append("R7 input without name  : %d%s" % (d["R7_count"], verdict("R7", d["R7_count"])))
        for e in d["R7_unnamed"][:6]:
            lines.append("     %-26s placeholder=%r" % (e["el"], e["ph"]))
        lines.append("R8 overflowing scroller: %d" % d["R8_count"])
        for e in d["R8_scrollers"][:4]:
            lines.append("     %-26s %sx%s in %sx%s  %s"
                         % (e["el"], e["sh"], e["sw"], e["ch"], e["cw"], e["ov"]))
        lines.append("R9 horizontal scroll   : %d  (doc %d vs client %d)%s"
                     % (d["R9_count"], d["R9_docScrollW"], d["R9_clientW"],
                        verdict("R9", d["R9_count"])))
        lines.append("R10 clipped text       : %d%s" % (d["R10_count"], verdict("R10", d["R10_count"])))
        for e in d["R10_clipped"][:5]:
            lines.append("     %-26s %-20s %s in %s" % (e["el"], e["txt"], e["sw"], e["cw"]))
    return "\n".join(lines), reds


def main(argv):
    url, out = DEFAULT_URL, None
    for i, a in enumerate(argv):
        if a == "--json" and i + 1 < len(argv):
            out = argv[i + 1]
        elif a.startswith("http"):
            url = a
    rep = run(url)
    text, reds = report_text(rep)
    print(text)
    if out:
        open(out, "w", encoding="utf-8").write(
            json.dumps(rep, ensure_ascii=False, indent=1))
    print("")
    print("RENDER ACCEPTANCE: %d red" % reds)


if __name__ == "__main__":
    main(sys.argv[1:])
