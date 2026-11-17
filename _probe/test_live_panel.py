# -*- coding: utf-8 -*-
"""The panel follows the file, instead of guessing when to look.

WHAT THE PLAYER ASKED FOR (2026-11-11):

    「这个页面依旧是不能实时更新的」
    「你就不会换一种更好的方式来实现吗」
    「比如说嵌入个什么」

THE CAUSE WAS NOT HTTP CACHING.  JSON and HTML already answer
`Cache-Control: no-store`.  What was missing is that every write verb
answered ONLY the screen that made the call: the second window, the editor 撤回
button, and anything typed into another tab kept drawing the old pages.  And
every page write called `loadCard` on the way back, which re-walks the 89 MB
civilisation block to redraw icons that did not move.

THE ANSWER IS A LONG POLL, not a timer and not SSE.  Three things have to hold,
and each is measured here rather than asserted from the source:

1. `/api/live?since=<v>` parks until a write moves `App._live_v`, then answers
   with the same counters every write already reports.  A write that happens
   while a screen is parked must wake it in well under the 20 s cap -- that is
   the whole difference between 「实时」 and 「等一会」.
2. Undo and redo wake the same waiters.  A step made of equal-width patches
   never bumps `_gen`, so a generation-only signal would let a 撤回 in one
   window leave another window showing the page it just removed.
3. A page write answers with the box new `page_list`, names included, so the
   strip, the tile badge and the window chips repaint from the answer instead
   of from a whole card re-read.

AND ONE THING THAT IS EASY TO BREAK WHILE DOING THIS: an always-open request
means the browser never reaches "network idle".  Measured 2026-11-11:
`_probe/render_acceptance.py` timed out at 30 s on `goto(wait_until=
"networkidle")` against a page that was drawing fine.  So the loop leaves a
short gap between polls, and section 6 pins it.
"""
import io
import json
import os
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

FAILS = []
BASE = "http://127.0.0.1:7811"


def check(ok, what, got=""):
    if ok:
        print("  ok   %s :: %s" % (what, got))
    else:
        print("  FAIL %s :: %s" % (what, got))
        FAILS.append(what)


def section(title):
    print()
    print("=== %s" % title)


def get(path, timeout=60):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body, timeout=300):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def report():
    print()
    if FAILS:
        print("LIVE PANEL: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("LIVE PANEL: THE SCREEN IS TOLD ABOUT A CHANGE INSTEAD OF ASKING -- "
          "A PARKED REQUEST IS WOKEN BY ANY WRITE (撤回 INCLUDED), AND A PAGE "
          "WRITE ANSWERS WITH THE PAGES IT MADE")
    return 0


