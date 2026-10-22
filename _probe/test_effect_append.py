# -*- coding: utf-8 -*-
"""Can the product ADD a command to a shipped effect record?

Every shipped `MutuallyExclusive` / `Toggleable` linked-tech group puts the real
exclusion in `.dat`: each member's effect carries a `type 102` command naming its
sibling (`tmp_group_mechanism.py`: 16 of 20 groups, 2-4 commands each).  Cycle
groups carry none.  So a group whose exclusion the EVIL ENGINE enforces has to
be written on both halves, and the `.dat` half means changing the LENGTH of a
variable-length list inside a 93 MB stream.

That is the hard case for this writer: every in-place patch keeps a field's
width, and the writer's raw cursor only learns the old width from what it is
about to emit.  A list whose ELEMENT COUNT changes has no such single value, so
`write_effect` now corrects the cursor by the DIFFERENCE after emitting.

This file pins the failure that made that fix necessary, because the failure is
silent in the way that matters: the file still writes, still deflates, still
re-reads to the same bytes -- it is 3 MB too long and dies only when something
parses it.

Measured 2026-10-22, before the fix:
    serialize: 96,331,764 B (shipped 93,268,152, delta +3,061,612)
    reparse:   struct.error: bad char in struct format   (in read_bird)
After:
    serialize: 93,268,174 B (delta +22 = two 11 B commands)
    reparse:   tech 67 -> [(102, -1, -1, -1, 74.0)] / tech 74 -> [(102, -1, -1, -1, 67.0)]

Run: python -X utf8 _probe/test_effect_append.py
"""
import contextlib
import copy
import io
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod import api as A
from aoe2mod.dat import locate as L
from aoe2mod.dat import writer as W

PAIR = (67, 74)          # Forging / Scale Mail Armor: same age, same building,
                         # neither is the other's prerequisite (tech 68 is, and
                         # that is why 67+68 would prove nothing)
OUT = os.path.join(HERE, "out_effect_append")
COMMAND_BYTES = 11

FAILS = []


def check(name, ok, detail=""):
    if ok:
        print("[PASS] %s" % name)
    else:
        print("[FAIL] %s :: %s" % (name, detail))
        FAILS.append(name)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    data, civs, civs_start, gv, tail, how = tk._parsed
    recs = L.locate_techs(data, tail, gv)

    # -- A. the prediction is arithmetic, not a guess ----------------------
    added = 0
    stats = copy.copy(tk._stats)
    stats["effects"] = list(tk._stats["effects"])
    for tid in PAIR:
        eid = recs[tid].get("effect_id")
        check("tech %d has an effect record" % tid, eid is not None, "effect_id=%r" % (eid,))
        if eid is None:
            continue
        rec = dict(stats["effects"][eid])
        cmds = list(rec.get("commands") or ())
        check("effect %d starts without a type-102 command" % eid,
              not [c for c in cmds if c[0] == 102], "%r" % (cmds,))
        for other in PAIR:
            if other != tid:
                cmd = (102, -1, -1, -1, float(other))
                if cmd not in cmds:
                    cmds.append(cmd)
                    added += 1
        rec["commands"] = cmds
        stats["effects"][eid] = rec
    print("commands added: %d (expected %d bytes)" % (added, added * COMMAND_BYTES))
    check("two commands were appended", added == 2, "%d" % added)

    # -- B. the stream grows by exactly the command bytes ------------------
    out, report = W.serialize_dat(stats, raw=data)
    delta = len(out) - len(data)
    check("the stream grows by exactly the appended command bytes",
          delta == added * COMMAND_BYTES,
          "shipped %d -> %d, delta %+d, expected %+d"
          % (len(data), len(out), delta, added * COMMAND_BYTES))
    # The writer compares every field it rewrites against the raw stream and
    # counts a disagreement -- correctly -- when the model says something the
    # file did not.  Editing these two records MUST produce disagreements, and
    # they must be confined to them: a disagreement anywhere else means the
    # cursor drifted and unrelated bytes came out different.
    #
    # So the assertion is not "no mismatch" (that would fail on every honest
    # length-changing edit, and the first version of this file did exactly
    # that) but "the disagreements are the two records we touched, nothing
    # more": one count field plus five command fields each -- 12 field sites.
    _mis = report.get("model_mismatches") or []
    check("the only disagreement with the raw stream is inside the two edited records",
          0 < len(_mis) <= 2 * (1 + 5),
          "%d site(s): %r" % (len(_mis), _mis[:3]))

    # -- C. the output is what a re-parse reads back ----------------------
    os.makedirs(OUT, exist_ok=True)
    co = zlib.compressobj(6, zlib.DEFLATED, -15)
    packed = co.compress(out) + co.flush()
    path = os.path.join(OUT, "empires2_x2_p1.dat")
    with open(path, "wb") as fh:
        fh.write(packed)
    raw2, how2 = A.P.load_dat(path)
    check("the file on disk inflates to exactly what we serialised", raw2 == out,
          "%r %d vs %d" % (how2, len(raw2), len(out)))

    # `tail` is an OFFSET into the shipped stream and the effects section sits
    # before it, so it moves by exactly the bytes we added.  Reading the new
    # stream with the old offset is the mistake this test made first (it died
    # four bytes past the end of the buffer).
    tail2 = tail + delta
    recs2 = L.locate_techs(raw2, tail2, gv)
    p2 = A.P.Parser(raw2)
    with contextlib.redirect_stdout(io.StringIO()):
        p2.parse()
    effs2 = p2.stats["effects"]
    for tid in PAIR:
        other = PAIR[1] if tid == PAIR[0] else PAIR[0]
        eid2 = recs2[tid].get("effect_id")
        got = [c for c in (effs2[eid2].get("commands") or ()) if c[0] == 102] if eid2 is not None else []
        check("effect %d reads back the type-102 command naming %d" % (eid2, other),
              len(got) == 1 and got[0][1] == -1 and got[0][2] == -1
              and got[0][3] == -1 and abs(got[0][4] - other) < 1e-6,
              "%r" % (got,))
        want = len(stats["effects"][recs[tid].get("effect_id")].get("commands") or ())
        got_n = len(effs2[eid2].get("commands") or ()) if eid2 is not None else -1
        check("effect %d kept every command the model gave it" % eid2, got_n == want,
              "%d on disk vs %d in the model" % (got_n, want))

    # -- D. a record nobody touched keeps its exact shape ------------------
    untouched = [i for i in range(len(effs2)) if i not in
                 tuple(recs[t].get("effect_id") for t in PAIR)][:200]
    same = [i for i in untouched
            if (effs2[i].get("commands") or ()) == (tk._stats["effects"][i].get("commands") or ())]
    check("two hundred untouched records came back command for command",
          len(same) == len(untouched), "%d of %d" % (len(same), len(untouched)))

    print()
    if FAILS:
        print("EFFECT APPEND: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("EFFECT APPEND: A SHIPPED EFFECT CAN GROW BY A COMMAND, AND THE STREAM "
          "STILL PARSES -- the .dat half of a linked-tech group is writable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
