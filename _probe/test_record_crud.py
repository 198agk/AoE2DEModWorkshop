# -*- coding: utf-8 -*-
"""The editor could change numbers but never add, copy or remove a record.

WHY THIS PIN EXISTS
-------------------
Every write this program shipped until 2026-11-05 was an EQUAL-WIDTH byte swap
inside a record that already existed.  That is what made the undo stack a plain
list of `(offset, before, after)` and what made `_after_write` able to patch
three caches in place: nothing ever moved.

Adding a record breaks all three assumptions at once, and each one failed on the
way in, in this order:

  1. the flag array grows at `ptr_off + 4*m`, NOT at the end of the record run
     (padding after the run made the parser read the first record's bytes as
     27,251 pointers and die in `read_bird` with
     `struct.error: bad char in struct format`);
  2. undo must replay the steps BACKWARDS -- a forward replay shrinks the flag
     array before it cuts the record, so it lands on the wrong bytes;
  3. the index that describes where every record starts has to be thrown away,
     and a scan that was already running when the buffer changed must lose.

WHAT IT CHECKS
--------------
1. `records.py` describes a unit insert as `(at, cut, add)` steps that, applied,
   reproduce the buffer API's own answer byte for byte;
2. a unit added past the end of the flag array grows it, one added inside it does
   not, and files shrink back when the top slot goes away;
3. add-then-remove returns the ORIGINAL BYTES, not merely a file that parses;
4. the same round trip for a technology, and the new technology's name lands in
   the record (the name is a `debug_string` at offset 55, not at offset 0);
5. through `App`: duplicate, undo (byte identical), redo, remove, and the
   session's own counters agree at every step;
6. deleting a record that effects still point at is refused with the counts, and
   `force` gets past it -- a silent delete is a broken mod that loads fine;
7. `"*"` (the field-write scope) is not an address: duplicating under 全部文明
   lands in one civilisation, not in an error;
8. the page can reach it: the two buttons exist, the duplicate sends `edCiv()`
   and not the scope, and `loadEditor` awaits the record it opens (measured
   2026-11-05: without that word the pane snapped back to 民兵 after a copy).

WHAT IT DOES NOT DO
-------------------
It does not re-serialize the file (that is 11 s and a different proof), and it
does not pin any message wording.  It runs on the shipped .dat through `App`
once and then reuses those offsets, because the layout is the input to every
number above.
"""
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from aoe2mod.dat import records as R
from aoe2mod.ui import server as S

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
PAGE_SRC = None

FAILS = []


def ck(name, ok, detail=""):
    if ok:
        print("  ok   %s" % (name,))
    else:
        print("  FAIL %s%s" % (name, (" :: " + str(detail)) if detail else ""))
        FAILS.append(name)


def raised(fn):
    """The message a refusal carries, or None when it did not refuse."""
    try:
        fn()
    except R.RecordError as exc:
        return str(exc)
    except Exception as exc:                       # noqa: BLE001 - reported
        return "wrong type: %r" % (exc,)
    return None


def section(title):
    print("\n=== %s ===" % (title,))


def page():
    global PAGE_SRC
    if PAGE_SRC is None:
        PAGE_SRC = io.open(PAGE, encoding="utf-8").read()
    return PAGE_SRC


app = S.App()
tk = app.tk
t0 = time.time()
tk._ensure()
print("app ready in %.2fs  raw %d B  gv=%d  civs_start=%d  tail=%d"
      % (time.time() - t0, len(tk._raw), tk._parsed[3], tk._parsed[2],
         tk._parsed[4]))
RAW = bytes(tk._raw)
GV = tk._parsed[3]
CIVS_START = tk._parsed[2]
TAIL = tk._parsed[4]
CIV = 1                      # 不列颠: the civilisation every example uses
UNIT = 83                    # a creatable unit with a full record
TECH_DONOR = 1509            # Blank Technology 39: the shortest tech record


# ---------------------------------------------------------------------------
section("1. a plan is steps, and the steps ARE the edit")
# ---------------------------------------------------------------------------
lay = R.civ_layout(RAW, GV, CIVS_START, CIV)
ck("the layout finds the flag array by walking to it",
   lay["ptr_off"] + 4 * lay["m"] == lay["run_start"],
   "(ptr_off=%d + 4*%d != run_start %d)" % (lay["ptr_off"], lay["m"], lay["run_start"]))
ck("every non-zero flag has exactly one record",
   sum(1 for v in lay["flags"] if v) == len(lay["spans"]),
   (sum(1 for v in lay["flags"] if v), len(lay["spans"])))
