# -*- coding: utf-8 -*-
r"""Is the two-game protocol sound?  Check every GATE field on both subjects.

A subject whose own entry carries a gate is the mistake that cost this project two
in-game tests.  The earlier confound was an AGE gate (`RequiredAge`); a panel
entry can also carry a **research gate**:

  * `buildpanel.GATE_KEYS = ("PrereqTech", "PrereqIconSet", "PrereqIconIndex",
                             "PrereqStyle", "PrereqStringID")`
  * a tree row can carry `Prerequisite IDs` + `Prerequisite Types`

If `JURCHENS`' panel entry for 77 carried `PrereqTech`, the button might not appear
even when the panel drives -- and "absent" would be misread as "the panel is not
consulted".  Check both subjects, in both layers, for every gate field.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

CASES = [
    ("JURCHENS", "Jurchens", 12, [77, 473, 567], "GAME 1 (kind P)"),
    ("SICILIANS", "Sicilians", 49, [588], "GAME 2 (kind T)"),
    ("GEORGIANS", "Georgians", 49, [588], "GAME 2 alt"),
]

print("BP.GATE_KEYS = %s" % (BP.GATE_KEYS,))
print()

for stem, disp, bld, ids, label in CASES:
    tree = trees[stem]
    pk = BP.panel_path_for(GAME, disp)
    obj = panels[pk[1]]["obj"]
    print("=" * 76)
    print("%s  %s   building %s" % (label, stem, bld))
    print("=" * 76)
    for uid in ids:
        print("  --- unit %s ---" % uid)
        # panel side: the RAW entry, every key
        b, e = BP.find_entry(obj, disp, uid, BP.UNITS_KEY)
        print("    panel: building=%r" % b)
        print("    panel: entry=%s" % json.dumps(e, ensure_ascii=False))
        if e:
            gates = {k: e[k] for k in BP.GATE_KEYS if k in e}
            print("    panel: GATE fields present = %s" % (gates or "NONE"))
        # tree side: the raw row, every key
        row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
        if row is None:
            print("    tree : NO ROW AT ALL")
        else:
            st = CT.node_status(tree, uid, CT.UNIT_USE_TYPES)
            print("    tree : status=%r age=%r building=%r"
                  % (st, row.get("Age ID"), row.get("Building ID")))
            pr = row.get("Prerequisite IDs")
            pt = row.get("Prerequisite Types")
            real = [(i, t) for i, t in zip(pr or [], pt or [])
                    if t not in (None, "None") and i not in (None, 0)]
            print("    tree : Prerequisite IDs=%s Types=%s -> real prereqs=%s"
                  % (pr, pt, real or "NONE"))
            print("    tree : Trigger Tech ID=%r Link ID=%r"
                  % (row.get("Trigger Tech ID"), row.get("Link ID")))
            # does any listed prerequisite exist as a tech row for this civ?
            for pid, ptype in real:
                tstat = CT.node_status(tree, pid, CT.TECH_USE_TYPES)
                print("        prereq %s (%s): this civ's tech status = %r"
                      % (pid, ptype, tstat))
        print()

print("=== what does PrereqTech actually contain, across the whole panel? ===")
from collections import Counter                                # noqa: E402
cnt = Counter()
examples = []
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        for blk in BP.buildings(rec["obj"], disp):
            for e in (blk.get(BP.UNITS_KEY) or []):
                for k in BP.GATE_KEYS:
                    if k in e:
                        cnt[k] += 1
                        if len(examples) < 6:
                            examples.append((disp, blk.get("ID"), e.get(k), k))
print("  gate-key occurrences across every panel entry:")
for k, n in cnt.most_common():
    print("     %-18s %d" % (k, n))
print("  examples: %s" % (examples,))
