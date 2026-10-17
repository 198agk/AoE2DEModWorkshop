"""Which screen does `futuravailableunits.json` feed?

The exe names it right beside BOTH `CommandPanel` and `TechTreePreviewPanel`:

    0325a528  ScreenTechTree
    0325a578  CommandPanel
    0325a588  storage_point_list
    0325a5a0  replace
    0325a5a8  use_modes_path_for_mods
    0325a5c0  linkedUnits.json
    0325a5d8  futuravailableunits.json
    0325a5f8  paphosfutureavailableunits.json
    0325a618  morematerials
    0325a628  materials
    0325a638  TechTreePreviewPanel
    0325a650  MenuPanel

Proximity in a string pool is weak evidence, so do not settle it that way.  The
NAME settles it: the command panel shows what you can build NOW, while "future
available units" is what the TECH TREE PREVIEW exists to show.  Test that
reading against the file's own shape:

  * if it is a build menu, it should cover the buildings that HAVE a build menu
    (barracks, range, stable, dock, ...) and omit the Castle (unique units are
    trained at the castle, which is not part of the villager build menu)
  * if it is a tech tree preview, it should cover the castle too

Run:  python _probe/probe_fu_scope.py
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
from aoe2mod.semantic import index as SI  # noqa: E402

FU_REL = os.path.join("resources", "_common", "dat", "futuravailableunits.json")


def main():
    tk = A.open_toolkit()
    fu = json.loads(open(os.path.join(tk.game_root, FU_REL), "rb")
                    .read().decode("utf-8-sig"))
    sem = SI.index()

    def nm(i):
        e = sem.units.get(i)
        return (e.en or e.zh) if e else "?"

    # Which buildings appear, and how often across civs?
    bcnt = Counter()
    for civ, blk in fu.items():
        for b in blk.get("Buildings", []):
            bcnt[b.get("ID")] += 1
    print("buildings referenced, by civ coverage (civs: %d):" % len(fu))
    for bid, n in bcnt.most_common(40):
        print("  %-6d %-26s in %d civs" % (bid, nm(bid)[:26], n))
    print()

    # Is the Castle (82) among them?  Unique units live there.
    for probe in (82, 12, 87, 101, 45):
        print("building %-4d %-20s present in %d of %d civs"
              % (probe, nm(probe)[:20], bcnt.get(probe, 0), len(fu)))
    print()

    # Where do the "tree says buildable, panel omits" units live in the tree?
    trees = CT.load_trees(tk.game_root)
    by_tree = {}
    for k in fu:
        cand = CT.civ_file_stem(k)
        if cand in trees:
            by_tree[cand] = k
    print("the 7 omissions and the building their tree row points at:")
    for civ, uid in (("GOTHS", 759), ("GOTHS", 761), ("HUNS", 886),
                     ("HUNS", 887), ("GEORGIANS", 588), ("SICILIANS", 588),
                     ("TUPI", 532)):
        row = CT.row_for(trees.get(civ, {}), uid)
        b = row.get("Building ID") if row else None
        print("  %-10s %-5d %-22s tree Building ID=%s (%s)"
              % (civ, uid, nm(uid)[:22], b, nm(int(b)) if b else "?"))
    print()
    print("If those Building IDs are 82 (Castle), the panel file leaves the")
    print("castle out on purpose -- consistent with a build menu, not with")
    print("a full tech-tree preview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