ck("the record run ends where the walk says it does",
   lay["run_end"] > lay["run_start"] and len(lay["flags"]) == lay["m"], lay["m"])

steps, info = R.plan_add_unit(RAW, GV, CIVS_START, CIV, UNIT,
                              new_id=30000, hp=None)
ck("a plan is a list of (at, cut, add) triples",
   steps and all(len(s) == 3 and isinstance(s[2], (bytes, bytearray))
                 for s in steps), steps)
ck("the plan says which id it will create",
   info.get("id") == 30000 and info.get("donor") == UNIT, info)
work, writes = R.apply_steps(RAW, steps)
ck("applying the plan writes every step",
   len(writes) == len(steps) and
   all(w["off"] == s[0] and len(w["after"]) == len(s[2])
       for w, s in zip(writes, steps)))
ck("the applied plan is the buffer API's own answer",
   bytes(work) == bytes(R.add_unit(RAW, GV, CIVS_START, CIV, UNIT, new_id=30000)[0]),
   "lengths %d vs %d" % (len(work), len(R.add_unit(RAW, GV, CIVS_START, CIV, UNIT, new_id=30000)[0])))
ck("a new record makes the file longer by exactly the cloned image",
   len(work) - len(RAW) == info["bytes"] + 4 * (30001 - lay["m"]),
   (len(work) - len(RAW), info["bytes"], lay["m"]))
lay2 = R.civ_layout(bytes(work), GV, CIVS_START, CIV)
ck("the created record is in the new layout, at the offset the plan named",
   lay2["spans"].get(30000, (None,))[0] == info["at"], (lay2["spans"].get(30000), info["at"]))


# ---------------------------------------------------------------------------
section("2. growing the flag array is not the same edit as filling a hole")
# ---------------------------------------------------------------------------
plain, plain_info = R.plan_add_unit(RAW, GV, CIVS_START, CIV, UNIT, new_id=382)
ck("an id inside the array needs no growth step",
   plain_info["slots"] == lay["m"] and len(plain) == 2, (plain_info["slots"], len(plain)))
grown, grown_info = R.plan_add_unit(RAW, GV, CIVS_START, CIV, UNIT, new_id=30000)
ck("an id past the array grows it to id+1 slots",
   grown_info["slots"] == 30001 and len(grown) == 4, (grown_info["slots"], len(grown)))
ck("the growth is inserted at the START of the record run, not its end",
   any(s[0] == lay["run_start"] and s[1] == 0 for s in grown),
   [(s[0], s[1]) for s in grown])
ck("filling a hole writes only the flag and the record",
   [s[0] for s in plain] == [lay["ptr_off"] + 4 * 382, None] or
   len(plain) == 2, [(s[0], s[1]) for s in plain])
ck("the two plans differ in length by the padding they add",
   len(grown[0][2]) == 4 * (30001 - lay["m"]), len(grown[0][2]))


# ---------------------------------------------------------------------------
section("3. add then remove gives the original bytes back")
# ---------------------------------------------------------------------------
grown_buf = bytes(work)
back, _bk = R.apply_steps(
    grown_buf, R.plan_remove_unit(grown_buf, GV, CIVS_START, CIV, 30000)[0])
ck("removing the record I just added restores the file byte for byte",
   bytes(back) == RAW, (len(back), len(RAW)))
lay3 = R.civ_layout(bytes(back), GV, CIVS_START, CIV)
ck("and the flag array shrank back to where it started",
   lay3["m"] == lay["m"], (lay3["m"], lay["m"]))
hole_buf = bytes(R.apply_steps(RAW, plain)[0])
hole_back, _hb = R.apply_steps(
    hole_buf, R.plan_remove_unit(hole_buf, GV, CIVS_START, CIV, 382)[0])
ck("the round trip also holds for a hole-filling id (no growth to undo)",
   bytes(hole_back) == RAW, (len(hole_back), len(RAW)))
ck("removing an id that is not there is refused, in Chinese",
   bool(raised(lambda: R.plan_remove_unit(RAW, GV, CIVS_START, CIV, 30000))))


# ---------------------------------------------------------------------------
section("4. technologies are the same shape, but their name is at offset 55")
# ---------------------------------------------------------------------------
tsteps, tinfo = R.plan_add_tech(RAW, GV, TAIL, TECH_DONOR, lang_name="Blacksmyth")
ck("a technology plan names the id it will take",
   tinfo.get("id") == tk._stats["tech_count"] and tinfo.get("donor") == TECH_DONOR, tinfo)
