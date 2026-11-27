# -*- coding: utf-8 -*-
"""The editor must fit the window.  No dragging a scrollbar to reach the numbers.

WHY THIS EXISTS
---------------
Measured 2026-11-01 (user report: 「ui有问题，显示不全，非要拖动滚动条」): in the
real 1264x821 window the document stood 921px tall, so the bottom of the field
table could only be reached by dragging the page.  The cause was one line:

    #editor .edbody { height: calc(100dvh - 220px); }

The chrome above the editor is not a constant: header 48+16, card title 37.3+16,
hint 69.28+12, tab row 35.09+12, margin-top 12 = 235.58, plus 20px card padding
and 16px shell padding = 272px.  The line guessed 220.  Guessing is the bug, not
the number: this file therefore fails on ANY `calc(100dvh - <n>px)` inside the
style block, because the next chrome change re-breaks it silently.

What replaced it is a flex chain -- every link `flex:1; min-height:0` so the
editor takes the space actually left over.  A single missing link makes a child
size itself to its 16000px of content and the page scrolls again, which is why
both halves of this gate exist:

  static   the style block states no dvh subtraction, and the chain's links are
           present where the comment says they are
  dynamic  a real Chromium at the two real widths measures document height and
           the scroll containers, and prints the numbers

Usage
    python -X utf8 _probe/test_editor_fit.py            # starts its own server
    python -X utf8 _probe/test_editor_fit.py --url http://127.0.0.1:7811/
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")

# The real window the product is designed against, and the next breakpoint down.
WIDTHS = (1264, 1100)
HEIGHTS = (821, 700)

# `.edbody`'s floor is `min(420px, 44vh)`: 420px on a tall screen, 44% of the
# window on a short one (see the rule in index.html for why a flat 420px was an
# overflow on a 1100x821 laptop).  The trade is still real -- a 6-row window is
# not a workspace, so the page is allowed to scroll a little down there -- but
# the floor now moves with the window, so the budget below is a number instead
# of whatever the arithmetic happened to produce.
#
# 821 is the real window: it must fit exactly, no scroll at all.  700 is a
# small laptop and is allowed to scroll, bounded at 120px so that a regression
# there still shows up as a number going up rather than as silence.
MUST_FIT = 821

# Selectors whose chain is load-bearing.  Order matters: each is the parent of
# the next, so a broken link shows up as the FIRST one that fails to stretch.
CHAIN = ("main", "#view-editor.on", "#editor", "#editor .edbody")

# The stacked layout, measured separately.  Below the 620px container query the
# two panes stop sharing one window and become two documents stacked in a
# column -- and each one has to cap itself, or it sizes to its content.  The
# list was capped at 240px from the start; the field pane was not, so at 640px
# wide the page stood 23,705px tall (measured 2026-11-04).  This is outside the
# product's own minimum window (desktop minWidth 960, `tools/run_ui.py`
# min_size 900x600) but it is one drag of the window edge away, so it is gated.
NARROW = (640, 600)
NARROW_MAX_PANE = 260      # the 240px cap plus borders and rounding

# The frame boxes allowed to subtract the page's own 16px padding (top+bottom).
# Anything else subtracting a pixel constant is a guess at the chrome, and a
# guess is exactly what this file exists to keep out.
DVH_OK = {".shell": 32, ".content": 32, ".rail": 32}

FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(label)
    return ok


def strip_comments(css):
    """Remove /* ... */ so a sentence ABOUT dvh arithmetic is not read as code.

    Without this the gate flagged its own explanatory comment: the note that
    explains why `calc(100dvh - 220px)` was wrong contains that very string.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def style_block(text):
    m = re.search(r"<style[^>]*>(.*)</style>", text, flags=re.S)
    return m.group(1) if m else ""


def all_rule_bodies(css, selector):
    """Every rule that names `selector` exactly, in file order.

    Several, not one: the base rule states `flex: 1` and a later
    `@container`/`@media` override restates the box for a narrow card.  Which
    one applies depends on the viewport, so a check has to say which it means
    instead of silently taking whichever comes last.
    """
    bodies = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        heads = [h.strip() for h in m.group(1).split(",")]
        if selector in heads:
            bodies.append(m.group(2))
    return bodies


def rule_body(css, selector):
    """The declarations of the LAST rule that names `selector` exactly.

    Last, not first: the responsive overrides (`@media`, `@container`) come
    later in the file and are what actually applies at 1100px.
    """
    bodies = all_rule_bodies(css, selector)
    return bodies[-1] if bodies else None


def dvh_subtractions(css):
    """Every `calc(100dvh - Npx)` plus the selector it sits under."""
    out = []
    for m in re.finditer(r"calc\(\s*100dvh\s*-\s*[0-9.]+px\s*\)", css):
        head = css[:m.start()]
        sel = ""
        for r in re.finditer(r"([^{}]+)\{", head):
            sel = r.group(1).strip().splitlines()[-1].strip()
        out.append((sel, m.group(0)))
    return out