def main():
    # ------------------------------------------------------------------ 1
    section("1. an idle screen is answered at once, not held")
    try:
        st = get("/api/live?wait=1")
    except Exception as exc:                                # noqa: BLE001
        check(False, "the live route answers", exc)
        return report()
    check(st.get("ok") is True and isinstance(st.get("v"), int),
          "it reports a version number the screen can send back",
          {k: st.get(k) for k in ("v", "gen", "pending", "undo")})
    check("pending" in st and "undo" in st and "redo" in st
          and "bytes" in st,
          "and carries the same counters a write reports, so one answer is enough",
          sorted(st.keys()))

    # A screen that is BEHIND must be answered at once instead of parked;
    # parking is only for a screen that is already up to date.  `v - 1` is
    # always a number this server is not at -- a literal 0 stops being
    # "behind" the moment the process restarts and its counter starts at 0.
    t0 = time.time()
    stale = get("/api/live?since=%d&wait=20" % (int(st.get("v") or 0) - 1))
    dt = time.time() - t0
    check(dt < 3.0 and stale.get("v") == st.get("v"),
          "a screen that is behind is answered immediately, not parked",
          (round(dt, 2), stale.get("v"), st.get("v")))

    # ------------------------------------------------------------------ 2
    section("2. a parked screen is woken by a write, in seconds")
    post("/api/session-reset", {})
    base = int(post("/api/session-info", {}).get("bytes") or 0)
    v0 = int(get("/api/live?wait=1").get("v") or 0)
    box = {}

    def park(key, since):
        t = time.time()
        try:
            box[key] = (round(time.time() - t, 2),
                        get("/api/live?since=%d&wait=20" % since, timeout=40))
        except Exception as exc:                            # noqa: BLE001
            box[key] = (None, {"error": str(exc)})

    th = threading.Thread(target=park, args=("w", v0))
    th.start()
    time.sleep(1.5)
    wrote = post("/api/pseudo-pages", {"building": 12, "box": 20,
                                     "on": [], "seconds": 0, "dry": False})
    th.join(40)
    dt, got = box.get("w") or (None, {})
    check(wrote.get("ok") is True, "a page lands while a screen is parked",
          wrote.get("error") or wrote.get("label"))
    check(dt is not None and dt < 8.0,
          "and the parked request came back before its 20 s cap", dt)
    check(int(got.get("v") or 0) > v0,
          "because the write moved the version it was waiting on",
          (v0, got.get("v")))
    check(int(got.get("pending") or 0) >= 1 and int(got.get("undo") or 0) >= 1,
          "and the answer already says there is one change to undo",
          (got.get("pending"), got.get("undo")))
    check(int(got.get("bytes") or 0) == base + int(wrote.get("grew") or 0),
          "with the byte count the write reported, not a stale one",
          (got.get("bytes"), base, wrote.get("grew")))

    # ------------------------------------------------------------------ 3
    section("3. 撤回 and 重做 wake the same screens")
    # THE TRAP: a step made of equal-width patches never bumps `_gen`, so a
    # generation-only signal would let an undo in one window leave another
    # window drawing the page it just removed.  Measured 2026-11-11.
    v1 = int(get("/api/live?wait=1").get("v") or 0)
    th = threading.Thread(target=park, args=("u", v1))
    th.start()
    time.sleep(1.5)
    undone = post("/api/undo", {})
    th.join(40)
    dt, got = box.get("u") or (None, {})
    check(bool(undone.get("undone")), "one undo takes the page back out",
          undone.get("undone"))
    check(dt is not None and dt < 8.0 and int(got.get("v") or 0) > v1,
          "and it wakes a parked screen even though the step was equal-width",
          (dt, v1, got.get("v")))
    check(int(got.get("bytes") or 0) == base,
          "the woken answer carries the byte count after the undo",
          (got.get("bytes"), base))
    check(int(got.get("undo") or 0) == 0 and int(got.get("redo") or 0) >= 1,
          "and says undo is spent and redo is available",
          (got.get("undo"), got.get("redo")))

    v2 = int(get("/api/live?wait=1").get("v") or 0)
    th = threading.Thread(target=park, args=("r", v2))
    th.start()
    time.sleep(1.5)
    redone = post("/api/redo", {})
    th.join(40)
    dt, got = box.get("r") or (None, {})
    check(bool(redone.get("redone")), "and redo puts it back",
          redone.get("redone"))
    check(dt is not None and dt < 8.0 and int(got.get("v") or 0) > v2,
          "waking the screens again", (dt, v2, got.get("v")))

    # ------------------------------------------------------------------ 4
    section("4. a page write answers with the pages it made")
    post("/api/session-reset", {})
    base = int(post("/api/session-info", {}).get("bytes") or 0)
    made = post("/api/pseudo-pages", {"building": 12, "box": 20,
                                    "on": [], "seconds": 0, "dry": False})
    pages = made.get("page_list")
    check(isinstance(pages, list) and len(pages) == 1,
          "the write that makes a page hands back the page list",
          None if pages is None else len(pages))
    check(isinstance(pages, list) and pages and pages[0].get("on_list") == [],
          "an empty page answers with an empty on_list, not a missing key",
          pages and pages[0].get("on_list"))
    put = post("/api/pseudo-page-put", {"building": 12, "box": 20,
                                        "unit": 83, "page": 1})
    rows = put.get("page_list") or []
    names = [u.get("name") for p in rows for u in (p.get("on_list") or [])]
    check(put.get("ok") is True and names == ["村民 (男性)"],
          "and putting a unit in answers with its NAME, so the tile is drawn"
          " without asking again", names)
    check(put.get("pending") is not None and put.get("undo") is not None
          and put.get("v") is not None,
          "the same answer carries the footer counters and the version, so"
          " the screen owes no second request",
          {k: put.get(k) for k in ("pending", "undo", "v")})
    took = post("/api/pseudo-page-del", {"building": 12, "box": 20,
                                        "unit": 83, "page": 1})
    rows = took.get("page_list") or []
    check(took.get("ok") is True and rows and rows[0].get("on_list") == [],
          "taking it out answers with the same page, now empty",
          rows and rows[0].get("on_list"))
    dropped = post("/api/pseudo-page-drop", {"building": 12, "box": 20,
                                          "page": 1})
    check(dropped.get("ok") is True and dropped.get("page_list") == [],
          "and dropping the page answers with an empty list, so the badge"
          " comes off without a re-read", dropped.get("page_list"))
    # WHAT THE FOUR WRITES GIVE BACK, AND WHAT THEY DELIBERATELY DO NOT.
    # Two things are left standing, and both have a byte count you can name:
    #
    #   11  the page's EFFECT record (4 byte head + 5 byte name + 2 byte
    #       count).  Dropping the last page cuts its technology record and
    #       leaves the effect as an orphan: deleting it would move every later
    #       effect offset for no gain, and a page made again appends a new one.
    #   9   the unit's train_locations placeholder -- the (-1, button) entry
    #       card.plan_slot appends when the unit carries no entry at all.  It
    #       is what made the icon show in the cell, and the page verbs never
    #       take it back.  Nothing points at it: card.boxes lists a unit under
    #       a building only when the entry NAMES that building, so a -1 entry
    #       draws in no box of any building.  Measured 2026-11-12: the whole
    #       89 building cards of the file are byte-identical before the four
    #       writes and after the drop.
    #
    # The 9 is written ONCE per unit, not once per round -- the next round
    # finds the placeholder and rewrites one byte instead of appending -- and
    # the second half of this check is what pins that.  The 11 does come back
    # every round; that is the price of never renumbering effects.
    left = int(post("/api/session-info", {}).get("bytes") or 0)
    check(left == base + 11 + 9,
          "the four writes give the file back, minus the orphan effect record"
          " and the unit's one placeholder cell",
          (left, base, left - base))
    post("/api/pseudo-pages", {"building": 12, "box": 20,
                               "on": [], "seconds": 0, "dry": False})
    post("/api/pseudo-page-put", {"building": 12, "box": 20,
                                  "unit": 83, "page": 1})
    post("/api/pseudo-page-del", {"building": 12, "box": 20,
                                  "unit": 83, "page": 1})
    post("/api/pseudo-page-drop", {"building": 12, "box": 20, "page": 1})
    again = int(post("/api/session-info", {}).get("bytes") or 0)
    check(again == left + 11,
          "and a second round costs the orphan effect record and nothing else,"
          " so the cell placeholder is reused rather than piled up",
          (again, left, again - left))

    # THE PLACEHOLDER IS INERT, and that is why leaving it is not a leak.  A
    # (-1, button) entry names no building, and card.boxes only lists a unit
    # under a building its entry NAMES -- so the entry draws in no box of any
    # building.  Measured on every card of the file, not argued from the code:
    # if this ever starts naming the building, a dropped page leaves an icon
    # standing in a box of a building the player never filled.
    def cards():
        # one flat string per drawn box: "building/button: name, name", so the
        # two reads compare as plain dicts (a list value is unhashable).
        out = {}
        for b in range(1, 130):
            try:
                d = get("/api/card?building=%d" % b, timeout=90)
            except Exception:                        # noqa: BLE001
                continue
            for bx in d.get("boxes") or []:
                us = [u.get("name") for u in (bx.get("units") or [])]
                if us:
                    out["%d/%s" % (b, bx.get("button"))] = ", ".join(
                        str(x) for x in us)
        return out

    seen = cards()
    check(len(seen) > 5,
          "the card route draws units somewhere, so the next check can see one",
          len(seen))
    post("/api/pseudo-pages", {"building": 12, "box": 20,
                               "on": [], "seconds": 0, "dry": False})
    post("/api/pseudo-page-put", {"building": 12, "box": 20,
                                  "unit": 83, "page": 1})
    post("/api/pseudo-page-del", {"building": 12, "box": 20,
                                  "unit": 83, "page": 1})
    post("/api/pseudo-page-drop", {"building": 12, "box": 20, "page": 1})
    after = cards()
    diff = sorted(set(seen.items()) ^ set(after.items()))         if seen or after else ["both reads came back empty"]
    check(not diff,
          "and the placeholder cell puts no icon in any building's card, so a"
          " dropped page leaves nothing behind but bytes", diff[:4])

    # ------------------------------------------------------------------ 5
    section("5. the panel rides it, and no page write re-reads the card")
    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                   encoding="utf-8").read()
    check('fetch("/api/live?since="' in page,
          "the page asks /api/live for the version it already has")
    check("liveStart();" in page and "function liveStart()" in page,
          "boot() starts it, and the starter is a named function")
    check("if (LIVE_ON) return;" in page,
          "the starter runs once, not once per call")
    check("if (typeof fetch !== \"function\") return;" in page,
          "and a harness with no fetch is survived, not crashed")
    check("EventSource" not in page,
          "it is a long poll, not SSE: the handler speaks HTTP/1.0, so a",
          "chunked event stream would be cut by the first reload")
    check("function liveApply(st)" in page and "cardCyclesRefresh()" in page,
          "an answer repaints the card panel through the cheap page route")
    # THE REGRESSION THIS SECTION EXISTS FOR: each of the four page writes
    # used to end in `await loadCard(CARD_BUILDING)`, which re-walks 89 MB to
    # redraw icons nothing moved.  Measured 0.85 s per icon; the page data
    # itself is one line of the answer.
    for name in ("cardAddPage", "cardDropPage", "cardPageTake"):
        body = page[page.find("async function %s(" % name):]
        body = body[:body.find("\n}")]
        check("loadCard(" not in body,
              "%s repaints from the answer instead of re-reading the card" % name,
              body.count("loadCard("))
        check("cardLivePaint(box);" in body,
              "and it repaints the strip, the badge and the chips")
    # The window has TWO click meanings and only the page branch was the
    # slow one: the box branch still re-reads the card on purpose, because
    # placing a NEW unit changes the card itself.  Scope the check to the
    # page branch, which ends at its own `return;`.
    take = page[page.find("async function cardPickTake("):]
    take = take[:take.find("\n}")]
    mark = take.find("// The BOX THAT WAS CLICKED")
    pageBranch = take[:mark] if mark > 0 else take
    check("cardPagesSet(box, rr.page_list);" in pageBranch
          and "cardLivePaint(box);" in pageBranch
          and "loadCard(" not in pageBranch,
          "a click on an icon in the window lands the same way",
          pageBranch.count("loadCard("))

    # ------------------------------------------------------------------ 6
    section("6. the loop leaves a gap, or no probe can ever see the page settle")
    # An always-open request means the browser never reaches network idle.
    # Measured 2026-11-11: render_acceptance's goto(networkidle) timed out at
    # 30 s against a page that drew fine, and the next reader would have
    # blamed the page instead of the poll.
    loop = page[page.find("async function liveLoop("):]
    loop = loop[:loop.find("\n}")]
    check("await liveSleep(700);" in loop,
          "there is a quiet window between one poll and the next",
          loop.count("liveSleep"))
    check("await liveSleep(4000);" in loop and "await liveSleep(2000);" in loop,
          "and a failed or unreadable answer backs off instead of spinning")
    check("if (was >= 0 && st.v !== was) liveApply(st);" in loop,
          "the first answer only says where the file stands, so nothing is",
          "repainted under a player who is already reading it")

    # THE WINDOW IS PART OF THE SAME FILE.  Measured 2026-11-11: a page write
    # made from another window repainted the strip and the badge, then left the
    # chips reading 「第 2 页 · 空」 over a page that held 长矛兵.  One file, two
    # answers -- so the repaint has to reach the chips as well.
    cyc = page[page.find("async function cardCyclesRefresh("):]
    cyc = cyc[:cyc.find("\n}")]
    check("cardPickPagesDraw();" in cyc and "cardPickSyncTitle();" in cyc,
          "a repaint while the window is open redraws its chips too")

    # Clean up so the next suite inherits the file it expects.
    post("/api/session-reset", {})
    return report()


if __name__ == "__main__":
    sys.exit(main())
