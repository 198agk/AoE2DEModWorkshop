# -*- coding: utf-8 -*-
"""Pressing Enter in a value box must queue the edit.

Reported 2026-11-02: 「就不能像正常的软件那样，任何改动都能直接全页保存」.  The old
gesture was type, press 先看看, press 记下这个改动, and a value typed without the
second click was silently NOT in the batch -- the header still said 已改 0 项 and
closing the window lost it without a word.

What this pins:
  * Enter alone moves the pending count from 0 to 1 (no 先看看 needed)
  * the server's session buffer really holds the value, not just the page
  * a refusal (a value out of range) leaves the count at 0 and shows why
  * 先看看 still works and still lets you see the bytes first
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, REPO)

from playwright.sync_api import sync_playwright   # noqa: E402

BASE = os.environ.get("BASE", "http://127.0.0.1:7811")
fails = []


def check(ok, what, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", what,
                         "" if not detail else " :: " + str(detail)))
    if not ok:
        fails.append(what)


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def pending():
    with urllib.request.urlopen(BASE + "/api/session-info", timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))["pending"]


post("/api/session-reset", {})
check(pending() == 0, "a fresh session has nothing pending", pending())

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1264, "height": 821})
    pg.goto(BASE + "/?nocache=enter", wait_until="domcontentloaded")
    pg.wait_for_selector("#railbar", timeout=180000)
    pg.evaluate("showView('editor')")
    pg.wait_for_selector("#fbody table.f", timeout=180000)

    # Narrow to 生命值 so the row under test is the first one and unambiguous.
    pg.fill("#field-q", "生命值")
    pg.wait_for_timeout(800)
    row = pg.evaluate("""() => {
      const tr = document.querySelector('#fbody table.f tr:nth-child(2)');
      return tr ? {label: tr.children[0].textContent, now: tr.children[2].textContent,
                   field: tr.querySelector('input')?.dataset.field} : null;
    }""")
    check(row and row["field"] == "HitPoints", "the filter found 生命值", row)

    # --- Enter alone must queue the edit ---------------------------------
    pg.fill("#fbody table.f tr:nth-child(2) input", "321")
    pg.press("#fbody table.f tr:nth-child(2) input", "Enter")
    # `ED_PENDING` is a module-scope `let`, so it is not on `window`; the header
    # is the number a player actually reads.  Wait for it rather than sleeping.
    try:
        pg.wait_for_function(
            "() => { const e = document.getElementById('edpend-n');"
            " return e && /已改 [1-9]/.test(e.textContent); }", timeout=30000)
    except Exception:
        pass
    hdr0 = pg.evaluate("() => document.querySelector('#edpend-n').textContent")
    check("已改 1 项" in hdr0, "Enter alone moves the pending count to 1", hdr0)
    check(pending() == 1, "and the server holds it, not just the page", pending())
    hdr = pg.evaluate("() => document.querySelector('#edpend-n').textContent")
    check("已改 1 项" in hdr, "the header says so", hdr)

    # The row shows the new value without a redraw.
    now = pg.evaluate("""() => document.querySelector(
        '#fbody table.f tr:nth-child(2) td.v').textContent""")
    check("321" in now, "the row's 现在 column follows", now)

    # --- a refusal must not queue anything --------------------------------
    before = pending()
    pg.fill("#fbody table.f tr:nth-child(2) input", "999999999")
    pg.press("#fbody table.f tr:nth-child(2) input", "Enter")
    pg.wait_for_timeout(2500)
    check(pending() == before, "an out-of-range value queues nothing", pending())
    why = pg.evaluate("""() => {
      const tr = document.querySelector('#fbody table.f tr:nth-child(2)');
      const plan = tr.nextSibling;
      return plan ? plan.textContent : '';
    }""")
    check(why.strip() != "", "and it says why on the row", why[:60])

    # --- 先看看 still works ------------------------------------------------
    pg.fill("#fbody table.f tr:nth-child(2) input", "654")
    pg.click("#fbody table.f tr:nth-child(2) button")
    pg.wait_for_timeout(1500)
    plan = pg.evaluate("""() => {
      const tr = document.querySelector('#fbody table.f tr:nth-child(2)');
      const p = tr.nextSibling;
      return p ? p.textContent : '';
    }""")
    check("字节" in plan, "先看看 shows the byte counts first", plan[:70])
    check(pending() == before, "and previewing alone queues nothing", pending())
    b.close()

post("/api/session-reset", {})
print("FAILED: %s" % fails if fails else "ENTER COMMIT: ALL PASSED")
sys.exit(1 if fails else 0)