def dynamic(url, sizes=None):
    from playwright.sync_api import sync_playwright

    js = r"""
    () => {
      const de = document.documentElement;
      const q = s => document.querySelector(s);
      const box = el => el ? {h: Math.round(el.getBoundingClientRect().height),
                             w: Math.round(el.getBoundingClientRect().width)}
                           : null;
      const scrolls = el => el ? (el.scrollHeight - el.clientHeight) : null;
      return {
        docH: de.scrollHeight,
        winH: de.clientHeight,
        overflowY: de.scrollHeight - de.clientHeight,
        overflowX: de.scrollWidth - de.clientWidth,
        chain: ['.shell', '.content', 'main', '#view-editor.on', '#editor',
                '#editor .edbody', '#editor .edlist', '#editor .edpane']
               .map(s => [s, box(q(s)), scrolls(q(s))]),
      };
    }
    """
    results = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            for w, h in (sizes or [(w, h) for w in WIDTHS for h in HEIGHTS]):
                pg = b.new_page(viewport={"width": w, "height": h})
                # ?nocache= because Chromium keeps the previously fetched
                # CSS for the same URL and the gate then measures the OLD
                # stylesheet -- that once made a fixed page look unfixed.
                pg.goto("%s?nocache=%d#editor" % (url.rstrip("/"), w * 1000 + h),
                        wait_until="networkidle")
                pg.wait_for_timeout(700)
                try:
                    pg.click("#nav-editor", timeout=2000)
                except Exception:                        # noqa: BLE001
                    pass
                pg.wait_for_timeout(500)
                results[(w, h)] = pg.evaluate(js)
                pg.close()
        finally:
            b.close()
    return results


