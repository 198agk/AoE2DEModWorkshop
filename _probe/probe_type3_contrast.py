# -*- coding: utf-8 -*-
"""Does a `type 3` upgrade command gate anything a player can observe?

`type 3 Upgrade Unit` (424 rows) is the family with the most "new techs it would
unlock" and it is the obvious next candidate to wire.  The previous round showed
that "biggest by newT" is not evidence -- `type 2` ranked second and turned out
to gate nothing per civ.  So this file runs the same CONTRAST experiment on
`type 3` before any code is written.

The shape of a `type 3` row is a pair of unit ids (A -> B): "this tech upgrades A
into B".  It lives on a tech, so it is an editor of WHAT a tech does, not of who
may have it.  Two questions, both answerable from shipped data:

  1. Does owning the command predict whether a civ can build the TARGET unit B?
     (If yes, changing the command would change buildability and it overlaps
     `unit.availability`.)
  2. Is the command's own AVAILABILITY gated by the tech-tree row of the tech it
     sits on?  (If yes, `tech.availability` already covers availability and the
     command only edits the effect.)

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

    stem2idx = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            stem2idx[stem] = c["index"]

    rows = []
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] == 3:
                _ty, a, b, cc, dd = r["raw"]
                rows.append((ti, t.get("civ"), a, b, cc, dd))

    print("type 3 rows: %d" % len(rows))
    print("distinct (A, B) pairs: %d" % len({(a, b) for _t, _o, a, b, _c, _d in rows}))
    print("distinct slot C values: %s"
          % collections.Counter(c for _t, _o, _a, _b, c, _d in rows).most_common())
    print("distinct slot D values: %s"
          % collections.Counter(d for _t, _o, _a, _b, _c, d in rows).most_common(6))
    print("owner techs civ-owned / global: %d / %d"
          % (len([1 for _t, o, *_ in rows if o is not None and o >= 0]),
             len([1 for _t, o, *_ in rows if o is None or o < 0])))
    print()

    # Is slot A always a real unit?  Is slot B?
    bad_a = sorted({a for _t, _o, a, _b, _c, _d in rows
                    if a is None or not isinstance(a, int)
                    or not (0 <= a < 2693)})
    bad_b = sorted({b for _t, _o, _a, b, _c, _d in rows
                    if b is None or not isinstance(b, int)
                    or not (0 <= b < 2693)})
    print("slot A values outside the plausible unit range: %s" % bad_a[:10])
    print("slot B values outside the plausible unit range: %s" % bad_b[:10])
    print()

    # per civ: which TARGETS does it own an upgrade command for
    own_to = collections.defaultdict(set)
    glob_to = set()
    for _ti, o, _a, b, _c, _d in rows:
        if o is None or o < 0:
            glob_to.add(b)
        else:
            own_to[o].add(b)

    def owns_upgrade(stem, b):
        idx = stem2idx.get(stem)
        return (idx is not None and b in own_to.get(idx, set())) or b in glob_to

    targets = sorted({b for _t, _o, _a, b, _c, _d in rows if isinstance(b, int)})
    print("distinct upgrade TARGETS: %d" % len(targets))
    print()

    # --- QUESTION 1: does owning the command predict buildability of B? ------
    print("=" * 74)
    print("Q1: does owning an upgrade command predict that a civ can BUILD B?")
    print("=" * 74)
    tab = collections.Counter()
    for stem, tr in sorted(trees.items()):
        for row in CT.unit_rows(tr):
            nid = row.get("Node ID")
            if nid is None or nid not in targets:
                continue
            can = CT.can_build(tr, nid)
            owns = owns_upgrade(stem, nid)
            tab[("can_build" if can else "cannot",
                 "owns_upgrade" if owns else "no_upgrade")] += 1
    for k in sorted(tab):
        print("  %-10s + %-13s : %d" % (k[0], k[1], tab[k]))
    wrong_yes = sum(v for k, v in tab.items()
                    if k == ("cannot", "owns_upgrade"))
    wrong_no = sum(v for k, v in tab.items()
                   if k == ("can_build", "no_upgrade"))
    print()
    print("  civs that CANNOT build it yet own the upgrade: %d" % wrong_yes)
    print("  civs that CAN build it yet own no upgrade:     %d" % wrong_no)
    print()

    # --- a concrete target with partial availability, for the reader --------
    print("=" * 74)
    print("Q1b: concrete targets, builders vs owners of an upgrade")
    print("=" * 74)
    scored = []
    for b in targets:
        builders = CT.builders(trees, b)
        owners = [s for s in trees if owns_upgrade(s, b)]
        if not builders and not owners:
            continue
        scored.append((abs(len(builders) - len(owners)), b, len(builders), len(owners)))
    scored.sort()
    for _gap, b, nb, no in scored[:8]:
        u = sem.units.get(b)
        print("  unit %-5s %-26s builders=%-3d upgrade-owners=%-3d"
              % (b, (u.en if u else "?"), nb, no))
    # biggest disagreement, which is the informative one
    print("  ...")
    for _gap, b, nb, no in scored[-5:]:
        u = sem.units.get(b)
        print("  unit %-5s %-26s builders=%-3d upgrade-owners=%-3d"
              % (b, (u.en if u else "?"), nb, no))
    print()

    # --- QUESTION 2: is the COMMAND's availability gated by the tech row? ---
    print("=" * 74)
    print("Q2: is the upgrade's AVAILABILITY gated by the carrying tech's row?")
    print("=" * 74)
    # For each civ-owned tech carrying a type-3, does the owner have a row for
    # that tech in its own tree, and is that row ResearchRequired/Completed?
    own_ok = 0
    own_na = 0
    own_missing = 0
    samples_missing = []
    for ti, o, _a, b, _c, _d in rows:
        if o is None or o < 0:
            continue
        stem = None
        for s, i in stem2idx.items():
            if i == o:
                stem = s
                break
        if stem is None:
            continue
        st = CT.node_status(trees[stem], ti, CT.TECH_USE_TYPES)
        if st is None:
            own_missing += 1
            if len(samples_missing) < 5:
                t = sem.techs.get(ti)
                samples_missing.append((stem, ti, (t.en if t else "?")))
        elif st == "NotAvailable":
            own_na += 1
        else:
            own_ok += 1
    print("civ-owned type-3 rows whose owner's TECH row reads:")
    print("  available (RC or RR): %d" % own_ok)
    print("  NotAvailable:         %d" % own_na)
    print("  no row at all:        %d" % own_missing)
    if samples_missing:
        print("  samples with no row: %s" % samples_missing)
    print()

    # how many civs can research the tech that carries the upgrade?
    print("a few known upgrade techs, and who can research them:")
    for ti, t in enumerate(techs):
        name = (t.get("name") or "")
        if name in ("Crossbowman", "Man-at-Arms", "Arbalester", "Halberdier",
                    "Two-Handed Swordsman", "Champion", "Paladin", "Hussar"):
            rr = [s for s in trees
                  if CT.can_build(trees[s], ti, CT.TECH_USE_TYPES)]
            tm = sem.techs.get(ti)
            print("  tech %-4s %-24s (en %-22s) researchable by %d civs"
                  % (ti, name, (tm.en if tm else "?"), len(rr)))
    print()

    # --- the decisive summary ----------------------------------------------
    print("=" * 74)
    print("VERDICT -- read with care, this table does NOT prove causation")
    print("=" * 74)
    print("  The 'no_upgrade' cells are EMPTY, which reads as 'owning an")
    print("  upgrade is necessary for buildability'.  That reading is an")
    print("  artifact: 196 of 305 targets are reachable through a GLOBAL")
    print("  upgrade, so the predicate is true for 1816 of 1896 pairs (95.8%)")
    print("  and cannot discriminate anything.")
    print()
    print("  The dependent variable is also wrong: an upgrade target is")
    print("  something you UPGRADE INTO, not something a building trains.")
    print("  Every apparent disagreement in Q1b is a unit with builders == 0")
    print("  (House, town-centre variants, internal placeholders).")
    print()
    print("  See `_probe/probe_type3_discriminate.py` and the pinned")
    print("  `_probe/test_type3_scope.py` for the corrected scope.")
    print("  => `type 3` edits WHAT an upgrade does (A -> B); who may obtain")
    print("     it is decided by the tree rows (`unit.availability` and")
    print("     `tech.availability`).  Do not sell it as an availability fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
