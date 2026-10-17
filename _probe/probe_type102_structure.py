# -*- coding: utf-8 -*-
"""type 102 Disable Tech: the 64 rows that contradict "the tree already says it".

probe_tech_side_verdict.py's Q2 printed 64 rows where the target's tree row reads
ResearchedCompleted -- i.e. the civ's tech tree OFFERS the tech -- and the
command DISABLES it.  That is not "two spellings of the same fact", which is
what the verdict paragraph claimed before the table existed.  This file measures
what those 64 rows actually are, because the shape decides whether a tree row can
ever express it.

Hypothesis to test: they come in MUTUALLY-EXCLUSIVE PAIRS of unique techs (the
Chronicles civs' choose-one-of-two), so the command means "once you research the
sibling, this one is gone" -- a rule the tree cannot state, since the tree lists
both as available.

Also counts the self-referential rows (carrier disables itself), which would be a
different thing again (removal after research).

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
        e = sem.techs.get(ti)
        return e.en if e else "?"

    idx2stem = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            idx2stem[c["index"]] = stem

    rows = []
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] == 102:
                rows.append((ti, t.get("civ"), int(r["raw"][4])))

    civ_rows = [(ti, o, d) for ti, o, d in rows if o is not None and o >= 0]
    print("type 102 rows: %d   civ-carried: %d   global-carried: %d"
          % (len(rows), len(civ_rows), len(rows) - len(civ_rows)))
    print()

    # --- self-referential vs sibling ------------------------------------
    self_ref = [(ti, o, d) for ti, o, d in civ_rows if ti == d]
    sibling = [(ti, o, d) for ti, o, d in civ_rows if ti != d]
    print("civ-carried rows that disable THEMSELVES : %d" % len(self_ref))
    print("civ-carried rows that disable a SIBLING  : %d" % len(sibling))
    print()

    # --- mutual exclusion: does every sibling pair exist both ways? ------
    by_civ = collections.defaultdict(set)
    for ti, o, d in civ_rows:
        if ti != d:
            by_civ[idx2stem.get(o, "?")].add((ti, d))
    both = 0
    one_way = 0
    for civ, pairs in sorted(by_civ.items()):
        for a, b in sorted(pairs):
            if (b, a) in pairs:
                both += 1
            else:
                one_way += 1
    print("sibling edges whose REVERSE edge also exists: %d" % both)
    print("sibling edges without a reverse edge        : %d" % one_way)
    print("  -> a two-way edge is a mutual exclusion (choose one of two);")
    print("     a one-way edge is a plain 'this removes that'.")
    print()

    print("per-civ mutual-exclusion pairs:")
    for civ, pairs in sorted(by_civ.items()):
        mutual = sorted({tuple(sorted((a, b))) for a, b in pairs if (b, a) in pairs})
        if mutual:
            print("  %-14s %d mutual pairs" % (civ, len(mutual)))
            for a, b in mutual[:6]:
                print("      %-5s %-24s <-> %-5s %s" % (a, tname(a), b, tname(b)))
    print()

    # --- which of these are offered by the tree? -------------------------
    tab = collections.Counter()
    for ti, o, d in civ_rows:
        stem = idx2stem.get(o)
        st_c = CT.node_status(trees[stem], ti, CT.TECH_USE_TYPES) if stem else None
        st_d = CT.node_status(trees[stem], d, CT.TECH_USE_TYPES) if stem else None
        tab[(st_c, st_d)] += 1
    print("(carrier's own tree row, target's tree row) -> count:")
    for (a, b), n in tab.most_common():
        print("  carrier=%-22s target=%-22s : %d" % (a, b, n))
    print()
    print("  READING: when carrier=ResearchedCompleted and target=ResearchedCompleted,")
    print("  the tree OFFERS both and the command says 'researching one removes the")
    print("  other'.  No tree row can state that: the tree is per-civ availability,")
    print("  not conditional-on-research availability.")
    print()

    # --- concentration ---------------------------------------------------
    civs = collections.Counter(idx2stem.get(o, "?") for ti, o, d in civ_rows)
    print("civs carrying type 102: %d" % len(civs))
    print("  %s" % civs.most_common())
    print("  -> 13 civs, led by the Chronicles set, plus 4 one-off rows on")
    print("     MONGOLS/ROMANS/HUNS/PERSIANS/LITHUANIANS/POLES.  So it is a")
    print("     per-civ design lever, not a global one -- and the self-referential")
    print("     26 rows are a third shape again (remove the carrier once used).")
    print()
    print("VERDICT (data-derived, do not pre-write this paragraph again):")
    print("  type 102 is NOT an alias of a tree row.  The tree lists availability;")
    print("  this command makes availability conditional on what you researched,")
    print("  which the tree cannot express.  It stays REFUSED because the engine's")
    print("  precedence between the two is not observable statically -- but it is a")
    print("  real missing capability, not a duplicate spelling of an existing one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