def free_port(start=7960):
    import socket
    for p in range(start, start + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("no free port")


def spawn_server():
    """Start the page's own engine, so the gate is self-contained.

    Two reasons not to lean on an ambient 7811: a suite that is silent when the
    server is absent is how the 921px page shipped in the first place, and a
    stale ambient engine serves a cached stylesheet, which measures the bug that
    was already fixed and reports it as still broken.  Returns (proc, url).
    """
    import subprocess
    import time
    import urllib.request

    # free_port() only PROVES a port was free a moment ago -- it closes the
    # socket before the engine binds it, and in a 250-suite sweep another
    # process can take that number in between.  When that happened the engine
    # exited at once and this gate reported "the page answered at :7960" as a
    # layout failure, which is the one thing it must never get wrong: a red here
    # means the editor does not fit.  So try a few ports before believing it.
    start = 7960
    url = "http://127.0.0.1:%d/" % start
    for attempt in range(4):
        port = free_port(start)
        url = "http://127.0.0.1:%d/" % port
        proc = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-u",
             os.path.join(ROOT, "tools", "run_ui.py"),
             "--serve-only", "--port", str(port)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + (180 if attempt == 0 else 60)
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(url + "api/meta", timeout=3) as r:
                    if b'"ok"' in r.read():
                        return proc, url
            except Exception:                            # noqa: BLE001
                pass
            time.sleep(0.5)
        try:
            proc.kill()
            proc.wait(timeout=20)
        except Exception:                                # noqa: BLE001
            pass
        # 7960 is taken by something else; look further up the range next time.
        start = port + 1
    return None, url


def main(argv):
    url = None
    if "--url" in argv:
        url = argv[argv.index("--url") + 1]

    text = io.open(PAGE, encoding="utf-8").read()
    css = style_block(text)
    code = strip_comments(css)

    print("\n=== 1. the only dvh arithmetic is the shell's own padding ===")
    # What is legitimate: the page's OWN 16px padding top and bottom, written as
    # `calc(100dvh - 32px)` on the three boxes that make up the window frame.
    # That number is the page's to know, and if the padding changes it changes
    # in one place with it.  What is NOT legitimate is subtracting a guess at
    # the chrome above the editor (220px), because that chrome moves whenever a
    # hint sentence gets longer -- measured 2026-11-01: it was 272px, the guess
    # was 52px short, and the page stood 921px in an 821px window.
    subs = dvh_subtractions(code)
    ok = dict(DVH_OK)
    bad = [(sel, expr) for sel, expr in subs
           if ok.get(sel) is None or expr != "calc(100dvh - %dpx)" % ok[sel]]
    check("every calc(100dvh - Npx) is the frame's own 32px padding", not bad,
          str(bad) + " -- a guessed chrome height is what made the page 921px")
    seen = sorted({sel for sel, _ in subs})
    check("and it sits on exactly the frame boxes", seen == sorted(DVH_OK),
          "%s vs expected %s" % (seen, sorted(DVH_OK)))

    print("\n=== 2. the flex chain is complete ===")
    for sel in CHAIN:
        bodies = all_rule_bodies(code, sel)
        if not bodies:
            check("%s has a rule" % sel, False, "selector not found")
            continue
        flat = re.sub(r"\s+", " ", bodies[0])
        # `min-height:0` is the link people leave out: without it a flex item
        # refuses to shrink below its content and the parent grows to 16000px.
        # `.edbody` is the exception the other way: it states a FLOOR on
        # purpose, so a 6-row window shrinks the page instead of the table.
        # That floor was a flat 420px until 2026-11-04, and on a 1100x821
        # laptop it pushed the page 33px past the window by itself -- a floor
        # that does not fit the window it is in is not a floor, it is an
        # overflow. It is now 420px on a tall screen and never more than 44%
        # of the window on a short one; either spelling counts as "a floor".
        shrinkable = ("min-height: 0" in flat or "min-height:0" in flat)
        if sel == "#editor .edbody":
            check("%s takes the leftover height" % sel,
                  "flex: 1" in flat or "flex:1" in flat, flat[:160])
            check("%s states an explicit floor instead of shrinking to nothing"
                  % sel,
                  "min-height: 420px" in flat or "min-height: min(420px, 44vh)" in flat,
                  flat[:160])
        else:
            check("%s is a flex column" % sel, "display: flex" in flat, flat[:160])
            check("%s can shrink below its content" % sel, shrinkable, flat[:160])

    print("\n=== 3. a real browser, at the two real widths ===")
    server = None
    narrow = {}
    if url is None:
        server, url = spawn_server()
        check("the page's own engine started at %s" % url, server is not None,
              "`python tools/run_ui.py --serve-only` did not answer /api/meta")
    try:
        got = dynamic(url) if (url and (server is not None or "--url" in argv)) else {}
        narrow = (dynamic(url, [NARROW])
                  if (url and (server is not None or "--url" in argv)) else {})
    except Exception as exc:                                 # noqa: BLE001
        check("the page answered at %s" % url, False, str(exc))
        got = {}
    finally:
        if server is not None:
            try:
                server.kill()
                server.wait(timeout=20)
            except Exception:                            # noqa: BLE001
                pass

    for (w, h), d in sorted(got.items()):
        print("  --   %dx%d  doc %dpx  window %dpx  overflow %+dpx (x %+d)"
              % (w, h, d["docH"], d["winH"], d["overflowY"], d["overflowX"]))
        for sel, box, scroll in d["chain"]:
            print("         %-20s %s  scroll %s" % (sel, box, scroll))
        if h >= MUST_FIT:
            check("%dx%d: the page does not scroll vertically" % (w, h),
                  d["overflowY"] <= 0, "+%dpx" % d["overflowY"])
        else:
            # Below the floor's ceiling the table stops shrinking at 44% of the
            # window, so the page scrolls a little on purpose.  Printed for the
            # record, and bounded so that a real regression there still shows
            # up as a number going up.
            print("         (below the floor's ceiling: page scrolls %+dpx by "
                  "design)" % d["overflowY"])
            check("%dx%d: below the floor it scrolls a little, not a lot"
                  % (w, h), d["overflowY"] <= 120, "+%dpx" % d["overflowY"])
        check("%dx%d: no horizontal scrollbar" % (w, h), d["overflowX"] <= 0,
              "+%dpx" % d["overflowX"])
        # The editor's own panes must scroll INSIDE the window instead of the
        # page growing to hold them.
        pairs = dict((s, (b, sc)) for s, b, sc in d["chain"])
        for sel in ("#editor .edbody",):
            box, scroll = pairs.get(sel, (None, None))
            if box is None:
                check("%dx%d: %s is present" % (w, h, sel), False, "no box")
                continue
            check("%dx%d: %s is inside the window" % (w, h, sel),
                  box["h"] <= d["winH"], "%dpx tall in %dpx" % (box["h"], d["winH"]))

    for (w, h), d in sorted(narrow.items()):
        print("\n  --   %dx%d (stacked)  doc %dpx  window %dpx  overflow %+dpx"
              % (w, h, d["docH"], d["winH"], d["overflowY"]))
        pairs = dict((s, (b, sc)) for s, b, sc in d["chain"])
        for sel in ("#editor .edlist", "#editor .edpane"):
            box, scroll = pairs.get(sel, (None, None))
            if box is None:
                check("%dx%d: %s is present" % (w, h, sel), False, "no box")
                continue
            # Both panes are capped and both scroll inside themselves.  Without
            # the cap the field table's 22,977px of content became the page's
            # height, and the document stood 23,705px in a 600px window.
            check("%dx%d: %s is capped, not content-sized" % (w, h, sel),
                  box["h"] <= NARROW_MAX_PANE,
                  "%dpx tall, %s of content" % (box["h"], scroll))
            check("%dx%d: %s scrolls inside itself" % (w, h, sel),
                  (scroll or 0) > 0 or box["h"] <= NARROW_MAX_PANE,
                  "scroll %s" % scroll)

    print()
    if FAILS:
        print("EDITOR FIT: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("EDITOR FIT: THE EDITOR TAKES THE SPACE LEFT OVER, AT EVERY TESTED "
          "WINDOW")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
