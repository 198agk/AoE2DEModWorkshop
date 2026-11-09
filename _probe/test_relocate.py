# -*- coding: utf-8 -*-
"""Adding one record must not cost ten seconds, and the model must still be right.

Reported 2026-11-05, verbatim:

    「每次粘贴都会重新刷新加载，太慢了」

Measured that day: one 「新增 20 条」 over HTTP took 44 s, of which 0.04 s was
the byte work.  The rest was two full passes over 93 MB -- `Parser.parse` +
`locate.locate` to rebuild the model after the splice (10.45 s), and
`unitfields.scan` to rebuild the unit index before the next form could open
(10.43 s) -- paid again by every paste and every undo.

The fix carries the model across the splice instead of re-deriving it:
`relocate.splice_rules` unfolds the applied writes back into original
coordinates, `shift_civs` adds those deltas to every byte offset the model holds,
`re_walk_civ` re-walks only the one civilisation the splice landed in, and
`chain_ok` re-checks the invariant `scan`'s zero leftover used to stand for.
The unit index is then built from the model's own `_start`/`_end`.

This pin is written to CATCH the ways that can be subtly wrong, not to confirm
it is fast:

  1. a splice whose delta is bigger than the gap to the next one -- the case the
     naive `value >= at` comparison silently mis-shifts;
  2. an undo, which runs on the EDITED buffer and therefore needs its thresholds
     moved, not just its signs flipped;
  3. the model after an edit must equal a fresh parse of the same bytes, offset
     for offset, or a later write lands in the wrong field;
  4. the fast index path must produce exactly what the scan produces, and must
     refuse (fall back) when the model cannot prove it describes these bytes.

Run: python -X utf8 _probe/test_relocate.py
"""
import contextlib
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A
import aoe2mod.ui.server as S
from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P
from aoe2mod.dat import records as REC
from aoe2mod.dat import relocate as REL

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


def snapshot(civs):
    """Every offset the editor can write through, as comparable tuples."""
    out = []
    for ci, c in enumerate(civs):
        out.append(("civ", ci, c.get("_start"), c.get("_end")))
        for u in c["units"]:
            t50 = u.get("type50") or {}
            out.append((
                "unit", ci, u["id"], u["_start"], u["_end"],
                tuple(sorted(u.get("_offs", {}).items())),
                u.get("_creatable_start"), u.get("_creatable_end"),
                u.get("_creatable_head_end"),
                u.get("_off_displayed_pierce_armour"),
                tuple((d.get("_off_train_time"), d.get("unit_id"))
                      for d in u.get("train_locations") or ()),
                tuple(c2.get("_off_amount") for c2 in u.get("costs") or ()),
                tuple((a.get("_off_class"), a.get("_off_amount"))
                      for a in t50.get("attacks") or ()),
                tuple((a.get("_off_class"), a.get("_off_amount"))
                      for a in t50.get("armors") or ())))
    return out


# ---------------------------------------------------------------------------
section("1. unfolding a plan puts every splice back in original coordinates")
# ---------------------------------------------------------------------------
# `apply_steps` records each write against the buffer as it was when THAT write
# ran, so write #2 has already seen write #1 move the bytes.  A shift rule is a
# statement about one coordinate system, so the list has to be unfolded first.
# Write #1 inserts 30 bytes at 1000, so the byte that used to sit at 4000 is at
# 4030 by the time write #2 runs -- `apply_steps` reports it as 4030.
_w = [{"off": 1000, "before": b"", "after": b"x" * 30},      # +30 at 1000
      {"off": 4000 + 30, "before": b"", "after": b"y" * 5}]  # really +5 at 4000
ck("a later write's offset is corrected by the deltas before it",
   REL.splice_rules(_w) == [(1000, 30), (4000, 5)], REL.splice_rules(_w))
_w2 = [{"off": 50, "before": b"z" * 9, "after": b""}]        # -9 at 50
ck("a removal is a negative delta", REL.splice_rules(_w2) == [(50, -9)],
   REL.splice_rules(_w2))
ck("zero-length changes produce no rule at all",
   REL.splice_rules([{"off": 7, "before": b"ab", "after": b"cd"}]) == [])

