# -*- coding: utf-8 -*-
"""The left-hand grid listed records the right-hand pane refused to open.

Measured 2026-11-13, on the shipped .dat (gv 54, 63 civilizations):

    /api/fields?unit=48&civ=*  ->  {ok: false,
        error: 「British」这个文明里没有第 48 号单位}

Unit 48 is the boar.  289 of the 1..1700 ids have no copy in civilization
index 1 (British, the reference every number in the pane is quoted from) and
276 of those live somewhere else -- mostly Gaia's: the boar 48, the gold mine
66, the wolf 89, the two fish 69 and 53.  `browse` lists 1,651 named units, so
363 rows in the grid were dead: click 「野猪」 and the pane answered with one
red line saying the record does not exist, in a civilization the player never
picked.

WHY THE FIX IS A FALLBACK AND NOT "just use the record's own civilization":
British has to stay the preference.  It is the copy the pane has always quoted
and moving the reference would silently re-display 1,363 ids from a different
copy -- a change nobody asked for, dressed as a bug fix.  So: read British,
fall back to the lowest civilization index that HAS the record (for the
Gaia-only ids that is 0, the civilization they belong to), and say so.

What this pins:
  1. the 363 dead rows open, and quote their own civilization;
  2. the 1,363 that British does carry still quote British;
  3. a civ named explicitly is never overridden (asking for British's boar is
     still a refusal, and it now names where the record lives);
  4. an id that exists nowhere says exactly that, not "not in this civ";
  5. the write path has the same rule -- a dry write to 全部文明 of the boar
     resolves a real offset and a real old value;
  6. the page prints the fallback instead of pretending.

Run: python -X utf8 _probe/test_reference_civ.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.ui.server as S

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
page = open(PAGE, encoding="utf-8").read()

FAILED = []


def ck(what, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", what,
                         (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILED.append(what)
    return ok


def section(title):
    print()
    print("=== %s ===" % title)


app = S.App()
app.session_raw()
idx = app._unit_index()
civs = app.tk._civs

# ---------------------------------------------------------------------------
section("1. the grid and the pane agree about which ids exist")
# ---------------------------------------------------------------------------
MISSING_IN_REF = sorted({u for (_ci, u) in idx} - {u for (ci, u) in idx
                                                 if ci == 1})
ck("there really are ids the reference civilization does not carry",
   len(MISSING_IN_REF) > 200, "%d ids" % (len(MISSING_IN_REF),))
ck("and the boar 48 is one of them (the reported one)",
   48 in MISSING_IN_REF, MISSING_IN_REF[:8])

for uid in (48, 66, 89, 241, 53):
    d = app.unit_fields(uid, civ="*")
    ok = d.get("ok") is True and d.get("field_count", 0) > 0
    ck("unit %d opens" % (uid,), ok, d.get("error") or d.get("field_count"))
    if not ok:
        continue
    ck("...and says it fell back", d.get("civ_fell_back") is True, d.get("civ"))
    ck("...to the civilization that actually has it",
       d.get("civ_index") in {ci for (ci, u) in idx if u == uid},
       (d.get("civ"), d.get("civ_index")))

# ---------------------------------------------------------------------------
section("2. British still answers for everything British carries")
# ---------------------------------------------------------------------------
for uid in (1, 74, 83, 448, 1251):
    d = app.unit_fields(uid, civ="*")
    ck("unit %d is British's, as before" % (uid,),
       d.get("ok") is True and d.get("civ_index") == 1
       and d.get("civ_fell_back") is False,
       (d.get("civ"), d.get("civ_index"), d.get("civ_fell_back")))

# ---------------------------------------------------------------------------
section("3. an explicitly named civilization is never overridden")
# ---------------------------------------------------------------------------
d = app.unit_fields(48, civ="British")
ck("asking for British's boar is still a refusal", d.get("ok") is False,
   d.get("ok"))
ck("...and names where the record lives instead of a dead end",
   ("Gaia" in str(d.get("error"))) and ("48" in str(d.get("error"))),
   d.get("error"))
ck("...and lists the owners for the caller to jump to",
   d.get("owners") == [0], d.get("owners"))
d = app.unit_fields(48, civ="Gaia")
ck("asking for Gaia's boar works, and is not called a fallback",
   d.get("ok") is True and d.get("civ") == "Gaia"
   and d.get("civ_fell_back") is False,
   (d.get("civ"), d.get("civ_fell_back")))

# ---------------------------------------------------------------------------
section("4. an id that exists nowhere says exactly that")
# ---------------------------------------------------------------------------
d = app.unit_fields(19999, civ="*")
ck("a nonexistent id is refused", d.get("ok") is False, d.get("ok"))
ck("...without sending the reader to look for a civilization",
   "都没有记录" in str(d.get("error")), d.get("error"))
ck("...and without offering owners it does not have",
   "owners" not in d, sorted(d))

# ---------------------------------------------------------------------------
section("5. the write path resolves the same record")
# ---------------------------------------------------------------------------
# A dry write is the honest test here: it walks to a real offset and reads the
# real old value, which is exactly the work a live write would then do.
w = app.set_unit_field(48, "HitPoints", 12, civ="*", dry=True)
ck("a dry write to 全部文明 of the boar finds the record", w.get("ok") is True,
   w.get("error"))
ck("...at a real offset with a real old value",
   isinstance(w.get("offset"), int) and w.get("offset", 0) > 0
   and isinstance(w.get("before"), (int, float)), (w.get("offset"), w.get("before")))
ck("...and touches every copy that has it, which is one",
   w.get("copies") == 1 and w.get("copies_changing") == 1,
   (w.get("copies"), w.get("copies_changing")))
w2 = app.set_unit_field(48, "HitPoints", 12, civ="British", dry=True)
ck("a write aimed at British is still refused, with the same message",
   w2.get("ok") is False and "只在" in str(w2.get("error")), w2.get("error"))

# ---------------------------------------------------------------------------
section("6. the page prints the fallback")
# ---------------------------------------------------------------------------
ck("the subtitle reads civ_fell_back", "d.civ_fell_back" in page)
ck("...and says the reference civilization has nothing to quote",
   "默认参照的文明没有这条" in page)
ck("...instead of the old two-branch line",
   "按 \" + (d.civ_zh || d.civ) + \" 显示 · 改全部 \" + d.civ_copies"
   not in page)
# The dropdown above the pane is a record ADDRESS, so it has to move too --
# otherwise the screen says 盖亚 in one line and 不列颠 in the control right
# above it.  Assigning `value` does not fire `onchange`, which is why this is a
# two-line fix and not a re-read loop.
ck("the civilization dropdown follows the fallback",
   ("const sel = $.ed-civ" not in page)
   and re.search(r"if \(fell\) \{\s*const sel = ", page) is not None
   and "const sel = $(" + chr(34) + "#ed-civ" + chr(34) + ");" in page)
ck("...and does not re-open the pane when it moves",
   re.search(r"sel\.value = d\.civ;", page) is not None)
server = open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"),
              encoding="utf-8").read()
ck("one helper decides the reference civilization, used by both paths",
   server.count("self._unit_read_ref(") == 3
   and server.count("def _unit_read_ref(") == 1,
   server.count("self._unit_read_ref("))
ck("the refusal is built in one place",
   server.count("def _unit_missing(") == 1
   and server.count("self._unit_missing(") == 3,
   server.count("self._unit_missing("))

print()
if FAILED:
    print("REFERENCE CIV: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
    sys.exit(1)
print("REFERENCE CIV: EVERY ROW THE GRID OFFERS OPENS -- THE PANE QUOTES THE "
      "REFERENCE CIVILIZATION WHERE IT HAS THE RECORD, THE CIVILIZATION THAT "
      "DOES WHERE IT DOES NOT, AND SAYS WHICH")