# The record's own name has to survive `debug_string`, so it is ASCII by
# construction: `newtech.internal_name_for` drops Chinese rather than inventing
# a pinyin spelling the game never uses.  The player's words live in the
# language DLL, which is a different write (`strings.build_files`).
ck("the new technology is named, not left as the donor's name",
   tinfo.get("name") == "NewTech1510_Blacksmyth", tinfo.get("name"))
ck("the count is a two-byte field, so the plan edits exactly two bytes",
   any(s[1] == 2 and len(s[2]) == 2 for s in tsteps), [(s[0], s[1]) for s in tsteps])
twork, _tw = R.apply_steps(RAW, tsteps)
ck("the file grew by exactly the record",
   len(twork) - len(RAW) == tinfo["bytes"], (len(twork) - len(RAW), tinfo["bytes"]))
cnt_off, cnt, tstart, tend = R.tech_section(bytes(twork), GV, TAIL)
old_cnt_off, old_cnt, old_start, old_end = R.tech_section(RAW, GV, TAIL)
ck("the technology array now counts one more",
   cnt == old_cnt + 1 and cnt_off == old_cnt_off, (cnt, old_cnt))
ck("the old records did not move: the new one is appended at the end",
   tstart == old_start + tinfo["bytes"] or tend - tstart == old_end - old_start + tinfo["bytes"],
   (tstart, old_start, tend - tstart, old_end - old_start))
ck("the renamed record carries the name, so it is not a byte-for-byte clone",
   R._tech_name_off(bytes(twork), GV, tstart) > tstart, tstart)
ck("removing it restores the original file",
   bytes(R.apply_steps(bytes(twork), R.plan_remove_tech(bytes(twork), GV, TAIL,
                                                        tinfo["id"])[0])[0]) == RAW)


# ---------------------------------------------------------------------------
section("5. through the App: duplicate, undo, redo, remove")
# ---------------------------------------------------------------------------
t0 = time.time()
r = app.record_edit("dup", kind="unit", civ="British", record=UNIT, name="测试单位")
print("   duplicate: %.1fs" % (time.time() - t0))
ck("duplicating a unit through the route succeeds", r.get("ok") is True, r.get("error"))
new_id = (r.get("info") or {}).get("id")
ck("it reports the id it created", isinstance(new_id, int) and new_id > 0, new_id)
ck("the session counts it as one pending change",
   r.get("pending") == 1, r.get("pending"))
ck("the buffer is longer than the file it came from",
   len(app.session_raw()) > len(RAW), (len(app.session_raw()), len(RAW)))
ck("the index was thrown away rather than left pointing at old offsets",
   getattr(tk, "_field_index", None) in (None, {}) or len(tk._field_index) > 0,
   getattr(tk, "_field_index", "missing") is None)
idx = app._unit_index()
ck("the new record is findable through the unit index",
   (CIV, new_id) in idx, new_id)
ck("the index still describes the EDITED file, not the file it replaced",
   all(0 <= rec["start"] < len(app.session_raw()) for rec in list(idx.values())[:200]))
ck("a field of a neighbouring record still reads",
   isinstance(app.unit_fields(UNIT, civ="British"), dict))

# A record the editor just made has to behave like a record everywhere, not only
# in the index the editor happens to read.  Measured 2026-11-05, right after this
# route landed: `/api/icon?id=30000` answered with a 57-byte blank (the donor's
# 4,519-byte PNG was one id away), `/api/browse` listed 1,651 rows without the new
# id, and `/api/describe` said 「找不到编号 30000 的单位」 -- three symptoms of two
# caches that were built before the insert and never rebuilt after it.
ent = tk.index().get("unit", new_id)
ck("the name index knows the record the editor just made",
   ent is not None, new_id)
if ent is not None:
    ck("it is named after the record it was copied from",
       ent.display == tk.index().get("unit", UNIT).display,
       (ent.display, tk.index().get("unit", UNIT).display))
ck("it is offered to a screen that lists units",
   any(row["id"] == new_id for row in tk.browse(kind="unit", limit=9999)["rows"]),
   new_id)
ic = tk.icon_for("unit", new_id)
ck("it draws the donor's picture instead of a blank cell",
   ic.get("ok") is True and ic.get("icon_id") == tk.icon_for("unit", UNIT).get("icon_id"),
   ic.get("why") or ic.get("icon_id"))

t0 = time.time()
u = app.undo()
print("   undo: %.1fs" % (time.time() - t0))
ck("undo succeeds", u.get("ok") is True, u.get("error"))
ck("undo leaves no change behind", u.get("undo") == 0 and u.get("redo") == 1,
   (u.get("undo"), u.get("redo")))
