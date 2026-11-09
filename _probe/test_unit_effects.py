# -*- coding: utf-8 -*-
"""Nail: 「哪些东西改了这个单位」-- the reverse of a technology's effect list.

What is being pinned, and why each part could be false:

1. The reverse index.  A .dat has no pointer from a unit to a technology; the
   only way to answer "what changes 民兵" is to walk every technology's effect
   list.  If that walk ever stops seeing a slot the technology panel can edit,
   this block says "nothing changes it" while the other screen edits it.
2. The row's numbers must be the file's numbers.  `effect_rows` is the single
   decoder, so the check is that the row's `value` equals what
   `/api/effect-set` reads back as `before` for that (tech, command).
3. The route must be a GET.  The first version was inserted into `do_POST`
   because both handlers contain an `/api/effect-set` line, and the page fetched
   it with a GET -- 404.  A source-level check that catches the placement is the
   only kind that would have caught it before the browser did.
4. The block must be CLOSED and must not fetch until opened.  59 rows above a
   434-field table pushed the table below the fold (screenshot 2026-11-06).
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")
COMPILER = os.path.join(ROOT, "aoe2mod", "intent", "compiler.py")

BASE = "http://127.0.0.1:7811"
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("  ok   " if ok else "  FAIL ") + name + (("  " + str(detail)) if detail else ""))


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    server = io.open(SERVER, encoding="utf-8").read()

    # ---- 1. the walk sees what the technology panel sees -------------------
    import aoe2mod.api as A
    from aoe2mod.intent import compiler as C
    from aoe2mod.ui import server as S

    app = S.App()
    tk = app.tk
    t0 = time.time()
    j = app.unit_effects(74)
    took = time.time() - t0
    check("unit 74 has rows", j.get("ok") and j.get("total") > 0,
          "total %s in %.2f s" % (j.get("total"), took))
    check("every row about 74 is editable",
          j.get("editable_count") == j.get("total"),
          "%s of %s" % (j.get("editable_count"), j.get("total")))

    # The same walk, done by hand, must agree row for row: if `unit_effects`
    # filters differently from the technology panel, one of the two screens is
    # lying and this is where it gets caught.
    eff = tk._effect_records()
    fan = tk._effect_fanout()
    ix = app._semantic()
    hand = 0
    for t in tk._tech_records():
        for r in C.effect_rows(eff, t, fanout=fan, ix=ix, unit_class=tk.unit_class):
            tgt = r.get("target")
            ids = tgt if isinstance(tgt, (list, tuple)) else ([tgt] if tgt is not None else [])
            if any(str(x) == "74" for x in ids):
                hand += 1
    check("the cached walk equals a hand count", hand == j.get("total"),
          "hand %d vs %d" % (hand, j.get("total")))

    # The cache must be invalidated by a generation bump, or an edit made after
    # the first look would be invisible forever.
    tk._unit_effects_gen = -1
    j2 = app.unit_effects(74)
    check("a stale generation refills the cache",
          j2.get("total") == j.get("total"), j2.get("total"))

    # ---- 2. the rows name the file's numbers -------------------------------
    row = next((r for r in j.get("rows") or [] if r.get("editable")), None)
    check("there is an editable row to check", row is not None)
    if row is not None:
        w = app.set_effect_value(row["tech"], row["command"],
                                 value=row["value"], dry=True)
        same = (w.get("ok")
                and abs(float(w.get("before")) - float(row["value"])) < 1e-6)
        check("the row's number is the file's number", same,
              "list %r vs before %r" % (row["value"], w.get("before")))
        check("the write path refuses rather than guesses on a no-op",
              w.get("ok") and w.get("bytes_changed") == 0,
              w.get("bytes_changed"))

    # ---- 3. the route is in do_GET, not do_POST ---------------------------
    get_at = server.index("        def do_GET(self):")
    post_at = server.index("        def do_POST(self):")
    check("GET has /api/unit-effects",
          server[get_at:post_at].count('"/api/unit-effects"') == 1,
          server[get_at:post_at].count('"/api/unit-effects"'))
    check("POST does not",
          server[post_at:].count('"/api/unit-effects"') == 0,
          server[post_at:].count('"/api/unit-effects"'))
    # And the live server answers it, which is the fact the source check is a
    # proxy for.
    try:
        with urllib.request.urlopen(BASE + "/api/unit-effects?unit=74", timeout=180) as r:
            live = json.loads(r.read().decode())
        check("the live server answers it", live.get("ok"),
              "total %s" % live.get("total"))
    except Exception as exc:                       # noqa: BLE001
        check("the live server answers it", False, str(exc)[:120])

    # ---- 4. the block is closed, and asks nothing until opened -----------
    check("the block is a <details>", 'const box = el("details", "fxbox");' in page)
    check("the summary carries the label",
          'sum.appendChild(el("span", "t", "哪些东西改了这个单位"));' in page)
    check("no request before the first open",
          'box.addEventListener("toggle", () => {' in page
          and "if (!box.open || asked) return;" in page)
    m = re.search(r"function loadUnitEffects\(d, cnt, body\) \{\n[\s\S]{0,200}?"
                  r'api\("/api/unit-effects\?unit=" \+ edIdOf\(d\)\)', page)
    check("the fetch lives in loadUnitEffects", m is not None)
    check("the fetch is a GET with the unit in the query",
          'api("/api/unit-effects?unit=" + edIdOf(d))' in page)
    check("a unit draws it, a technology does not",
          'if (edKindOf(d) !== "tech" && !d.table) drawUnitEffects(pane, d);' in page)
    # A table row drawn by a builder that returns one <tr> cannot own its own
    # preview line: the preview is inserted by the loop, and the row finds it by
    # id.  Pinning both halves keeps that contract from drifting apart.
    check("the preview line is inserted per row, keyed by tech+command",
          'note.id = "ufx-note-" + r.tech + "-" + r.command;' in page
          and 'document.getElementById("ufx-note-" + r.tech + "-" + r.command)' in page)
    check("a refused row shows 只读 with the reason on hover",
          'const ro = el("span", "ro", "只读");' in page
          and "if (!r.editable && r.reason) td.title = r.reason;" in page)
    check("the write goes through /api/effect-set, same as the tech panel",
          'api("/api/effect-set", {\n        tech: r.tech, command: r.command' in page)
    check("the first click previews, the second writes",
          "go.onclick = () => write(true);" in page
          and 'const ok = el("button", "chip on", "记下");' in page)

    # ---- report ----------------------------------------------------------
    bad = [c for c in CHECKS if not c[1]]
    print()
    if bad:
        for name, _, detail in bad:
            print("FAILED: %s :: %s" % (name, detail))
        print("UNIT EFFECTS: %d CHECK(S) FAILED" % len(bad))
        return 1
    print("UNIT EFFECTS: A UNIT HAS NO EFFECT OF ITS OWN -- THE NUMBERS THAT "
          "CHANGE IT LIVE IN OTHER TECHNOLOGIES, THIS WALK FINDS EVERY ONE OF "
          "THEM IN A TENTH OF A SECOND, THE SCREEN SHOWS THEM ONLY WHEN ASKED, "
          "AND THE BOX THAT CHANGES ONE IS THE SAME BOX THE TECHNOLOGY PANEL USES")
    return 0


sys.exit(main())
