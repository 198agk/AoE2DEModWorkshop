"""Check the 12 acceptance items in DESIGN.md §10 against the real page.

The contract says "一条不绿就不算改完" and lists twelve greps by hand.  Doing them
by hand is how the same defect (13 font sizes, 29 hex literals) survived several
rounds of "themed it".  This prints the measured number and the pass/fail for
each item, and never edits anything.

Two of the greps are wrong if taken literally, and this file takes the contract's
own intent instead:

* item 1 cannot forbid hex everywhere, because the token table in `:root` IS a
  list of hex values.  The rule is "no hex outside the token table", so the
  `:root` block is excused and every other rule must be clean.
* items 2 and 5 measure numbers, and the page now says `var(--fs-body)`.  A
  grep for `[0-9]+px` would report 0 sizes and pass while the page could hold
  nine of them, so the tokens are resolved before counting.  A checker that
  goes green because it found nothing is the defect this file exists to catch.

Item 11 (no horizontal scroll at 1237 / 1100) cannot be answered from text, so
it is reported as MANUAL with the two numbers it depends on.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
TOKEN = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")
FS_ANY = re.compile(r"font-size:\s*([^;]+);")
FS_SHORT = re.compile(r"font:\s*[^;]*?(var\(--fs-[a-z0-9-]+\))")
RADIUS = re.compile(r"border-radius:\s*([^;]+);")
SPACE = re.compile(r"(?:padding|gap|margin)[a-z-]*:\s*([^;]+);")
INLINE = re.compile(r'style="')
VAR_USE = re.compile(r"var\((--[a-z0-9-]+)")
LABEL = re.compile(r"<label\b[^>]*>")
PRIMARY = re.compile(r'class="[^"]*\bprimary\b')

# 48 is on the scale because the contract's own spacing table says so
# ("页面底部留白 | 56 -> 48").  The line that lists the allowed values
# forgot it; the table below it did not.  A checker that reds the page
# for obeying the table would be the defect.
SPACE_SCALE = {0, 2, 4, 6, 8, 12, 16, 20, 24, 32, 48}


def style_block(html):
    m = re.search(r'<style id="aoe2mod-legible">(.*?)</style>', html, re.S)
    if not m:
        raise SystemExit('REFUSING: no <style id="aoe2mod-legible"> block')
    return m.group(1)


def root_block(css):
    m = re.search(r":root\s*\{(.*?)\}", css, re.S)
    if not m:
        raise SystemExit("REFUSING: no :root block to read tokens from")
    return m.group(1)


def tokens(css):
    return {name: value.strip() for name, value in TOKEN.findall(root_block(css))}


def resolve(text, table, depth=0):
    """Replace every var(--x) with its token value, so numbers can be counted."""
    if depth > 6:
        return text

    def one(m):
        return table.get(m.group(1), m.group(0))

    out = re.sub(r"var\((--[a-z0-9-]+)\)", one, text)
    if out != text:
        return resolve(out, table, depth + 1)
    return out


def px_values(raw):
    out = set()
    for part in raw.replace("/", " ").split():
        p = part.strip().strip(",")
        if re.fullmatch(r"[0-9.]+px", p):
            out.add(float(p[:-2]))
    return out


def main():
    html = io.open(PAGE, encoding="utf-8", newline="").read()
    css = style_block(html)
    table = tokens(css)
    checks = []

    def check(name, ok, detail):
        checks.append((name, ok, detail))

    # 1. no hex literals outside the token table
    outside = css.replace(root_block(css), "", 1)
    hexes = HEX.findall(outside)
    check("1 no hex literals outside :root", not hexes,
          "found %d: %s" % (len(set(hexes)), sorted(set(hexes))[:8])
          if hexes else "0 (all %d live in the token table)" % len(
              set(HEX.findall(root_block(css)))))

    # 2. at most 5 font sizes, with tokens resolved
    sizes = set()
    for raw in FS_ANY.findall(css):
        sizes |= px_values(resolve(raw, table))
    for raw in FS_SHORT.findall(css):
        sizes |= px_values(resolve(raw, table))
    sizes = sorted(sizes)
    check("2 at most 5 font sizes", 0 < len(sizes) <= 5,
          "%d: %s" % (len(sizes), sizes))

    # 3. no half-pixel font sizes
    halves = [s for s in sizes if s != int(s)]
    check("3 no x.5px font size", not halves, str(halves))

    # 4. at most 3 radii, with tokens resolved
    radii = set()
    for raw in RADIUS.findall(css):
        got = resolve(raw, table)
        for part in got.split():
            p = part.strip()
            if p.endswith("px"):
                radii.add(p)
            elif p == "50%":
                radii.add(p)
    check("4 at most 3 radii", 0 < len(radii) <= 3,
          "%d: %s" % (len(radii), sorted(radii)))

    # 5. spacing on the 4px scale, with tokens resolved
    vals = set()
    for raw in SPACE.findall(css):
        vals |= px_values(resolve(raw, table))
    off = sorted([v for v in vals if v not in SPACE_SCALE], reverse=True)
    check("5 spacing on the 2/4/6/8/12/16/20/24/32 scale", not off,
          "%d values, off-scale: %s" % (len(vals), off))

    # 6. no inline style attributes
    inline = INLINE.findall(html)
    check("6 no inline style=", not inline, "%d" % len(inline))

    # 7. every var(--x) is defined
    used = {v for v in VAR_USE.findall(css)}
    defined = {v for v in VAR_DEF_ALL(css)}
    missing = sorted(used - defined)
    check("7 every var() is defined", not missing, "missing: %s" % missing)

    # 8. no empty rule and no duplicate selector
    bodies = re.findall(r"\{([^{}]*)\}", css)
    empty = len([b for b in bodies if not b.strip()]) - len(
        [b for b in bodies if not b.strip() and b.startswith(":root")])
    # The :root block's own body is non-empty, so a simple count is honest here.
    empty = len([b for b in bodies if not b.strip()])
    # A selector may appear twice ON PURPOSE when the second one lives inside a
    # `@container` / `@media` block: that is how the editor collapses when its
    # own card is narrow.  Only top-level repeats are duplicates.
    top = re.sub(r"@(?:container|media)[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css)
    selectors = [s.strip() for s in re.findall(r"(?:^|\})\s*([^{}@]+)\{", top)]
    dupes = sorted({s for s in selectors if selectors.count(s) > 1 and s})
    check("8 no empty rule, no duplicate selector", empty == 0 and not dupes,
          "empty blocks %d, duplicate selectors: %s" % (empty, dupes[:6]))

    # 9. every label has for=, every input has a name
    labels = LABEL.findall(html)
    no_for = [l for l in labels if "for=" not in l]
    check("9 every <label> has for=", not no_for,
          "%d labels, %d without for=" % (len(labels), len(no_for)))

    # 10. at most one .primary per screen
    primaries = PRIMARY.findall(html)
    check("10 at most one .primary", len(primaries) <= 1,
          "%d occurrences" % len(primaries))

    # 11. responsive: measured by _probe/measure_widths.py, read back here.
    # `scroll == doc` is the no-horizontal-scroll half; the second half is that
    # the grid still has two columns at 1237 and one at 1100, so nothing was
    # squeezed out of the window to make the numbers look clean.
    widths = load_widths()
    if widths is None:
        check("11 no horizontal scroll at 1237 / 1100", None,
              "MANUAL -- run _probe/measure_widths.py <base-url> first")
    else:
        problems = []
        for w in ("1237", "1100"):
            got = widths.get(w) or {}
            doc, scroll = got.get("doc"), got.get("scroll")
            cols = (got.get("cols") or "").split()
            if not doc or not scroll:
                problems.append("%spx produced no numbers" % w)
                continue
            if doc != scroll:
                problems.append("%spx scrolls horizontally (%s vs %s)"
                                % (w, scroll, doc))
            if w == "1237" and len(cols) != 2:
                problems.append("1237px lost a column: %r" % got.get("cols"))
            if w == "1100" and len(cols) != 1:
                problems.append("1100px did not collapse: %r" % got.get("cols"))
        check("11 no horizontal scroll at 1237 / 1100", not problems,
              "ok (%s / %s)" % (widths.get("1237", {}).get("doc"),
                                widths.get("1100", {}).get("doc"))
              if not problems else "; ".join(problems))

    # 12. no em dash in Chinese copy -- including the string table, because the
    # page replaces its own text with that table at load time.  Scanning only the
    # markup let four sentences keep their dashes while this item reported green.
    em = re.findall(r"[^\n]{0,20}\u2014[^\n]{0,20}", html)
    locale_em = []
    for path in locale_files():
        body = io.open(path, encoding="utf-8").read()
        for line in body.split("\n"):
            if "\u2014" in line:
                locale_em.append("%s: %s" % (os.path.basename(path),
                                             line.strip()[:70]))
    check("12 no em dash", not em and not locale_em,
          "%d in markup, %d in locales %s"
          % (len(em), len(locale_em), locale_em[:4]))

    # 13-15. DESIGN.md §12.4.  These three exist because §12 is about the page
    # LOOKING like a desktop tool, and the way that fails is not a literal -- it
    # is a size that was defined and then never spent, or a radius drift nobody
    # noticed.  Each one therefore asks "how many distinct values are actually
    # declared", not "is any value forbidden".
    #
    # 13: all four type steps must be used.  The page had four defined and spent
    #     three, so the biggest thing on screen was a 15px card title -- no
    #     focal line anywhere.  `--fs-display` is now the app bar's h1.
    fs_defs = sorted(
        {v for k, v in table.items() if k.startswith("--fs-")},
        key=lambda s: float(re.sub(r"[^0-9.]", "", s) or 0))
    fs_used = set()
    for name in ("--fs-micro", "--fs-body", "--fs-title", "--fs-display"):
        if re.search(r"var\(\s*" + re.escape(name) + r"\s*\)", css):
            fs_used.add(name)
    check("13 all four type steps are spent", len(fs_used) == 4,
          "%d of 4 used (%s); defined: %s"
          % (len(fs_used), ", ".join(sorted(fs_used)), fs_defs))

    # 14: exactly three radii.  §12 raised surface/control but kept the count.
    check("14 exactly three radii", len(radii) == 3,
          "%d: %s" % (len(radii), sorted(radii)))

    # 15: the panel must sit clearly above the page.  A white card on a page that
    # is nearly white has no edge, and the fix people reach for is a heavier
    # border -- which is the web-est possible answer.  Measured as the WCAG
    # contrast between --panel and --bg: >= 1.09 is about 4 steps of grey.
    def _lum(hexval):
        h = hexval.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

    panel = table.get("--panel", "")
    bg = table.get("--bg", "")
    if panel.startswith("#") and bg.startswith("#"):
        lp, lb = _lum(panel), _lum(bg)
        ratio = (max(lp, lb) + 0.05) / (min(lp, lb) + 0.05)
        check("15 panel stands off the page", ratio >= 1.09,
              "%.3f:1 (%s on %s), need >= 1.09" % (ratio, panel, bg))
    else:
        check("15 panel stands off the page", False,
              "could not read --panel / --bg (%r, %r)" % (panel, bg))

    bad = 0
    for name, ok, detail in checks:
        mark = "MANUAL" if ok is None else ("ok  " if ok else "FAIL")
        if ok is False:
            bad += 1
        print("%s %-46s %s" % (mark, name, detail))
    manual = len([1 for _, ok, _ in checks if ok is None])
    green = len([1 for _, ok, _ in checks if ok is True])
    print("\nDESIGN ACCEPTANCE: %d of %d green, %d red, %d manual"
          % (green, len(checks), bad, manual))
    return 1 if bad else 0


def load_widths():
    path = os.path.join(ROOT, "_probe", "width_report.json")
    if not os.path.isfile(path):
        return None
    try:
        return json.loads(io.open(path, encoding="utf-8").read())
    except ValueError:
        return None


def locale_files():
    """Every string table the page can be running against."""
    base = os.path.join(ROOT, "aoe2mod", "schema", "locales")
    if not os.path.isdir(base):
        return []
    return [os.path.join(base, n) for n in sorted(os.listdir(base))
            if n.endswith(".json")]


def VAR_DEF_ALL(css):
    """Every custom property declared anywhere in the block, not only :root."""
    return re.findall(r"(--[a-z0-9-]+)\s*:", css)


if __name__ == "__main__":
    sys.exit(main())
