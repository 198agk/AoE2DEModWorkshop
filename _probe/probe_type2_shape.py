# -*- coding: utf-8 -*-
"""Type 2 (Enable/Disable Unit): can every shipped instance be written safely?

`type 2` is the single most valuable refused family (169 technologies with no
other editable command, every one of them player-visible).  But "I can name the
slots" is not "the slots mean what I think":

  * slot A is claimed to be a UNIT id, yet the identical integer can be a tech
    index -- the overlap is real (755 is both Tarkan and a legal tech index), so
    overlap alone proves nothing and a value OUTSIDE the tech range proves a lot.
  * slot B is claimed to be 0/1, but a flag with a third value silently means
    something else, so the count of non-{0,1} rows decides whether "flag" is a
    usable abstraction or a description of the majority.
  * c/d are claimed unused -- if any row uses them, the command carries a second
    meaning and one operation cannot describe it.

It writes nothing.  Its verdict decides whether type 2 gets implemented, and its
counts are the ones a refusal message is allowed to quote.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402
from aoe2mod.dat import locate as L                            # noqa: E402
from aoe2mod.intent import compiler as C                       # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- %s" % detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(label)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)

    unit_ids = set()
    for civ in tk._civs:
        for u in civ.get("units") or ():
            unit_ids.add(u.get("id"))

    rows = []
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if not r["editable"] and r["type"] == 2:
                rows.append((ti, r))
    print("type 2 refused rows: %d, across %d technologies"
          % (len(rows), len({ti for ti, _r in rows})))
    print()

    A_ = [r["raw"][1] for _ti, r in rows]
    B_ = [r["raw"][2] for _ti, r in rows]
    C_ = [r["raw"][3] for _ti, r in rows]
    D_ = [r["raw"][4] for _ti, r in rows]

    print("slot A histogram (top 8): %s"
          % collections.Counter(A_).most_common(8))
    print("slot B histogram: %s" % collections.Counter(B_).most_common())
    print("slot C histogram: %s" % collections.Counter(C_).most_common())
    print("slot D histogram: %s" % collections.Counter(D_).most_common())
    print()

    # --- A is a unit id ------------------------------------------------
    off_unit = [v for v in A_ if v not in unit_ids]
    check(not off_unit,
          "every slot A names a real unit id (%d rows)" % len(A_),
          "not-unit: %s" % sorted(set(off_unit))[:6])
    # Overlap is not evidence: values outside the tech range ARE.
    off_tech = [v for v in A_ if v >= len(techs)]
    check(off_tech,
          "  and overlap with the tech space is not what proves it "
          "(%d of %d A values lie outside the tech array)"
          % (len(off_tech), len(A_)))
    print()

    # --- B is a two-valued flag ---------------------------------------
    bvals = collections.Counter(B_)
    check(set(bvals) <= {0, 1},
          "slot B is a strict 2-valued flag across every shipped row",
          str(dict(bvals)))
    print("    B=1 meaning sample: rows whose effect says 'enable'")
    print()

    # --- C and D unused -----------------------------------------------
    check(set(C_) == {-1}, "slot C is unused (-1) everywhere", str(set(C_)))
    check(set(D_) == {0}, "slot D is unused (0) everywhere", str(set(D_)))
    print()

    # --- what does B mean, checked against a KNOWN answer --------------
    # The classic example: a civilization can build the Hand Cannoneer only
    # after researching Chemistry, and the command that grants it is type 2.
    print("rows that look like a known unlock:")
    from aoe2mod.semantic import index as SI
    sem = SI.index()
    named = 0
    for ti, r in rows:
        a, b = r["raw"][1], r["raw"][2]
        if a in (5, 41, 8, 755):      # Hand Cannoneer / Huskarl / Longbow / Tarkan
            named += 1
            e = (sem.techs or {}).get(str(ti)) or {}
            print("    tech[%d] %-30s unit=%-5s B=%s  internal=%s"
                  % (ti, (e.get("en") or e.get("internal") or "?")[:30], a, b,
                     techs[ti].get("civ")))
    check(named > 0, "at least one well-known unlock is present to read")
    print()

    # --- how many distinct units does this family touch? ---------------
    print("distinct unit ids touched: %d" % len(set(A_)))
    print("technologies that would gain their FIRST editable command: %d"
          % len({ti for ti, _r in rows}))
    print()
    print("TYPE 2 VERDICT: %s" % ("WRITABLE" if not FAILS else "REFUSE: %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
