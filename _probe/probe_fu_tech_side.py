"""The tech half of the same question, plus the mode sibling.

`futuravailableunits.json` is named for units but carries a `Techs` list on 782
buildings, and the sample entry is `{"ID": 100, "Name": "Crossbowman"}` -- 100 is
a TECH id (the tech that turns Archers into Crossbowmen), not a unit.  So the
cache covers both id spaces, which means `tech.availability` has a place to write
too, and it has to be tested the same way the unit half was:

  1. does each panel `Techs` entry sit under the Building ID the civ's tree tech
     row gives?
  2. does RequiredAge track the tree's Age ID?
  3. does it list only techs the tree offers (i.e. never a `NotAvailable` row)?
  4. and what is `paphosfutureavailableunits.json` -- the mode override for the
     civs the main file is missing?

This decides whether the product has to write the CACHE as well as the tree.

Run:  python _probe/probe_fu_tech_side.py
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat")


def load(path):
    return json.loads(open(path, "rb").read().decode("utf-8-sig"))


def main():
    tk = A.open_toolkit()
    d = os.path.join(tk.game_root, DAT_REL)
    fu = load(os.path.join(d, "futuravailableunits.json"))
    pap = load(os.path.join(d, "paphosfutureavailableunits.json"))
    trees = CT.load_trees(tk.game_root)
    by_tree = {}
    for k in fu:
        cand = CT.civ_file_stem(k)
        if cand in trees:
            by_tree[cand] = k

    tech_ids = set()
    for civ in trees:
        for r in CT.tech_rows(trees[civ]):
            tech_ids.add(r.get("Node ID"))
    unit_ids = set()
    for civ in trees:
        for r in CT.unit_rows(trees[civ]):
            unit_ids.add(r.get("Node ID"))
    print("tree ids: %d tech, %d unit  (overlap %d)"
          % (len(tech_ids), len(unit_ids), len(tech_ids & unit_ids)))
    print()

    # Which space does an entry belong to?  An id in BOTH is ambiguous; the
    # list it sits in is the only reliable signal, so record where we saw it.
    seen = Counter()
    rows = []
    for civ in sorted(by_tree):
        for blk in fu[by_tree[civ]].get("Buildings", []):
            bid = blk.get("ID")
            for key, space in (("Techs", "tech"), ("Units", "unit")):
                for e in blk.get(key) or []:
                    i = e.get("ID")
                    seen[(space, i in tech_ids, i in unit_ids)] += 1
                    rows.append((civ, space, bid, e))
    print("entry placement vs tree id sets  (space, in_tech, in_unit):")
    for k, n in sorted(seen.items()):
        print("  %-6s tech=%-5s unit=%-5s  %5d" % (k[0], k[1], k[2], n))
    print()

    # ---- the tech half ----------------------------------------------------
    t_ok = t_bad = t_norow = 0
    t_mism = []
    for civ, space, bid, e in rows:
        if space != "tech":
            continue
        row = CT.row_for(trees[civ], e.get("ID"), CT.TECH_USE_TYPES)
        if row is None:
            t_norow += 1
            continue
        tb = row.get("Building ID")
        if tb is not None and int(tb) == int(bid):
            t_ok += 1
        else:
            t_bad += 1
            t_mism.append((civ, e.get("ID"), e.get("Name"), bid, tb))
    print("tech entries: %d" % (t_ok + t_bad + t_norow))
    print("  building matches tree tech row : %d" % t_ok)
    print("  building differs               : %d" % t_bad)
    print("  no tree tech row for that civ  : %d" % t_norow)
    for m in t_mism[:10]:
        print("    %-14s tech %-5s %-28s panel %-5s tree %s" % m)
    print()

    st = Counter()
    for civ, space, bid, e in rows:
        if space != "tech":
            continue
        row = CT.row_for(trees[civ], e.get("ID"), CT.TECH_USE_TYPES)
        st[row.get("Node Status") if row is not None else "(no tree row)"] += 1
    print("panel TECH entries by tree status: %s" % dict(st))
    print()

    trr = set()
    for civ in trees:
        for r in CT.tech_rows(trees[civ]):
            if r.get("Node Status") == "ResearchRequired":
                trr.add((civ, r.get("Node ID")))
    print("tree (civ, tech) pairs gated ResearchRequired: %d" % len(trr))
    listed = {(c, e.get("ID")) for c, s, b, e in rows if s == "tech"}
    print("  of those, listed in the panel cache          : %d" % len(trr & listed))
    print()

    # ---- paphos sibling ---------------------------------------------------
    print("paphosfutureavailableunits.json: %d keys" % len(pap))
    print("  %s" % sorted(pap))
    print("  keys also in the main file: %s" % sorted(set(pap) & set(fu)))
    only = sorted(set(pap) - set(fu))
    print("  keys ONLY there: %s" % only)
    for k in only[:6]:
        nb = len(pap[k].get("Buildings", []))
        nu = sum(len(b.get("Units") or []) for b in pap[k].get("Buildings", []))
        nt = sum(len(b.get("Techs") or []) for b in pap[k].get("Buildings", []))
        stem = CT.civ_file_stem(k)
        print("    %-14s stem=%-14s buildings %-4d units %-4d techs %-4d tree? %s"
              % (k, stem, nb, nu, nt, stem in trees))
    return 0


if __name__ == "__main__":
    sys.exit(main())