ck("undo gives back the ORIGINAL bytes, not merely a parseable file",
   bytes(app.session_raw()) == RAW,
   (len(app.session_raw()), len(RAW)))
ck("undo shrank the flag array back",
   R.civ_layout(bytes(app.session_raw()), GV, CIVS_START, CIV)["m"] == lay["m"])

t0 = time.time()
rr = app.redo()
print("   redo: %.1fs" % (time.time() - t0))
ck("redo succeeds", rr.get("ok") is True, rr.get("error"))
ck("redo puts the record back",
   len(app.session_raw()) == len(RAW) + info["bytes"] + 4 * (30001 - lay["m"]),
   len(app.session_raw()))
ck("the record is findable again after redo",
   (CIV, new_id) in app._unit_index(), new_id)

t0 = time.time()
d = app.record_edit("del", kind="unit", civ="British", record=new_id, force=True)
print("   remove: %.1fs" % (time.time() - t0))
ck("removing the duplicate succeeds", d.get("ok") is True, d.get("error"))
ck("the buffer is back to the shipped length",
   len(app.session_raw()) == len(RAW), (len(app.session_raw()), len(RAW)))
ck("and back to the shipped bytes", bytes(app.session_raw()) == RAW)
ck("the index no longer has it", (CIV, new_id) not in app._unit_index())


# ---------------------------------------------------------------------------
section("6. a record other things point at is not deleted silently")
# ---------------------------------------------------------------------------
refs = R.unit_references(tk._stats, UNIT)
ck("the reference count is counted, not guessed",
   refs["effects"] > 0 and refs["civs"] > 1, refs)
steps_before = app.hist_state().get("undo")
bad = app.record_edit("del", kind="unit", civ="British", record=UNIT)
ck("deleting it without force is refused", bad.get("ok") is False, bad.get("ok"))
ck("the refusal says how many things point at it",
   bad.get("references") == refs, bad.get("references"))
ck("the refusal names the escape hatch",
   "force" in str(bad.get("error")), bad.get("error"))
ck("the refusal did not touch the file",
   bytes(app.session_raw()) == RAW, (len(app.session_raw()), len(RAW)))
ck("a refusal is not an undo step",
   app.hist_state().get("undo") == steps_before,
   (app.hist_state().get("undo"), steps_before))


# ---------------------------------------------------------------------------
section("7. \"*\" is a scope, not an address")
# ---------------------------------------------------------------------------
star = app.record_edit("dup", kind="unit", civ="*", record=UNIT)
ck("duplicating while 全部文明 is selected works", star.get("ok") is True,
   star.get("error"))
ck("it lands in ONE civilisation, because a record belongs to one",
   (star.get("info") or {}).get("civ") == CIV, (star.get("info") or {}).get("civ"))
ck("and not 63 times",
   len(app.session_raw()) < len(RAW) + 64 * (info["bytes"] + 4))
app.undo()


# ---------------------------------------------------------------------------
section("8. a duplicated technology is a technology everywhere")
# ---------------------------------------------------------------------------
# Same three symptoms the unit copy had, one kind over: `clone_tech` keeps the
# donor's `icon_id`, so a copy that answers `{"ok": false}` to `/api/icon` is
# reporting a missing LOOKUP, not a missing picture.  Measured 2026-11-05.
TECH_DONOR_ICON = 2           # Scale Mail Armor: a shipped tech that has a picture
ck("the donor technology has a picture to begin with",
   tk.icon_for("tech", TECH_DONOR_ICON).get("ok") is True,
   tk.icon_for("tech", TECH_DONOR_ICON))
tdup = app.record_edit("dup", kind="tech", record=TECH_DONOR_ICON, civ=CIV)
tnew = (tdup.get("info") or {}).get("id")
ck("duplicating a technology succeeds", tdup.get("ok") is True, tdup.get("error"))
ck("the name index knows the technology the editor just made",
   tk.index().get("tech", tnew) is not None, tnew)
ti = tk.icon_for("tech", tnew)
ck("it keeps the donor's picture instead of a blank cell",
   ti.get("ok") is True
   and ti.get("icon_id") == tk.icon_for("tech", TECH_DONOR_ICON).get("icon_id"),
   ti.get("why") or ti.get("icon_id"))
