# -*- coding: utf-8 -*-
"""Refine the type-3 contrast: separate GLOBAL upgrades from civ-owned ones.

The first pass (`probe_type3_contrast.py`) produced a table with an empty cell:

    can_build  + owns_upgrade : 1477
    cannot     + owns_upgrade :  419
    can_build  + no_upgrade  :    0     <- empty
    cannot     + no_upgrade  :    0     <- empty

which reads as "owning an upgrade is NECESSARY for buildability".  That reading
is suspect for a specific reason: most upgrade commands sit on GLOBAL techs
(`tech.civ < 0`), so "a civ owns an upgrade into B" is true for every civ at
once.  A population where the predicate is almost always true cannot discriminate
anything -- it makes the "no_upgrade" cells empty by construction, not by
causation.

So this file splits the targets by where the upgrade comes from:

  * global-only targets  -- owning is trivially true, the table cannot speak;
  * civ-owned-only targets -- owning genuinely varies, and here the table can
    actually discriminate.

Only the second population may be used to claim anything.  Writes nothing.
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

    own_to = collections.defaultdict(set)
    glob_to = set()
    rows = []
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] != 3:
                continue
            _ty, a, b, cc, dd = r["raw"]
            rows.append((ti, t.get("civ"), a, b, cc, dd))
            if t.get("civ") is None or t.get("civ") < 0:
                glob_to.add(b)
            else:
                own_to[t["civ"]].add(b)

    targets = sorted({b for _t, _o, _a, b, _c, _d in rows if isinstance(b, int)})
    print("type 3 rows: %d   distinct targets: %d" % (len(rows), len(targets)))
    print("targets reachable via at least one GLOBAL upgrade: %d" % len(glob_to & set(targets)))
    print("targets reachable ONLY via civ-owned upgrades:      %d"
          % len(set(targets) - glob_to))
    print()

    # How often is "owns an upgrade" trivially true?  Over ALL unit rows.
    triv = 0
    total = 0
    for stem, tr in sorted(trees.items()):
        idx = stem2idx.get(stem)
        for row in CT.unit_rows(tr):
            nid = row.get("Node ID")
            if nid is None or nid not in targets:
                continue
            total += 1
            if nid in glob_to:
                triv += 1
    print("(civ, target-row) pairs: %d" % total)
    print("  of which the upgrade is available GLOBALLY (predicate trivially true): %d (%.1f%%)"
          % (triv, 100.0 * triv / max(1, total)))
    print()

    # --- the discriminating population: civ-owned-only targets -------------
    own_only = sorted(set(targets) - glob_to)
    print("=" * 74)
    print("DISCRIMINATING POPULATION: the %d civ-owned-only targets" % len(own_only))
    print("=" * 74)
    tab = collections.Counter()
    for stem, tr in sorted(trees.items()):
        idx = stem2idx.get(stem)
        for row in CT.unit_rows(tr):
            nid = row.get("Node ID")
            if nid is None or nid not in own_only:
                continue
            can = CT.can_build(tr, nid)
            owns = idx is not None and nid in own_to.get(idx, set())
            tab[("can_build" if can else "cannot",
                 "owns_upgrade" if owns else "no_upgrade")] += 1
    for k in sorted(tab):
        print("  %-10s + %-13s : %d" % (k[0], k[1], tab[k]))
    for k in (("can_build", "no_upgrade"), ("cannot", "owns_upgrade")):
        if tab.get(k):
            print("  -> %s+%s = %d" % (k[0], k[1], tab[k]))
    print()

    # Concrete: for each civ-owned-only target, name the disagreement.
    print("concrete civ-owned-only targets:")
    for b in own_only:
        builders = CT.builders(trees, b)
        owners = [s for s in trees if (stem2idx.get(s) is not None
                                       and b in own_to.get(stem2idx[s], set()))]
        u = sem.units.get(b)
        print("  unit %-5s %-24s builders=%-3d upgrade-owners=%-3d %s"
              % (b, (u.en if u else "?"), len(builders), len(owners),
                 "DISAGREE" if len(builders) != len(owners) else ""))
    print()

    # --- Q2 redone: is the carrying tech's row the gate? -------------------
    print("=" * 74)
    print("Q2: for civ-owned upgrade techs, does the owner have a usable row?")
    print("=" * 74)
    tally = collections.Counter()
    for ti, o, _a, _b, _c, _d in rows:
        if o is None or o < 0:
            continue
        stem = next((s for s, i in stem2idx.items() if i == o), None)
        if stem is None:
            continue
        st = CT.node_status(trees[stem], ti, CT.TECH_USE_TYPES)
        tally[st] += 1
    for st, n in tally.most_common():
        print("  %-22s : %d" % (st, n))
    print()
    print("NOTE: 'None' here means the owner has no tech row for the carrying")
    print("tech.  That is NOT automatically a defect -- the .dat holds one")
    print("GLOBAL tech record, so a civ can own an INTERNAL tech that a")
    print("different (tree-listed) tech makes reachable.  Claiming otherwise")
    print("requires the tree-side tech id, which this probe has not proven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