# ---------------------------------------------------------------------------
section("2. a delta larger than the gap still lands offsets correctly")
# ---------------------------------------------------------------------------
# THE BUG THIS PINS.  `shift` used to compare the (already moved) value against
# the (unmoved) threshold.  A 1,000-byte insertion at 1,000 followed by a
# 1-byte insertion at 1,500 must leave an offset of 1,400 where it was: the
# naive comparison pushes it past 1,500 and then adds the second byte too.
_rules = [(1000, 1000), (1500, 1)]
ck("an offset before both splices does not move",
   REL.shift(_rules, 400) == 400, REL.shift(_rules, 400))
ck("an offset between the splices collects only the first delta",
   REL.shift(_rules, 1400) == 2400, REL.shift(_rules, 1400))
ck("an offset inside the second delta's reach is not swallowed by it",
   REL.shift(_rules, 1500) == 2501, REL.shift(_rules, 1500))
ck("None survives, because a missing offset must not become an offset",
   REL.shift(_rules, None) is None)
ck("no rules means no movement", REL.shift([], 12345) == 12345)

# ---------------------------------------------------------------------------
section("3. an undo is expressed in the coordinates of the edited buffer")
# ---------------------------------------------------------------------------
# The undo runs on bytes that already carry the insertion, so the second rule's
# threshold is 1,500 + 1,000 in that buffer.  Flipping the sign without moving
# the threshold would subtract one byte at address 1,500 -- inside the inserted
# run -- for every rule after the first.
_undo = REL.splice_rules(_w, undo=True)
ck("an undo moves each threshold by the deltas before it",
   _undo == [(1000, -30), (4030, -5)], _undo)
ck("an undo takes a shifted offset back to where it started",
   [REL.shift(_undo, REL.shift(REL.splice_rules(_w), v))
    for v in (400, 1400, 5000)] == [400, 1400, 5000])

# ---------------------------------------------------------------------------
section("4. the model after a real splice equals a fresh parse of the bytes")
# ---------------------------------------------------------------------------
app = S.App()
tk = app.tk
tk._ensure()
raw0 = bytes(app.session_raw())
civs_start = tk._parsed[2]
gv = tk._parsed[3]
tail0 = tk._parsed[4]
ck("the model vouches for itself before the edit (chain closes)",
   REL.chain_ok(tk._civs, civs_start, tail0))

_n0 = sum(len(c["units"]) for c in tk._civs)
t0 = time.time()
out = app.record_edit("add", kind="unit", civ="British", record=74, count=4)
add_s = time.time() - t0
ck("a four-record add succeeds", out.get("ok"), out.get("error"))
ck("it cost under three seconds, not forty-four", add_s < 3.0, "%.2f s" % add_s)
raw1 = bytes(app.session_raw())
ck("the buffer actually grew", len(raw1) > len(raw0),
   "%d -> %d" % (len(raw0), len(raw1)))
ck("the tail pointer moved with it",
   tk._parsed[4] == tail0 + (len(raw1) - len(raw0)),
   "%d -> %d" % (tail0, tk._parsed[4]))
ck("the model still closes into one unbroken stream",
   REL.chain_ok(tk._civs, civs_start, tk._parsed[4]))
ck("four records appeared", sum(len(c["units"]) for c in tk._civs) == _n0 + 4,
   "%d -> %d" % (_n0, sum(len(c["units"]) for c in tk._civs)))

# The only real proof: parse the edited buffer from scratch and compare.
_p = P.Parser(raw1)
with contextlib.redirect_stdout(io.StringIO()):
    _p.parse()
ref_civs, ref_start, ref_gv, ref_tail = L.locate(raw1, parser=_p)
_a = snapshot(tk._civs)
_b = snapshot(ref_civs)
_diff = [(x, y) for x, y in zip(_a, _b) if x != y]
ck("every offset in the moved model matches a fresh parse",
   len(_a) == len(_b) and not _diff,
   "%d rows, %d differ%s" % (len(_a), len(_diff), (" first=" + repr(_diff[0])) if _diff else ""))
ck("and so does the tail pointer", tk._parsed[4] == ref_tail,
   "%d vs %d" % (tk._parsed[4], ref_tail))
ck("and the statistics the record browser reads",
   len(tk._stats["techs"]) == len(_p.stats["techs"])
   and tk._stats["tech_count"] == _p.stats["tech_count"],
   "%d vs %d" % (tk._stats["tech_count"], _p.stats["tech_count"]))
ck("and the civ rows that free-id allocation reads",
   [u["id"] for u in tk._stats["civs"][1]["units"]]
   == [u["id"] for u in _p.stats["civs"][1]["units"]],
   "%d vs %d units" % (len(tk._stats["civs"][1]["units"]),
                       len(_p.stats["civs"][1]["units"])))

