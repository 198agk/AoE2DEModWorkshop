# -*- coding: utf-8 -*-
"""Follow-up: fix two probe bugs and answer whether 101/103/102/8 add a
capability the shipped intents cannot express.

Bugs in probe_tech_side_families.py:
  1. type 102's target is slot D as a FLOAT (79.0), not an int -> the
     `isinstance(d, int)` guard rejected every row, so "target not
     identifiable: 269" was a probe artifact, not a fact.
  2. research time is NOT `tech["research_time"]` on VER 8.9 -- it lives in the
     `research_locations` array (GV_C31+).  Reading the scalar printed None for
     every row.

The decisive question this file answers: a 101/103 row changes the cost/time of
a DIFFERENT tech, conditionally on the carrier being researched.  `tech.cost` /
`tech.research_time` write the target's own GLOBAL record.  So is the family a
per-civ modifier (new capability) or a second spelling of a global number?

Writes nothing.
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
from aoe2mod.game import civtechtrees as CT                    # noqa: E402
from aoe2mod.intent import compiler as C                       # noqa: E402
from aoe2mod.semantic import index as SI                       # noqa: E402


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    trees = CT.load_trees(tk.game_root)
    sem = SI.index()

    print("tech record keys (first record):")
    print("  %s" % sorted(techs[0].keys()))
    print()

    def tname(ti):
        e = sem.techs.get(ti)
        return e.en if e else "?"

    stem2idx = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            stem2idx[stem] = c["index"]
    idx2stem = {v: k for k, v in stem2idx.items()}

    fam = collections.defaultdict(list)
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] in (101, 102, 103, 8):
                fam[r["type"]].append((ti, t.get("civ"), r["raw"]))

    # ---------------------------------------------------------------- 102
    print("=" * 74)
    print("type 102 Disable Tech -- target is slot D (float)")
    print("=" * 74)
    rs = fam[102]
    ok = [(ti, o, rw) for ti, o, rw in rs
          if isinstance(rw[4], float) and 0 <= int(rw[4]) < len(techs)]
    print("  rows %d, targets that are a real tech id: %d, unresolvable: %d"
          % (len(rs), len(ok), len(rs) - len(ok)))
    tab = collections.Counter()
    samples = []
    for ti, o, rw in ok:
        d = int(rw[4])
        if o is None or o < 0:
            tab["carrier is global (no single owner)"] += 1
            continue
        stem = idx2stem.get(o)
        if stem is None:
            tab["owner has no tree file"] += 1
            continue
        st = CT.node_status(trees[stem], d, CT.TECH_USE_TYPES)
        tab["tree already reads %s" % st] += 1
        if len(samples) < 10:
            samples.append((stem, ti, tname(ti), d, tname(d), st))
    for k, n in tab.most_common():
        print("  %-42s : %d" % (k, n))
    print("  samples:")
    for s in samples:
        print("    %-14s car %-5s %-20s disables %-5s %-20s tree=%s" % s)
    print()

    # ------------------------------------------------------------ 101 / 103
    for ty, label, key in ((101, "cost", "costs"), (103, "research time", None)):
        rs = fam[ty]
        print("=" * 74)
        print("type %d Tech %s Modifier -- shape" % (ty, label))
        print("=" * 74)
        tgt = {}
        for ti, o, rw in rs:
            _t, a, b, c, d = rw
            tgt.setdefault(a, []).append((ti, o, b, c, d))
        print("  rows %d, distinct targets %d" % (len(rs), len(tgt)))
        print("  target == carrier: %d / different: %d"
              % (sum(1 for ti, _o, rw in rs if rw[1] == ti),
                 sum(1 for ti, _o, rw in rs if rw[1] != ti)))
        b_hist = collections.Counter(rw[2] for _ti, _o, rw in rs)
        c_hist = collections.Counter(rw[3] for _ti, _o, rw in rs)
        nz = sum(1 for _ti, _o, rw in rs if rw[4])
        print("  slot B (resource/field?): %s" % b_hist.most_common())
        print("  slot C (operation?):      %s" % c_hist.most_common())
        print("  rows whose slot D is non-zero: %d of %d" % (nz, len(rs)))
        print("  carrier owners: civ-owned %d / global %d"
              % (sum(1 for _ti, o, _rw in rs if o is not None and o >= 0),
                 sum(1 for _ti, o, _rw in rs if o is None or o < 0)))
        print("  distinct carriers: %d" % len({ti for ti, _o, _rw in rs}))
        print("  sample targets with their CURRENT global stored value:")
        shown = 0
        for a, rows in sorted(tgt.items()):
            if key:
                stored = techs[a].get(key)
            else:
                locs = techs[a].get("research_locations")
                stored = [x.get("research_time") for x in locs] if locs else None
            print("    target %-5s %-24s stored=%-46s  modifiers=%s"
                  % (a, tname(a), str(stored)[:46],
                     [(b, c, d) for _ti, _o, b, c, d in rows][:4]))
            shown += 1
            if shown >= 8:
                break
        print()

    # ------------------------------------------------------------------ 8
    print("=" * 74)
    print("type 8 Modify Tech -- shape (slot D looks like a string id)")
    print("=" * 74)
    rs = fam[8]
    print("  rows %d, distinct targets %d, distinct carriers %d"
          % (len(rs), len({rw[1] for _ti, _o, rw in rs}),
             len({ti for ti, _o, _rw in rs})))
    print("  slot B: %s" % collections.Counter(rw[2] for _ti, _o, rw in rs).most_common())
    print("  slot C: %s" % collections.Counter(rw[3] for _ti, _o, rw in rs).most_common())
    dvals = [rw[4] for _ti, _o, rw in rs]
    print("  slot D range: %s .. %s  (%d distinct)"
          % (min(dvals), max(dvals), len(set(dvals))))
    for ti, o, rw in rs[:6]:
        print("    carrier %-5s %-22s owner=%-5s raw=%s -> target %s (%s)"
              % (ti, tname(ti), o, rw, rw[1], tname(rw[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
