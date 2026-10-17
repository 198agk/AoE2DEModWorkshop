# -*- coding: utf-8 -*-
"""The verdict on the four tech-side families: what each one IS, and whether a
shipped intent could already express it.

Established so far (probe_tech_side_shapes.py):
  * 101 Tech Cost Modifier   175 rows, 172 target a DIFFERENT tech
  * 103 Tech Time Modifier    71 rows,  68 target a DIFFERENT tech
  * 102 Disable Tech         269 rows, target = slot D as a float
  * 8   Modify Tech           52 rows, slot D is a string-id-sized value

`tech.cost` / `tech.research_time` write the TARGET's own GLOBAL record.  So a
row that targets a different tech, conditionally on the CARRIER being
researched, is not the same observable -- unless the carrier is global, in which
case it is a global edit spelled indirectly.

This file answers the three questions that decide whether to wire anything:
  Q1  how many rows are GLOBAL-carried (i.e. what `tech.cost` could arguably
      already say for everyone)?
  Q2  for type 102, does the receiver's TREE already agree with the command
      (making the tree the place to say it, as with type 2)?
  Q3  how many rows use an operation/resource code whose meaning is NOT
      established, and therefore must stay refused?

Writes nothing.  Exit code 0.
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

    def tname(ti):
        e = sem.techs.get(ti) if isinstance(ti, int) else None
        return (e.en if e else "?") if e else "?"

    idx2stem = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            idx2stem[c["index"]] = stem

    fam = collections.defaultdict(list)
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] in (101, 102, 103, 8):
                fam[r["type"]].append((ti, t.get("civ"), r["raw"]))

    print("#" * 74)
    print("Q1  is the modifier GLOBAL (everyone pays it) or PER-CIV?")
    print("#" * 74)
    for ty in (101, 103, 8):
        rs = fam[ty]
        glob = [x for x in rs if x[1] is None or x[1] < 0]
        civs = collections.Counter(idx2stem.get(x[1], "<civ %s>" % x[1]) for x in rs if x[1] is not None and x[1] >= 0)
        print("type %-4d rows %-4d  global-carried %-4d  civ-carried %-4d"
              % (ty, len(rs), len(glob), len(rs) - len(glob)))
        print("          carriers by civ: %s" % civs.most_common(12))
    print()
    print("  -> a GLOBAL carrier applies the modifier for every civilization, so")
    print("     for those rows the observable is a plain global edit of that")
    print("     tech's cost/time -- which tech.cost / tech.research_time write")
    print("     directly.  The per-civ rows are the ones no shipped intent can")
    print("     express.")
    print()

    print("#" * 74)
    print("Q2  type 102: does the receiver's TREE already say the same thing?")
    print("#" * 74)
    rs = fam[102]
    agree = collections.Counter()
    detail = collections.defaultdict(list)
    for ti, o, rw in rs:
        d = int(rw[4])
        if o is None or o < 0:
            agree["carrier is global"] += 1
            continue
        stem = idx2stem.get(o)
        if stem is None:
            agree["owner has no tree file"] += 1
            continue
        st = CT.node_status(trees[stem], d, CT.TECH_USE_TYPES)
        agree[st] += 1
        detail[st].append((stem, ti, tname(ti), d, tname(d)))
    for k, n in agree.most_common():
        print("  target's tree row reads %-22s : %d" % (k, n))
    print()
    print("  the %d rows where the tree ALREADY reads ResearchedCompleted"
          % len(detail["ResearchedCompleted"]))
    print("  (the civ is shown as able, and this command takes it away):")
    for s in detail["ResearchedCompleted"][:18]:
        print("    %-14s carrier %-5s %-24s disables %-5s %s" % s)
    print()
    print("  the %d rows where the tree has NO row (the civ is already unable,"
          % len(detail[None]))
    print("  so the command and the tree agree):")
    for s in detail[None][:10]:
        print("    %-14s carrier %-5s %-24s disables %-5s %s" % s)
    print()

    print("#" * 74)
    print("Q3  operation / resource codes with NO established meaning")
    print("#" * 74)
    KNOWN_RESOURCE = {0, 1, 2, 3}          # food, wood, stone, gold
    for ty, label in ((101, "cost"), (103, "time")):
        rs = fam[ty]
        unknown_b = [x for x in rs if x[2][2] not in KNOWN_RESOURCE and x[2][2] != -1]
        b_neg = [x for x in rs if x[2][2] == -1]
        c_known = [x for x in rs if x[2][3] in (0, 2)]
        c_unknown = [x for x in rs if x[2][3] not in (0, 2)]
        print("type %d (%s): B not a known resource and not -1: %d  (B == -1: %d)"
              % (ty, label, len(unknown_b), len(b_neg)))
        print("           C in {0, 2}: %d   C not in {0, 2}: %d  -> %s"
              % (len(c_known), len(c_unknown),
                 sorted({x[2][3] for x in c_unknown})))
        if unknown_b:
            print("           unknown-B rows: %s"
                  % [(ti, x[2]) for ti, _o, x in unknown_b][:5])
    print()
    rs = fam[8]
    print("type 8 (modify tech): B values %s" % sorted({x[2][2] for x in rs}))
    print("                      C values %s" % sorted({x[2][3] for x in rs}))
    print("                      D values (string-id shaped) %s"
          % sorted({int(x[2][4]) for x in rs})[:12])
    print()
    print("#" * 74)
    print("VERDICT")
    print("#" * 74)
    print("1. 101/103 are CONDITIONAL PER-CIV modifiers of ANOTHER tech.  A")
    print("   shipped intent cannot express them: tech.cost / tech.research_time")
    print("   write the target's own record, globally, with no carrier.")
    print("2. Their global-carried rows ARE reachable today, indirectly, and")
    print("   only if the modifier is arithmetic the user can predict.")
    print("3. 102 is NOT an alias of a tree row.  This file's Q2 was written")
    print("   before the table existed and guessed 'the tree already says it';")
    print("   the table says the opposite on 64 of 81 civ-carried rows (the tree")
    print("   OFFERS the tech and the command REMOVES it -- the civ's")
    print("   choose-one-of-two unique techs).  See")
    print("   _probe/probe_type102_structure.py, which measures that properly.")
    print("   It stays refused for a different reason: the engine's precedence")
    print("   between 'listed as available' and 'removed once a sibling is")
    print("   researched' is not observable without running the game.")
    print("4. 8 Modify Tech writes a STRING-ID-shaped value; that is display")
    print("   text, not a number, so it is not the same class of edit at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
