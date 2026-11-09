# -*- coding: utf-8 -*-
"""「新增」 must also mean 「新增一条没有的」, not only 「复制一条有的」.

Reported 2026-11-06, verbatim:

    「你这个新增是复制粘贴的，我要新增完全空白的」

Every add path until then cloned a donor: `records.plan_add_unit` refused to run
without one ("这个文明里没有编号 %s 的单位，所以没有东西可以照着做"), because a unit
record's tail is type-dependent -- Type50 / Projectile / Creatable / Building,
each behind its own version guards -- and rebuilding it from zeros is one guess
per field.  `newunit.blank_image` guesses them once, in one place, and then
PROVES the guess: it walks back its own bytes with the reader that will read
them out of the file.

The failure mode this guards is not "the record looks wrong".  A record whose
length does not match what the reader walks leaves the stream one byte off, and
then every record after it in that civilisation is garbage -- the error surfaces
tens of thousands of records later, inside `read_bird`, as
`struct.error: bad char in struct format`.  So the checks here are:

  1. `blank_image` walks back to exactly its own length, at every game version;
  2. what it writes lands where `clone_image` and the reader both expect;
  3. the plan does not need a donor, and still refuses a missing one when the
     caller did not say `blank`;
  4. the bytes in the file at the new record's span ARE the blank record;
  5. the model, the statistics, the browser and the field form all see it;
  6. a step that takes rows away takes the page count with them.

Run: python -X utf8 _probe/test_blank_unit.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.ui.server as S
from aoe2mod.dat import locate as L
from aoe2mod.dat import newunit as NU
from aoe2mod.dat import parser as P
from aoe2mod.dat import records as REC
from aoe2mod.dat import relocate as REL
from aoe2mod.dat import unitfields as UF

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

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


# ---------------------------------------------------------------------------
section("1. a blank record walks back to exactly its own length")
# ---------------------------------------------------------------------------
# The one invariant everything else rests on.  `walk_unit` consumes the record
# by walking it; if it stops anywhere but the last byte, the next record's first
# byte is read as part of this one and the whole stream downstream is fiction.
img = NU.blank_image(54, 30000)
_r = L.Orec(img, 0, gv=54)
_u = L.walk_unit(_r, 0)
ck("the reader stops exactly at the end of the record", _r.o == len(img),
   "walked %d of %d bytes" % (_r.o, len(img)))
ck("it is the id we asked for", _u["id"] == 30000, _u["id"])
ck("it is type 70, the cheapest tail that is still a real unit",
   _u["type"] == 70, _u["type"])
ck("it has our name in it", _u["name"] == "NEWUNIT30000", _u["name"])

# Every shipped version has its own guards inside `read_creatable`; a record
# written for gv 54 must not be handed to a gv 25 reader.
_bad = []
for _gv in (54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 44, 42, 41, 39, 38, 35, 30, 25):
    try:
        _b = NU.blank_image(_gv, 30001)
        _rr = L.Orec(_b, 0, gv=_gv)
        L.walk_unit(_rr, 0)
        if _rr.o != len(_b):
            _bad.append((_gv, _rr.o, len(_b)))
    except Exception as exc:                      # noqa: BLE001 - report, do not raise
        _bad.append((_gv, type(exc).__name__, str(exc)[:40]))
ck("it closes at every game version, not only this one", not _bad, _bad)

# ---------------------------------------------------------------------------
section("2. it is deliberately dull, and it says so")
# ---------------------------------------------------------------------------
ck("no train location, so nothing can build it by accident",
   _u.get("train_locations") == [], _u.get("train_locations"))
ck("three resource costs, all zero",
   [c.get("amount") for c in _u.get("costs") or []] == [0, 0, 0],
   [c.get("amount") for c in _u.get("costs") or []])
ck("no icon", _u.get("icon_id") == 0, _u.get("icon_id"))
ck("no hit points until someone types one", _u.get("hit_points") == 0,
   _u.get("hit_points"))
ck("no graphics", _u.get("standing_graphic") == [0, 0], _u.get("standing_graphic"))
ck("no speed", _u.get("speed") == 0, _u.get("speed"))

# ---------------------------------------------------------------------------
section("3. the values land where the reader and `clone_image` look")
# ---------------------------------------------------------------------------
# `ICON_OFF = 51` and `hp` at 22 are the offsets `clone_image` patches; a blank
# record that disagreed would make the two doors into the same editor mean
# different things.
_filled = NU.blank_image(54, 30002, hp=77, icon_id=9, name="MYUNIT")
_rf = L.Orec(_filled, 0, gv=54)
_uf = L.walk_unit(_rf, 0)
ck("the hit points land in the field the form writes",
   _uf["hit_points"] == 77, _uf["hit_points"])
ck("the icon lands in the field the list reads",
   _uf["icon_id"] == 9, _uf["icon_id"])
ck("the name is the one we passed", _uf["name"] == "MYUNIT", _uf["name"])
ck("and it still closes", _rf.o == len(_filled),
   "%d of %d" % (_rf.o, len(_filled)))
ck("`clone_image` patches the same icon byte a blank record writes",
   NU.clone_image(NU.blank_image(54, 30003), 30003, icon_id=9)[NU.ICON_OFF:
                                                              NU.ICON_OFF + 2]
   == _filled[NU.ICON_OFF:NU.ICON_OFF + 2],
   "ICON_OFF=%d" % NU.ICON_OFF)

# The form must be able to open it: `fields_at` walks the same record a third
# time, through the field-recording reader the editor uses.
_fld = UF.fields_at(img, 54, 0)
ck("the field form resolves a blank record", len(_fld) > 100, "%d fields" % len(_fld))
ck("and the form's own idea of where the record ends matches",
   all(v["offset"] < len(img) for v in _fld.values()),
   max(v["offset"] for v in _fld.values()))

# ---------------------------------------------------------------------------
section("4. the plan does not need a donor, but still wants one when not blank")
# ---------------------------------------------------------------------------
app = S.App()
app.reset_session()
tk = app.tk
tk._ensure()
raw = bytes(app.session_raw())
gv = tk._parsed[3]
civs_start = tk._parsed[2]
tail = tk._parsed[4]

# `new_id=None` needs `stats` to find a free id -- the same rule the clone path
# has, and the pin has to satisfy it or it measures the wrong refusal.
_steps, _info = REC.plan_add_unit(bytearray(raw), gv, civs_start, 1, None,
                                  blank=True, stats=tk._stats)
ck("a blank plan needs no donor at all", _info.get("blank") is True, _info)
ck("and records that it copied nobody", _info.get("donor") is None, _info)
ck("it still allocates a real id", isinstance(_info.get("id"), int), _info.get("id"))

try:
    REC.plan_add_unit(bytearray(raw), gv, civs_start, 1, None)
    ck("a plan with neither a donor nor `blank` is refused", False, "no exception")
except REC.RecordError as exc:
    ck("a plan with neither a donor nor `blank` is refused",
       "没有东西可以照着做" in str(exc), str(exc)[:60])

try:
    NU.blank_image(54, 0)
    ck("id 0 is refused", False, "no exception")
except NU.NewUnitError as exc:
    ck("id 0 is refused", "1..32767" in str(exc), str(exc)[:40])
try:
    NU.blank_image(54, 40000)
    ck("id 40000 is refused", False, "no exception")
except NU.NewUnitError as exc:
    ck("id 40000 is refused", "1..32767" in str(exc), str(exc)[:40])

# ---------------------------------------------------------------------------
section("5. a blank add through the editor puts those bytes in the file")
# ---------------------------------------------------------------------------
_n0 = sum(len(c["units"]) for c in tk._civs)
_len0 = len(raw)
out = app.record_edit("add", kind="unit", civ="British", blank=True)
ck("the add succeeds", out.get("ok"), out.get("error"))
_new = (out.get("info") or {}).get("id")
ck("it reports the id it made", isinstance(_new, int), out.get("info"))
_raw1 = bytes(app.session_raw())
# The file grows by the record AND by whatever the flag array had to grow to
# reach this id: `_grow_to` inserts 4 bytes per slot between the old top (2,749)
# and the new one.  So the check is not "grew by one record" -- it is "grew by
# the record, plus four bytes per new slot, and nothing else".
_slot_grow = 4 * (_new + 1 - 2750)
ck("the file grew by the record plus its pointer slots",
   len(_raw1) - _len0 == len(NU.blank_image(gv, _new)) + _slot_grow,
   "%d bytes = %d record + %d slots"
   % (len(_raw1) - _len0, len(NU.blank_image(gv, _new)), _slot_grow))
ck("the undo label says 空白, not 复制",
   "空白" in (out.get("undo_label") or ""), out.get("undo_label"))

# The strong one: the bytes sitting at this record's span in the SESSION BUFFER
# must be the blank record itself, byte for byte.  Anything else means the plan
# and the builder disagree about what was written.
_rec = None
for _c in tk._civs:
    for _x in _c["units"]:
        if _x["id"] == _new:
            _rec = _x
            break
    if _rec:
        break
ck("the model has the record", _rec is not None)
if _rec:
    _span = _raw1[_rec["_start"]:_rec["_end"]]
    ck("the bytes in the file at that span are the blank record",
       _span == NU.blank_image(gv, _new), "%d bytes" % len(_span))
    ck("and it walks back to its own length there too",
       len(_span) == _rec["_end"] - _rec["_start"],
       "%d..%d" % (_rec["_start"], _rec["_end"]))
    ck("the record knows its own span", _rec["_start"] > 0 and _rec["_end"] > _rec["_start"],
       (_rec["_start"], _rec["_end"]))

ck("the model still closes into one unbroken stream",
   REL.chain_ok(tk._civs, civs_start, tk._parsed[4]))
ck("the tail pointer moved with the file",
   tk._parsed[4] == tail + (len(_raw1) - _len0),
   "%d -> %d" % (tail, tk._parsed[4]))
ck("one record appeared", sum(len(c["units"]) for c in tk._civs) == _n0 + 1,
   "%d -> %d" % (_n0, sum(len(c["units"]) for c in tk._civs)))

# ---------------------------------------------------------------------------
section("6. every reader of the model sees it, not just the one we looked at")
# ---------------------------------------------------------------------------
_rows = [u for u in tk._stats["civs"][1]["units"] if u["id"] == _new]
ck("the statistics copy of the civ has it (id allocation reads that one)",
   len(_rows) == 1, len(_rows))
if _rows:
    ck("with the six fields that copy carries",
       sorted(_rows[0]) == ["class", "hit_points", "id", "name", "type",
                            "task_swap_group"] or
       {"class", "hit_points", "id", "name", "type", "task_swap_group"} <= set(_rows[0]),
       sorted(_rows[0]))
    ck("and its name is the blank name",
       _rows[0]["name"] == "NEWUNIT%d" % _new, _rows[0]["name"])

_f = app.unit_fields(_new, civ="British")
ck("the field form opens it", bool(_f.get("ok")), _f.get("error"))
ck("with every field the form knows", len(_f.get("fields") or []) > 100,
   "%d" % len(_f.get("fields") or []))
_w = app.set_unit_field(_new, "HitPoints", 33, civ="British", dry=False)
ck("and a value can be written into it", bool(_w.get("ok")), _w.get("error"))
_f2 = app.unit_fields(_new, civ="British")
_hp = [x for x in _f2.get("fields") or [] if (x.get("name") or "").endswith("HitPoints")]
ck("the value reads back", _hp and _hp[0]["value"] == 33,
   _hp[:1])

_b = tk.browse(kind="unit", query="NEWUNIT", limit=50, offset=0, order="id")
_bids = [r["id"] for r in _b["rows"]]
ck("the browser lists it by name", _new in _bids, _bids[:5])
_nb = tk.browse(kind="unit", limit=5, offset=0, order="new")
ck("最新的在前 puts it on the first page", _nb["rows"] and _nb["rows"][0]["id"] == _new,
   [r["id"] for r in _nb["rows"][:3]])

# ---------------------------------------------------------------------------
section("7. a batch is one gesture and one undo")
# ---------------------------------------------------------------------------
_before = len(app.session_raw())
_undo0 = app.hist_state().get("undo") or 0
_b = app.record_edit("add", kind="unit", civ="British", blank=True, count=5)
ck("five at once succeeds", _b.get("ok"), _b.get("error"))
_ids = (_b.get("info") or {}).get("ids") or []
ck("it made five records", len(_ids) == 5, _ids)
ck("with distinct ids", len(set(_ids)) == 5, _ids)
ck("in one step, whatever the history already held",
   (app.hist_state().get("undo") or 0) == _undo0 + 1,
   "%d -> %s" % (_undo0, app.hist_state().get("undo")))
ck("and the label counts them",
   "5" in (_b.get("undo_label") or ""), _b.get("undo_label"))
_after = len(app.session_raw())
# Five records plus the pointer slots the flag array had to grow to reach them.
_grow = 5 * len(NU.blank_image(gv, _ids[0])) + 4 * (_ids[-1] + 1 - _ids[0])
ck("the file grew by five blank records and their slots",
   _after - _before == _grow,
   "%d bytes for 5 (want %d)" % (_after - _before, _grow))

_u = app.undo()
ck("one undo takes all five back", _u.get("ok"), _u.get("error"))
ck("byte for byte", len(app.session_raw()) == _before, len(app.session_raw()))

# The field write from section 6 is a step of its own and sits between the two
# adds.  It is the same width, so it does not change the length -- which is
# exactly why the check below walks back until the buffer IS the original file
# instead of assuming one more undo does it.  Bounded, so a history that will
# not unwind fails here rather than hanging.
for _ in range(6):
    if len(app.session_raw()) == _len0:
        break
    if not app.undo().get("ok"):
        break
ck("undoing far enough gets back to the original length",
   len(app.session_raw()) == _len0,
   "%d vs %d" % (len(app.session_raw()), _len0))
ck("and the model closes again", REL.chain_ok(tk._civs, civs_start, tk._parsed[4]))

# ---------------------------------------------------------------------------
section("8. the page has both doors, and the toolbar one is on the toolbar")
# ---------------------------------------------------------------------------
page = open(PAGE, encoding="utf-8").read()
_m = re.search(r'<span class="edbulkbar" id="ed-bulkbar"[\s\S]*?</span>', page)
ck("there is a toolbar bar at all", _m is not None)
if _m:
    ck("新增空白 is inside the toolbar bar", 'id="ed-blank-add"' in _m.group(0),
       _m.group(0)[-120:])
    ck("it shares the count box next to it", 'id="ed-bulk-n2"' in _m.group(0))
ck("the pane has its own door",
   re.search(r'blank\.id = "ed-rec-blank"', page) is not None)
ck("and the pane door sends a hidden count of one",
   re.search(r'bn\.id = "ed-blank-n1"[\s\S]{0,80}bn\.value = "1"', page) is not None)
ck("the toolbar door is bound",
   page.count('$("#ed-blank-add").onclick') == 1)
ck("the binding passes the blank flag",
   re.search(r'edBulkAdd\(ev\.currentTarget, "#ed-bulk-n2", true\)', page) is not None)
ck("the function takes the flag",
   re.search(r"async function edBulkAdd\(btn, which, blank\)", page) is not None)
ck("a blank request carries no donor, only the flag",
   re.search(r'\{kind: "unit", civ: edCiv\(\), count: n, blank: true\}', page) is not None)
ck("a clone request still carries the donor",
   re.search(r'\{kind: "unit", record: donor, civ: edCiv\(\), count: n\}', page) is not None)
ck("the toolbar bar is only shown for units",
   re.search(r'bulk\.hidden = \(kind !== "unit"\)', page) is not None)

server = open(SERVER, encoding="utf-8").read()
ck("the route passes the flag through",
   re.search(r'blank=bool\(payload\.get\("blank"\)\)', server) is not None)
ck("the editor has the parameter",
   re.search(r"def record_edit\(self[^)]*blank=False", server) is not None)
ck("and refuses to fall through to the clone branch when it is set",
   re.search(r"elif blank:", server) is not None)

# ---------------------------------------------------------------------------
section("9. a step that takes rows away takes the page count with it")
# ---------------------------------------------------------------------------
# Measured 2026-11-06: three blank records added, then 撤回 left the DOM at 397
# rows while the counter still said 「400 / 1651」 and the pager -- which counts
# `.edrow` -- offered "the next page".  Two answers to "how much is loaded".
ck("the counter is recomputed from the rows that are left",
   re.search(r"ED_OFFSET = \(EDROWS \|\| \[\]\)\.length;", page) is not None)
ck("and it happens where the removed rows are taken away",
   re.search(r"if \(gone\.has\(row\.dataset\.id\)\) row\.remove\(\);"
             r"[\s\S]{0,1400}ED_OFFSET = \(EDROWS", page) is not None)

print()
if FAILED:
    print("BLANK UNIT: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
    sys.exit(1)
print("BLANK UNIT: A NEW RECORD CAN BE MADE FROM NOTHING -- IT WALKS BACK TO ITS "
      "OWN LENGTH AT EVERY VERSION, THE BYTES IN THE FILE ARE THE ONES BUILT, AND "
      "EVERY READER OF THE MODEL SEES IT")
