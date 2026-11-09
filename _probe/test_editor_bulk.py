# -*- coding: utf-8 -*-
"""One thousand records as one gesture, and the keys that go with a selection.

Reported 2026-11-05, verbatim:

    「列表没有新增啊，我要新增1000甚至10000个id怎么办」
    「还有ctrl和shift的快捷键也要能用」

Both complaints are about the same shape of absence: the editor could only act
on ONE record, and only with the mouse.  This pin checks the machinery that
answers them, at three levels:

  * the data layer -- a batch is ONE plan, its flag window never reads record
    bytes as if they were pointers, and remove takes it all back byte for byte;
  * the server -- `count`, `ids` and `donors` reach `record_edit`, a batch is ONE
    undo step, and a thousand rows cost one splice rather than a thousand;
  * the page -- the keys are bound, the selection is visible, and the two
    orderings are the same rows read in the other direction.

Run: python -X utf8 _probe/test_editor_bulk.py
"""
import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A
from aoe2mod.dat import records as REC

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

FAILED = []


def ck(what, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", what, (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILED.append(what)
    return ok


def src(path):
    return io.open(path, encoding="utf-8").read()


def digest(b):
    return hashlib.sha256(bytes(b)).hexdigest()


print("=== 1. one plan for a thousand records ===")
tk = A.open_toolkit()
tk._ensure()
raw = bytes(tk._raw)
gv, civs_start = tk._parsed[3], tk._parsed[2]
CIV, DONOR = 1, 74
lay = REC.civ_layout(raw, gv, civs_start, CIV)
print("  civ %d: m=%d records=%d" % (CIV, lay["m"], len(lay["spans"])))

steps, info = REC.plan_add_units(raw, gv, civs_start, CIV, DONOR, count=1000,
                                 stats=tk._stats)
ids = info["ids"]
ck("a thousand records plan to four steps", len(steps) == 4, len(steps))
ck("the ids are a thousand consecutive numbers", ids == list(range(ids[0], ids[0] + 1000)),
   "%d..%d" % (ids[0], ids[-1]))
ck("the flag window grows to the highest new id", info["slots"] == ids[-1] + 1,
   info["slots"])
ck("the blob is one record per clone", len(steps[-1][2]) == 1000 * info["unit_bytes"],
   "%d bytes" % len(steps[-1][2]))
ck("every growth step inserts at the flag array's end, not the record run's",
   steps[0][0] == lay["run_start"] and steps[0][1] == 0, steps[0][:2])

work, writes = REC.apply_steps(raw, steps)
ck("applying the plan changes the length by the blob plus the new slots",
   len(work) - len(raw) == len(steps[-1][2]) + 4 * (info["slots"] - lay["m"]),
   len(work) - len(raw))
ck("undoing takes back exactly what it wrote",
   len(writes) == 4 and all(w["before"] or w["after"] for w in writes), len(writes))

back, _ = REC.apply_steps(work, [(w["off"], len(w["after"]), w["before"]) for w in reversed(writes)])
ck("the reverse of a batch is the original file, byte for byte", digest(back) == digest(raw))

print("=== 2. the flag window does not read record bytes ===")
# The first cut copied `buf[ptr_off+4*lo : ptr_off+4*hi+4]` without asking where
# the array ends; with hi past m that window swallows the first record's bytes
# and the parser then reads them as pointers (measured: `read_bird` -> "bad char
# in struct format").  A plan that adds INSIDE the array must not touch the run.
free = [i for i in range(1, min(lay["m"], 2749)) if i not in lay["spans"]]
print("  %d free slots inside the flag array, first %s" % (len(free), free[:3] if free else None))
if free:
    hole = free[0]
    st2, i2 = REC.plan_add_unit(raw, gv, civs_start, CIV, DONOR, new_id=hole,
                                stats=tk._stats)
    total = sum(len(add) - cut for _at, cut, add in st2)
    ck("adding into a hole does not grow the flags", i2["slots"] == lay["m"],
       (i2["slots"], lay["m"]))
    ck("and it writes only the record, the flag slot keeps its width",
       total == i2["bytes"], total)
    w2, _w = REC.apply_steps(raw, st2)
    try:
        import aoe2mod.dat.parser as P
        p2 = P.Parser(bytearray(w2))
        p2.parse()
        walked = True
    except Exception as exc:                      # noqa: BLE001 - the message IS the check
        walked = False
        print("     reparse said: %s" % (exc,))
    ck("the parser still walks that file", walked)
    ck("and the new id is in the civ it was added to",
       any(u["id"] == hole for u in p2.stats["civs"][CIV]["units"]))
else:
    print("  (no free slot inside the array -- skipped)")

print("=== 3. remove takes a batch back ===")
st3, i3 = REC.plan_remove_units(work, gv, civs_start, CIV, ids)
t3, _ = REC.apply_steps(work, st3)
ck("removing a thousand records gives back the original bytes",
   digest(t3) == digest(raw), "%d -> %d" % (len(work), len(t3)))
ck("and the flag array shrinks back with it",
   REC.civ_layout(t3, gv, civs_start, CIV)["m"] == lay["m"])

print("=== 4. free_unit_ids knows what is taken ===")
got = REC.free_unit_ids(tk._stats, 5)
ck("it hands back five numbers above everything the file already uses",
   len(got) == 5 and min(got) > max(lay["spans"]), got[:3])
ck("asking again gives the same answer while nothing is written",
   REC.free_unit_ids(tk._stats, 5) == got)
try:
    REC.free_unit_ids(tk._stats, 40000)
    ck("asking for more than exists is refused", False)
except REC.RecordError as exc:
    ck("asking for more than exists is refused", "放不下" in str(exc), str(exc)[:40])

print("=== 5. the server takes a batch as one gesture ===")
import aoe2mod.ui.server as S
app = S.App()
_ = app.tk
app.reset_session()
before = len(app.session_raw())
out = app.record_edit("add", kind="unit", civ="British", record=DONOR, count=3)
ck("count reaches record_edit", out.get("ok") and len((out.get("info") or {}).get("ids") or []) == 3,
   out.get("error"))
st = app.hist_state()
ck("three records are ONE undo step", st["undo"] == 1, st["undo"])
ck("the label says how many", "3 条" in (st.get("undo_label") or ""), st.get("undo_label"))
ck("the buffer grew by three records",
   len(app.session_raw()) > before, len(app.session_raw()) - before)

print("=== 6. a paste of several donors is one step too ===")
app.reset_session()
raw2 = bytes(app.session_raw())
out = app.record_edit("add", kind="unit", civ="British", donors=[74, 83, 4])
ck("donors reach record_edit", out.get("ok"), out.get("error"))
made = (out.get("info") or {}).get("ids") or []
ck("one record per donor", len(made) == 3, made)
ck("and the ids are all different", len(set(made)) == 3, made)
# The first cut handed `stats` to every clone, and `stats` never learns about the
# records the previous clone made -- so it returned the same free id four times
# and the paste died with "这个文明已经有编号 30000 的单位了" half applied.
ck("it is still one undo step", app.hist_state()["undo"] == 1, app.hist_state()["undo"])
app.undo()
ck("and undo takes the whole paste back", digest(app.session_raw()) == digest(raw2))
# A failure halfway must not leave half a paste behind.
app.reset_session()
raw3 = bytes(app.session_raw())
bad = app.record_edit("add", kind="unit", civ="British", donors=[74, 999999])
ck("a bad donor fails the whole paste", not bad.get("ok"), bad.get("ok"))
ck("and leaves no bytes behind", digest(app.session_raw()) == digest(raw3))

print("=== 7. browse can read the same rows backwards ===")
n_id = A.Toolkit.browse(tk, kind="unit", limit=5, offset=0, order="id")
n_new = A.Toolkit.browse(tk, kind="unit", limit=5, offset=0, order="new")
ck("order=new is reported back", n_new.get("order") == "new", n_new.get("order"))
ck("both orders carry the same total", n_new["total"] == n_id["total"],
   (n_id["total"], n_new["total"]))
# "new" is not another sort: it is the SAME list read from the other end.  So the
# first page of one is the last page of the other, reversed.
last = A.Toolkit.browse(tk, kind="unit", limit=5, offset=n_id["total"] - 5, order="id")
ck("the first page of new is the last page of id, backwards",
   [r["id"] for r in n_new["rows"]] == [r["id"] for r in reversed(last["rows"])],
   ([r["id"] for r in n_new["rows"]], [r["id"] for r in last["rows"]]))
ck("the newest record is on the first page when read backwards",
   n_new["rows"][0]["id"] == max(r["id"] for r in last["rows"]),
   n_new["rows"][0]["id"])

print("=== 8. the page binds the keys ===")
page = src(PAGE)
for key, why in (
    ('k === "Delete" || k === "Backspace"', "Delete removes the selection"),
    ('low === "a"', "Ctrl+A selects the page of rows"),
    ('low === "c"', "Ctrl+C copies the selection"),
    ('low === "v"', "Ctrl+V pastes it as new records"),
    ('k === "Escape"', "Escape clears the selection"),
    ('k === "ArrowDown" || k === "ArrowUp"', "arrows walk the list"),
):
    ck(why, key in page, key)
ck("Shift+click selects a range", "if (shift) {" in page and "EDROWS.slice(lo, hi + 1)" in page)
ck("Ctrl+click toggles one row", "EDPICK = EDPICK.concat(" in page and "EDPICK.filter(" in page)
ck("a text box keeps its own Ctrl+A", 'tag === "input" || tag === "textarea"' in page)
ck("the selection is drawn, not just stored", ".edrow.picked" in page and "edPaintPicked" in page)
ck("the counter is outside the pane that a pick rebuilds", 'id="ed-pickbar"' in page and
   '.edpickbar' in page)
ck("there is a bulk box and a button", 'n.id = "ed-bulk-n"' in page and
   'bulk.id = "ed-bulk-add"' in page)
ck("bulk add posts a count", 'count: n' in page, "count: n")
ck("paste posts donors", "donors: ids" in page, "donors: ids")
ck("both orderings have a chip", 'id="ed-order-id"' in page and 'id="ed-order-new"' in page)
server = src(SERVER)
ck("the route forwards donors", 'donors=payload.get("donors")' in server)
ck("the route forwards count", 'count=payload.get("count")' in server)
ck("the route forwards ids", 'ids=payload.get("ids")' in server)

print("=== 9. a step that takes records away takes its rows away ===")
# The add path patches the list in place, so the undo path owes it the other half.
ck("the server names the rows a step created", 'out["undone"] = self._step_notes(step)' in server)
ck("and the rows a redo brought back", 'out["redone"] = self._step_notes(step)' in server)
ck("a step's notes are handed out one copy each", "def _step_notes(writes):" in server)
ck("the page acts on them when a step lands", "await edStepRows(r);" in page)
ck("undo filters the rows out of the model list",
   'EDROWS = (EDROWS || []).filter((row) => !gone.has(String(row.id)));' in page)
ck("undo also takes the nodes out of the DOM", "if (gone.has(row.dataset.id)) row.remove();" in page)
ck("redo puts them back through the same inserter",
   "await edInsertRows(Array.from(gone));" in page)
ck("the inserter is one function, not two copies", "async function edInsertRows(ids) {" in page)
ck("an add still goes through it", "await edInsertRows(made);" in page)
ck("the counter is re-read rather than guessed",
   'api("/api/browse?kind=" + EDKIND + "&limit=1&offset=0&order=id&q=")' in page)
ck("the pager is redrawn when rows leave", page.count("drawPager(box);") >= 2)

print()
if FAILED:
    print("EDITOR BULK: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
    sys.exit(1)
print("EDITOR BULK: A THOUSAND RECORDS ARE ONE GESTURE AND ONE UNDO, "
      "AND EVERY KEY A SELECTION NEEDS IS BOUND")
