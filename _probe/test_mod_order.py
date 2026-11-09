# -*- coding: utf-8 -*-
"""Nail: a mod row can be dropped at a POSITION, and the position is what is written.

The list had two arrows, one place per press.  On the machine this was built on
there are 18 installed mods, so putting the last one first is 17 clicks and 17
rewrites of `mod-status.json` -- a file the engine reads on every launch, and
whose array order IS the load order (no sort in `screeninstalledmods.xaml`).
A drag says where in ONE write.

Four things that can be wrong and none of them throw:

1. The arithmetic.  The row is lifted OUT before it is put back, so every slot
   after it shifts down one.  Without that subtraction a drop one place down is
   a no-op and a drop on itself moves one place -- both read as "the mouse is
   unreliable", and neither raises.
2. The base.  `Priority` is 1-based and it is the number the screen shows; the
   array index is 0-based.  Converting in the wrong layer makes "drop at the
   top" land second.
3. The clamp.  A drop past the end means "last", not an error dialog -- the
   player dragged at the bottom of the list, which is where a miss lands.
4. The handler.  `if (to === from) return;` has to exist or a drop that lands
   where the row already is still writes the file, and a drag that ends in the
   same place becomes an edit the player has to undo.

Run:  python -X utf8 _probe\\test_mod_order.py
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")
HARNESS = os.path.join(ROOT, "_probe", "ui_page_harness.js")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("  ok   " if ok else "  FAIL ") + name + (("  " + str(detail)) if detail else ""))


def _doc(*names):
    """A status document in the shape the game writes: `Path` is `kind//folder`."""
    return {"Mods": [{"Path": "local//" + n, "Title": n, "Enabled": True,
                      "Priority": i + 1} for i, n in enumerate(names)],
            "Unsub": []}


def _order(doc):
    return [e["Path"].split("//", 1)[1] for e in doc["Mods"]]


def _pris(doc):
    return [e["Priority"] for e in doc["Mods"]]


def _fake_profile(tmp, *names):
    """A profile `pick_account` can find: one account dir with a mods tree."""
    acc = os.path.join(tmp, "9999")
    for sub in ("local", "subscribed"):
        os.makedirs(os.path.join(acc, "mods", sub), exist_ok=True)
    doc = _doc(*names)
    G.write_status_doc(acc, doc, backup=False)
    return acc


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    server = io.open(SERVER, encoding="utf-8").read()
    harness = io.open(HARNESS, encoding="utf-8").read()

    # ---- 1. the pure reorder ---------------------------------------------
    doc = _doc("a", "b", "c", "d")
    pos = G.move_mod_to_entry(doc, "d", 0)
    check("dropping the last row on the top puts it first",
          _order(doc) == ["d", "a", "b", "c"] and pos == 1,
          "%r / pos %r" % (_order(doc), pos))
    check("and every Priority is still 1..n",
          _pris(doc) == [1, 2, 3, 4], "%r" % (_pris(doc),))

    doc = _doc("a", "b", "c", "d")
    pos = G.move_mod_to_entry(doc, "a", 9)
    check("a drop past the end means last, not an error",
          _order(doc) == ["b", "c", "d", "a"] and pos == 4,
          "%r / pos %r" % (_order(doc), pos))

    doc = _doc("a", "b", "c")
    pos = G.move_mod_to_entry(doc, "b", 1)
    check("a drop where the row already is leaves the order alone",
          _order(doc) == ["a", "b", "c"] and pos == 2,
          "%r / pos %r" % (_order(doc), pos))

    doc = _doc("a", "b", "c")
    pos = G.move_mod_to_entry(doc, "a", -5)
    check("a negative position clamps to the top",
          _order(doc) == ["a", "b", "c"] and pos == 1,
          "%r / pos %r" % (_order(doc), pos))

    doc = _doc("a", "b", "c")
    try:
        G.move_mod_to_entry(doc, "nope", 0)
        raised = None
    except KeyError as exc:
        raised = exc
    check("a name that is not installed raises KeyError", raised is not None,
          repr(raised))
    check("and the document is untouched after that refusal",
          _order(doc) == ["a", "b", "c"], "%r" % (_order(doc),))

    # One move, one write: the whole reason this exists.  Ten ±1 moves rewrite
    # the file eleven times and can stop halfway; this is a single call.
    doc = _doc(*[chr(97 + i) for i in range(10)])
    G.move_mod_to_entry(doc, "j", 0)
    check("ten rows reorder in one call, all ten still present",
          len(doc["Mods"]) == 10 and _order(doc)[0] == "j"
          and sorted(_order(doc)) == sorted(chr(97 + i) for i in range(10)),
          "%r" % (_order(doc),))

    # ---- 2. the same thing through the toolkit, on a real file -----------
    tmp = tempfile.mkdtemp(prefix="aoe2mod_order_")
    try:
        acc = _fake_profile(tmp, "first", "second", "third", "fourth")
        tk = A.Toolkit(game_root=GAME)
        got = tk.move_mod_to("fourth", 1, profile_root=tmp)
        doc, _a, _b = G.read_status_doc(tmp)
        check("the toolkit's position is 1-based and matches Priority",
              got["priority"] == 1 and _order(doc)[0] == "fourth",
              "priority %r, order %r" % (got.get("priority"), _order(doc)))
        check("the answer carries the game-running note like every other write",
              "game_running" in got and "running_warning" in got,
              "%r" % (sorted(got),))
        # `position` is what a drop sends; `delta` is what an arrow sends.  They
        # must not be interchangeable: position 3 from the top, vs +3 places.
        got = tk.move_mod_to("third", 3, profile_root=tmp)
        doc, _a, _b = G.read_status_doc(tmp)
        check("a position addresses a slot, not a distance",
              got["priority"] == 3, "priority %r order %r"
              % (got.get("priority"), _order(doc)))
        # And the old ±1 entry point still works on the same file.
        tk.move_mod("first", 1, profile_root=tmp)
        doc, _a, _b = G.read_status_doc(tmp)
        check("the arrows and the drag write the same shape",
              _pris(doc) == [1, 2, 3, 4], "%r" % (_pris(doc),))
        # A backup is taken, because this file is the player's whole mod setup.
        tgt = G.resolve_mod_name(tmp, "first")
        check("the status file is written with a backup beside it",
              os.path.exists(os.path.join(acc, "mods", "mod-status.json.bak")),
              "folder %r" % (tgt,))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- 2b. the kind a name lives in ------------------------------------
    # Every write route defaults to `kind="local"`, and a Steam library is
    # `subscribed`.  Measured 2026-11-07 on this machine: all 18 installed mods
    # are subscribed, so every arrow, every drag and every switch answered
    # 「移不动：'582581_文明联盟 test 9'」 while the list they were drawn from had
    # just been read out of the subscribed folder.
    tmp = tempfile.mkdtemp(prefix="aoe2mod_kind_")
    try:
        acc = os.path.join(tmp, "9999")
        for sub in ("local", "subscribed"):
            os.makedirs(os.path.join(acc, "mods", sub), exist_ok=True)
        doc = {"Mods": [
            {"Path": "subscribed//steam mod", "Title": "Steam Mod",
             "Enabled": True, "Priority": 1},
            {"Path": "local//mine", "Title": "Mine",
             "Enabled": True, "Priority": 2},
        ], "Unsub": []}
        G.write_status_doc(acc, doc, backup=False)
        got = G.resolve_mod_any(tmp, "steam mod", kind="local", account=acc)
        check("a subscribed mod is found even when the caller said local",
              got == ("steam mod", "subscribed", "path"), "%r" % (got,))
        got = G.resolve_mod_any(tmp, "Steam Mod", kind="local", account=acc)
        check("and by its Title too", got == ("steam mod", "subscribed", "title"),
              "%r" % (got,))
        got = G.resolve_mod_any(tmp, "mine", kind="subscribed", account=acc)
        check("a local mod is found when the caller said subscribed",
              got == ("mine", "local", "path"), "%r" % (got,))
        # The caller's own kind still wins, so nothing that worked moved.
        doc["Mods"].append({"Path": "subscribed//mine", "Title": "Mine Sub",
                             "Enabled": True, "Priority": 3})
        G.write_status_doc(acc, doc, backup=False)
        got = G.resolve_mod_any(tmp, "mine", kind="local", account=acc)
        check("when the name exists in both kinds the asked-for one wins",
              got == ("mine", "local", "path"), "%r" % (got,))
        got = G.resolve_mod_any(tmp, "nothing here", kind="local", account=acc)
        check("a name that matches nothing is returned unchanged",
              got == ("nothing here", "local", "bare"), "%r" % (got,))
        # A folder dropped in by hand, with no status entry at all.
        os.makedirs(os.path.join(acc, "mods", "subscribed", "dropped in"),
                    exist_ok=True)
        got = G.resolve_mod_any(tmp, "dropped in", kind="local", account=acc)
        check("a folder dropped into the mods tree with no entry is still found",
              got == ("dropped in", "subscribed", "folder"), "%r" % (got,))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # And the writers have to USE it -- the helper being right is not the fix.
    api = io.open(os.path.join(ROOT, "aoe2mod", "api.py"),
                  encoding="utf-8").read()
    check("move_mod asks which kind before it writes",
          "folder, kind, _how = G.resolve_mod_any(" in api)
    check("and so does move_mod_to",
          api.count("folder, kind, _how = G.resolve_mod_any(") == 2,
          api.count("folder, kind, _how = G.resolve_mod_any("))
    loc = io.open(os.path.join(ROOT, "aoe2mod", "game", "locations.py"),
                  encoding="utf-8").read()
    check("uninstall and the on/off switch ask too",
          loc.count("folder, kind, how = resolve_mod_any(") == 1
          and loc.count("folder, kind, _how = resolve_mod_any(") == 1,
          loc.count("resolve_mod_any("))

    # ---- 3. the route sits in do_POST ------------------------------------
    at = server.index('if path == "/api/mod-move-to":')
    post_at = server.index("def do_POST(self)")
    get_at = server.index("def do_GET(self)")
    check("the move route is a POST, not a GET",
          post_at < at and not (get_at < at < post_at),
          "get@%d post@%d route@%d" % (get_at, post_at, at))
    # The handler wraps every call in `self._guard(lambda: ...)`, so the call is
    # split across lines and the arguments are indented.  Pinning the one-line
    # spelling failed on a route that was correct -- the check said "not a
    # position" about code that has only a position in it.
    body = re.search(
        r'app\.move_mod_to\(\s*payload\["name"\],\s*payload\["position"\]',
        server)
    check("it forwards the position, not a delta", body is not None,
          "route body")
    tail = server[server.index('/api/mod-move-to'):][:400]
    check("and a delta never reaches this handler",
          "payload[\"delta\"]" not in tail, tail.splitlines()[:6])

    # ---- 4. the page: what a drop does -----------------------------------
    # 2026-11-07: HTML5 drag never reaches the page inside the shipped window --
    # the desktop host owns the webview's drop target, so `dragstart` is consumed
    # before the page sees it.  The row is moved by hand with pointer events, and
    # `draggable` is deliberately FALSE: asking the browser for a drag the host
    # swallows is how a row comes to look clickable and do nothing.
    check("every row can be picked up", "row.draggable = false;" in page)
    check("the row hears the pointer go down", 'row.addEventListener("pointerdown"' in page)
    check("and listens on the document, because the pointer leaves the row",
          'document.addEventListener("pointermove", onMove, true)' in page
          and 'document.addEventListener("pointerup", onUp, true)' in page)
    check("the row under the pointer is found by point, not by hit target",
          "document.elementFromPoint" in page
          and 'under.closest("#mods .mod")' in page)
    check("a 4 px wobble is not a drag",
          re.search(r"Math\.abs\(ev\.clientY - startY\) < 4", page) is not None)
    check("pressing a switch or a button is not a drag",
          'e.target.closest("button, input, .switch")' in page)
    check("the ordering rule is one function a test can call",
          "async function modDropAt(name, from, at, total)" in page)
    check("a drop posts the target position",
          '"/api/mod-move-to"' in page and "position: to + 1" in page)
    check("and never a delta", "delta: to" not in page and "delta: at" not in page)
    # The lift-out shift.  Without it a one-place drop down does nothing, and
    # nothing about that failure is visible: the server is never called.
    check("the row is taken out before it is put back",
          re.search(r"if \(to > from\) to -= 1;", page) is not None)
    check("a drop that lands where the row is sends nothing",
          re.search(r"if \(to < 0 \|\| to === from\) return false;", page) is not None)
    # The half-of-the-row rule: without it the only reachable target is "before
    # this row", so the last row can never be dragged to the end.
    # The half-of-the-row rule: without it the only reachable target is "before
    # this row", so the last row can never be dragged to the end.  The pointer
    # version reads the box from the row it is over, not from the row it started
    # on, because those are different rows.
    check("the bottom half of a row means after it",
          re.search(r"MOD_DRAG\.at = Number\(hit\.dataset\.at\) \+ \(after \? 1 : 0\);",
                    page) is not None
          and re.search(r"\(ev\.clientY - r\.top\) > \(r\.height / 2\)", page)
          is not None)
    check("one row carries the highlight at a time",
          re.search(r"function modDragOver\(row\)", page) is not None
          and re.search(r"MOD_DRAG\.over\.classList\.remove\(\"dragover\"\)", page)
          is not None)
    check("the row being carried says so while it is carried",
          re.search(r'row\.classList\.add\("dragging"\)', page) is not None
          and re.search(r"\.mod\.dragging \{ opacity: \.5 \}", page) is not None)
    check("the drop target is drawn as an outline, not a fill",
          re.search(r"\.mod\.dragover \{ outline: 2px solid var\(--accent-line\);",
                    page) is not None)
    check("the row can be told apart from a button by the cursor",
          re.search(r"\.mod \{ cursor: grab; touch-action: none \}", page) is not None)
    check("and the whole page shows the grab while a row is carried",
          re.search(r"body\.dragging-row, body\.dragging-row \* \{ cursor: grabbing",
                    page) is not None)
    check("the list says rows can be dragged",
          'id="mods-drag-hint"' in page and "拖到别的位置" in page)

    # ---- 5. the harness pins all of it -----------------------------------
    check("the browser harness pins the drop position",
          '"/api/mod-move-to"' in harness
          and "(sent.body || {}).position === 1" in harness)
    check("and pins the lift-out shift",
          "a drop that lands where the row already is sends nothing" in harness
          and "a drop past two rows asks for the third place" in harness)
    check("and pins that a card can be dragged too",
          "a card answers the pointer too" in harness)
    # The stub's branch order: `/api/mod` is a prefix of `/api/mod-move-to`, so a
    # toggle branch placed first swallows the move and answers the OLD list.  That
    # is exactly what happened when this was first written.
    move_at = harness.index('url.indexOf("/api/mod-move-to")')
    mod_at = harness.index('url.indexOf("/api/mod") === 0')
    check("the stub matches the move route before the toggle route",
          move_at < mod_at, "move@%d toggle@%d" % (move_at, mod_at))

    bad = [c for c in CHECKS if not c[1]]
    print()
    if bad:
        for name, _, detail in bad:
            print("FAILED: %s :: %s" % (name, detail))
        print("MOD ORDER: %d CHECK(S) FAILED" % len(bad))
        return 1
    print("MOD ORDER: A ROW IS DROPPED AT A POSITION IN ONE WRITE -- THE LIFT-OUT "
          "SHIFT IS SUBTRACTED, A DROP WHERE IT ALREADY IS SENDS NOTHING, A DROP "
          "PAST THE END MEANS LAST, AND THE SAME CODE RUNS IN BOTH VIEWS")
    return 0


sys.exit(main())