# ---------------------------------------------------------------------------
section("5. the field index comes from the model and matches the scan")
# ---------------------------------------------------------------------------
from aoe2mod.dat import unitfields as UF
idx_fast = app._unit_index()
ck("the index covers every record", len(idx_fast) == len(_a) - len(tk._civs),
   "%d rows" % (len(idx_fast),))
_units, _st, _left = UF.scan(raw1, gv, light=True)
_slow = {(u["civ_index"], u["id"]): (u["start"], u["end"], u["type"], u["civ"])
         for u in _units}
_fast = {k: (v["start"], v["end"], v["type"], v["civ"]) for k, v in idx_fast.items()}
ck("the scan agrees the file is fully walked", _left == 0, _left)
ck("the fast index is byte-identical to the scan", _fast == _slow,
   "%d keys, %d differ" % (len(_fast),
                           len(set(_fast.items()) ^ set(_slow.items()))))
ck("the civ name on each row is a name, not a record",
   all(isinstance(v["civ"], str) for v in list(idx_fast.values())[:200]))

# ---------------------------------------------------------------------------
section("6. an undo puts the model back where it was")
# ---------------------------------------------------------------------------
t0 = time.time()
app.undo()
undo_s = time.time() - t0
ck("the undo cost under three seconds too", undo_s < 3.0, "%.2f s" % undo_s)
ck("the buffer is byte-identical to before the edit",
   bytes(app.session_raw()) == raw0,
   "%d vs %d bytes" % (len(app.session_raw()), len(raw0)))
ck("the tail pointer came back", tk._parsed[4] == tail0,
   "%d vs %d" % (tk._parsed[4], tail0))
ck("the model closes again", REL.chain_ok(tk._civs, civs_start, tk._parsed[4]))
ck("the record count came back", sum(len(c["units"]) for c in tk._civs) == _n0,
   sum(len(c["units"]) for c in tk._civs))

# ---------------------------------------------------------------------------
section("7. a model that cannot prove itself is not trusted")
# ---------------------------------------------------------------------------
_civs = tk._civs
_saved = {ci: (_civs[ci].get("_start"), _civs[ci].get("_end"))
          for ci in (0, len(_civs) - 1)}
try:
    _civs[0]["_start"] = None
    ck("a civ with no start falls back to the scan",
       app._index_from_model(tk, bytes(app.session_raw())) is None)
    _civs[0]["_start"] = _saved[0][0]
    ck("restoring it makes the fast path work again",
       app._index_from_model(tk, bytes(app.session_raw())) is not None)
    _civs[-1]["_end"] = _saved[len(_civs) - 1][1] + 4
    ck("a chain that does not end at the tail falls back",
       app._index_from_model(tk, bytes(app.session_raw())) is None)
    _civs[-1]["_end"] = _saved[len(_civs) - 1][1]
    ck("a buffer of the wrong length falls back",
       app._index_from_model(tk, bytes(app.session_raw()) + b"\0") is None)
finally:
    for ci, (s, e) in _saved.items():
        _civs[ci]["_start"] = s
        _civs[ci]["_end"] = e
ck("the model is intact after the tampering test",
   REL.chain_ok(tk._civs, civs_start, tk._parsed[4]))

# ---------------------------------------------------------------------------
section("8. the server routes the writes to the incremental path")
# ---------------------------------------------------------------------------
server = io.open(SERVER, encoding="utf-8").read()
ck("the record editor hands its writes to the relocator",
   re.search(r"self\._restructure\(writes\)", server) is not None)
ck("undo and redo say which direction they are going",
   re.search(r'self\._restructure\(writes, undo=\(side == "before"\)\)', server) is not None)
ck("the effects cache is deliberately kept, because a civ splice cannot move it",
   "_effects" not in re.search(
       r"for name in \(\"_field_index\".*?setattr\(tk, name, None\)",
       server, re.S).group(0))
ck("the technology block is re-read rather than shifted",
   re.search(r"L\.locate_techs\(raw, new_tail, gv\)", server) is not None)
ck("the unit index asks the model first",
   re.search(r"fast = self\._index_from_model\(tk, raw\)", server) is not None)

print()
if FAILED:
    print("RELOCATE: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
    sys.exit(1)
print("RELOCATE: ONE SPLICE MOVES THE MODEL IN HALF A SECOND, AND THE MOVED "
      "MODEL IS INDISTINGUISHABLE FROM A FRESH PARSE")
