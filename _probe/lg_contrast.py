# -*- coding: utf-8 -*-
"""What the glass really sits on, and whether the words on it survive.

The contrast rule in `render_acceptance.py` reads `backgroundColor` off the DOM
and stops at the first ancestor above 50% alpha, so a card at .64 is scored as
if it were opaque white.  That is fine for a flat design and wrong for this one.

So this probe measures the other way round: paint the page with the picture and
the veil but with every surface made transparent, screenshot that, and sample
the real pixels behind each run of text.  Then composite the card's own fill
over those pixels and score the three greys against the result.  Whatever the
numbers say is what the eye is being asked to read.
"""
import io
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "7811"
OUT = sys.argv[2] if len(sys.argv) > 2 else "_shots/now"
VIEW = sys.argv[3] if len(sys.argv) > 3 else "mods"

# Strip everything that is surface, keep everything that is picture.
BARE = """
  html, body { background: transparent !important; }
  .shell, .rail, .content, header, main, .box, .setrow, .mod, .intentcard,
  .chip, button, input, textarea, select, .segs, .bgpick, .pipe, .pane {
    background: transparent !important;
    background-image: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    box-shadow: none !important;
    border-color: transparent !important;
  }
  * { color: transparent !important; text-shadow: none !important;
      -webkit-text-fill-color: transparent !important; }
  .switch::after, .dot, .railbar::after { background: transparent !important; }
"""


def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def over(fg, bg, alpha):
    return tuple(round(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))


COLLECT = """
  () => {
    const seen = [];
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walk.nextNode())) {
      const t = n.textContent.trim();
      if (!t) continue;
      const el = n.parentElement;
      if (!el) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue;
      const r = el.getBoundingClientRect();
      if (r.width < 8 || r.height < 6) continue;
      if (r.top < 0 || r.bottom > innerHeight) continue;
      seen.push({
        cls: (el.className || el.tagName).toString().slice(0, 26),
        txt: t.slice(0, 18),
        color: cs.color,
        px: parseFloat(cs.fontSize),
        bold: parseInt(cs.fontWeight, 10) >= 600,
        x: Math.round(r.left), y: Math.round(r.top),
        w: Math.round(r.width), h: Math.round(r.height),
      });
    }
    return seen;
  }
"""


def parse_rgb(s):
    """The page's own tokens arrive as hex; computed colours arrive as rgb()."""
    s = s.strip()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    inside = s[s.index("(") + 1:s.index(")")].split(",")
    return tuple(int(float(v)) for v in inside[:3])


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1255, "height": 897}, device_scale_factor=1)
        pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="load", timeout=90000)
        pg.wait_for_timeout(7000)
        pg.evaluate("() => { const n = document.getElementById('notice'); if (n) n.classList.remove('on'); }")
        pg.evaluate("(v) => showView(v)", VIEW)
        pg.wait_for_timeout(2500)
        # The state under test: the switch the player flips.
        pg.evaluate("() => document.body.classList.add('lg')")
        pg.wait_for_timeout(600)

        texts = pg.evaluate(COLLECT)
        pg.screenshot(path=f"{OUT}/lgreal_full.png")
        pg.add_style_tag(content=BARE)
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/lgreal_backdrop.png")

        img = Image.open(f"{OUT}/lgreal_backdrop.png").convert("RGB")
        W, H = img.size

        alpha = pg.evaluate("() => parseFloat(getComputedStyle(document.body).getPropertyValue('--lg-alpha'))")
        inks = pg.evaluate(
            """() => {
              const cs = getComputedStyle(document.body);
              return {
                text: cs.getPropertyValue('--text').trim(),
                text2: cs.getPropertyValue('--lg-text-2').trim(),
                text3: cs.getPropertyValue('--lg-text-3').trim(),
              };
            }"""
        )
        print(f"view={VIEW}  --lg-alpha={alpha}  inks={inks}")

        rows = []
        for t in texts:
            x0, y0 = max(0, t["x"]), max(0, t["y"])
            x1, y1 = min(W, t["x"] + t["w"]), min(H, t["y"] + t["h"])
            if x1 - x0 < 4 or y1 - y0 < 4:
                continue
            crop = img.crop((x0, y0, x1, y1))
            px = list(crop.getdata())
            # The darkest patch inside the run is the honest worst case: that is
            # the pixel where this line is hardest to read.
            worst = min(px, key=lum)
            surface = over((255, 255, 255), worst, alpha)
            worst_ratio = 9e9
            for key, css in inks.items():
                r = ratio(parse_rgb(css), surface)
                if r < worst_ratio:
                    worst_ratio, worst_key = r, key
            need = 3.0 if (t["px"] >= 24 or (t["px"] >= 18.66 and t["bold"])) else 4.5
            rows.append((worst_ratio, need, t["cls"], t["txt"], worst, surface, worst_key))

        rows.sort(key=lambda r: r[0])
        bad = [r for r in rows if r[0] < r[1]]
        print(f"text runs sampled: {len(rows)}   below AA: {len(bad)}")
        for r in rows[:10]:
            print("  %.2f (need %.1f)  %-26s %-18s under=%s surf=%s via %s"
                  % (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
        if bad:
            print("--- failures")
            for r in bad[:10]:
                print("  %.2f (need %.1f)  %-26s %-18s under=%s surf=%s via %s"
                      % (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
        b.close()


main()