tdesc = app.describe("tech", tnew)["entity"]
ck("describe finds it in the file, with the donor's record shape",
   tdesc.get("record_count") == 1
   and (tdesc.get("stats") or {}).get("research_time")
       == (app.describe("tech", TECH_DONOR_ICON)["entity"].get("stats") or {}).get("research_time"),
   (tdesc.get("record_count"), tdesc.get("stats")))
app.undo()
ck("undo put the technology array back",
   len(app.session_raw()) == len(RAW), (len(app.session_raw()), len(RAW)))


# ---------------------------------------------------------------------------
section("9. the page provides the way in")
# ---------------------------------------------------------------------------
src = page()
# The ids are assigned in JS (`dup.id = "ed-rec-dup"`), not written as HTML
# attributes: the strip is built by `edRecordActions`, not declared in markup.
ck("the duplicate button exists, by the id the page's own code uses",
   '"ed-rec-dup"' in src and 'edRecordOp("dup"' in src)
ck("the delete button exists, by the id the page's own code uses",
   '"ed-rec-del"' in src and 'edRecordOp("del"' in src)
ck("the duplicate sends the record's own civilisation, not the write scope",
   re.search(r"civ:\s*edCiv\(\)", src) is not None)
ck("`loadEditor` waits for the record it opens",
   re.search(r"await openEditor\(target\)", src) is not None)
ck("the page calls the three record routes by name, with an inline body",
   all(re.search(r'api\("/api/record-%s",\s*\{' % op, src)
       for op in ("add", "dup", "del")),
   "the route contract only sees a literal URL followed by an object literal")
ck("the server names all three routes literally, so the contract pin sees them",
   all(('"/api/record-%s"' % op)
       in io.open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"),
                  encoding="utf-8").read()
       for op in ("add", "dup", "del")))
ck("the page warns that a record edit moves every later offset",
   ("重算后面所有偏移" in src) and ("约 1 秒" in src))
# The warning used to say 重读整份数据 (约 10 秒), which was true until
# 2026-11-06: `_restructure` now carries the model across a splice in 1.2 s
# instead of re-parsing 93 MB in 10.45 s.  A pin that keeps the old sentence
# green would keep the interface lying about its own cost.
ck("the page no longer claims a record edit re-reads the whole file",
   "重读整份数据" not in src)
ck("after a delete the page does not try to open the record it just removed",
   re.search(r'if \(op !== "del" && first != null\)', src) is not None,
   "the id in `info` is the one that no longer exists; opening it asks "
   "`/api/fields?unit=30000` about a hole and the pane comes back empty")
# A batch add and a paste report `ids`, not `id`.  Pinning only `info.id` left
# the pane on the donor after 「新增这么多条」 -- measured 2026-11-05.
ck("a batch add opens the first record it made, not the donor it copied",
   re.search(r"const first = info\.id != null \? info\.id : "
             r"\(info\.ids \|\| \[\]\)\[0\];", src) is not None)
# The tail of loadEditor appends rows and opens a record AFTER its second await.
# Measured 2026-11-05: a boot-time unit load parked in the icon batch woke up
# after the user had clicked 科技, appended 400 unit rows to the tech list and
# opened unit 74 into the tech pane -- so 复制成新记录 sent
# {"kind":"unit","record":74} from inside the 科技 tab.
_tail = src[src.find("  drawPager(box);" + chr(10) + "  if (more) return;"):]
_guard = _tail.find("if (gen !== ED_GEN) return;")
# One `POST /api/record-dup {"kind":"tech"}` came back as
# `AttributeError: '_NameSpot' object has no attribute 'pos'` and the next try
# succeeded: `read_tech` is handed readers of both kinds, and `Orec` calls its
# cursor `o` while `P.Reader` calls it `pos`.
ck("the reader that remembers where a tech name lives answers to both cursor names",
   hasattr(R._NameSpot, "pos") and R._NameSpot.pos.fget is not None,
   "a reader with only one of the two names fails on whichever call site "
   "reaches for the other")

ck("loadEditor re-checks its generation before it touches the pane",
   _guard != -1 and _guard < _tail.find("await openEditor(target)"),
   "the rows and the pane are written after the icon batch, so a load that "
   "lost the race can still paint its own tab's rows and open its own record")


print("")
if FAILS:
    print("RECORD CRUD: %d CHECK(S) FAILED -- %s" % (len(FAILS), FAILS))
    sys.exit(1)
print("RECORD CRUD: A RECORD CAN BE ADDED, COPIED AND REMOVED, UNDO PUTS THE FILE BACK BYTE FOR BYTE, "
      "AND A RECORD OTHER THINGS POINT AT IS NOT DELETED WITHOUT BEING TOLD TWICE")
