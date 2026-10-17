# -*- coding: utf-8 -*-
"""Are `.dat` type-2 "enable" commands and CivTechTrees rows BOTH required?

This is the decisive question before implementing the type-2 family, and it is
also an audit of the `unit.availability` intent already shipped.

Two mechanisms can make a unit buildable for a civ:

  * a `type 2` effect command on a tech the civ owns (`tech.civ == civ index`)
    -- the ".dat side";
  * a row in that civ's `CivTechTrees/<CIV>.json` -- the "tree side", which is
    what `unit.availability` writes and what the engine provably reads.

If every civ that HAS a tree row also owns an enable tech, then a row alone is
not sufficient and `unit.availability` is half a feature.  If civs have rows
without enable techs, a row stands on its own.  Both answers are useful; only
one of them is comfortable.

It writes nothing.
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
    civs = tk._civs
    sem = SI.index()
    trees = CT.load_trees(tk.game_root)

    # civ index -> dat civ name -> tree key
    idx2tree = {}
    for c in civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            idx2tree[c["index"]] = stem

    # --- the .dat side: which (civ, unit) pairs does an enable command grant?
    dat_enabled = collections.defaultdict(set)   # civ index -> {unit ids}
    dat_disabled = collections.defaultdict(set)
    global_enabled = set()
    for ti, t in enumerate(techs):
        owner = t.get("civ")
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] != 2:
                continue
            _ty, unit, b, cc, dd = r["raw"]
            if b == 1:
                if owner is None or owner < 0:
                    global_enabled.add(unit)
                else:
                    dat_enabled[owner].add(unit)
            elif b == 0:
                dat_disabled[owner].add(unit)

    rows_total = sum(1 for _c, tr in trees.items() for _r in CT.unit_rows(tr))
    print("CivTechTrees: %d civs, %d unit rows" % (len(trees), rows_total))
    print("type 2 clean enable commands: civ-owned %d pairs across %d civs; "
          "global %d units"
          % (sum(len(v) for v in dat_enabled.values()), len(dat_enabled),
             len(global_enabled)))
    print()

    # --- the question, per unit: civs with a row vs civs with an enable ---
    unit_nodes = set()
    for c, tr in trees.items():
        for r in CT.unit_rows(tr):
            unit_nodes.add(r.get("Node ID"))
    unit_nodes.discard(None)
    print("distinct unit nodes in the tree layer: %d" % len(unit_nodes))
    print()

    row_without_enable = []
    enable_without_row = []
    both = 0
    for idx, stem in sorted(idx2tree.items()):
        tr = trees[stem]
        for node in CT.unit_rows(tr):
            nid = node.get("Node ID")
            if nid is None:
                continue
            has_row = True
            has_en = (nid in dat_enabled.get(idx, set())) or (nid in global_enabled)
            if has_row and has_en:
                both += 1
            elif has_row:
                row_without_enable.append((stem, nid))
    for idx, units in dat_enabled.items():
        stem = idx2tree.get(idx)
        if stem is None:
            continue
        tr = trees[stem]
        for u in units:
            if not CT.has(tr, u):
                enable_without_row.append((stem, u))

    print("(civ, unit-row) pairs that ALSO own a type-2 enable: %d" % both)
    print("unit rows whose civ owns NO enable command: %d" % len(row_without_enable))
    print("type-2 enables whose civ has NO tree row: %d" % len(enable_without_row))
    print()

    # Which units are row-without-enable, and what does the tree say about them?
    if row_without_enable:
        c = collections.Counter(n for _s, n in row_without_enable)
        print("top row-without-enable units: %s"
              % [(n, (sem.units.get(n).en if sem.units.get(n) else "?"), k)
                 for n, k in c.most_common(10)])
        print()
        print("sample pairs:")
        for s, n in row_without_enable[:10]:
            u = sem.units.get(n)
            print("    %-14s unit %-5s %-28s status=%s"
                  % (s, n, (u.en if u else "?"), CT.node_status(trees[s], n)))
    print()

    # --- the exclusive units, as concrete known cases -------------------
    EXCL = {41: "GOTHS", 8: "BRITONS", 725: "AZTECS", 755: "HUNS", 692: "VIKINGS"}
    print("the five exclusive units, both mechanisms:")
    name2idx = {c.get("name"): c["index"] for c in civs}
    for uid, stem in sorted(EXCL.items()):
        # find the dat civ whose file stem is this
        idx = None
        for i, s in idx2tree.items():
            if s == stem:
                idx = i
        en = (uid in dat_enabled.get(idx, set())) if idx is not None else None
        u = sem.units.get(uid)
        print("    %-28s unit %-5s civ %-8s type2-enable=%s  tree_row=%s"
              % ((u.en if u else "?"), uid, stem, en, CT.has(trees[stem], uid)))
    print()

    # --- and for a civ that has the row, does the enable come from a GLOBAL?
    print("global enables (tech.civ < 0) sample: %s" % sorted(global_enabled)[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
