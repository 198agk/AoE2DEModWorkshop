"""Verify ONE unreachable-Building-ID case by hand, from the raw JSON.

`probe_building_warning.py` printed truncated building lists, so the claim
"ARMENIANS cannot reach Building ID 104" was only eyeballed.  This checks it
against the raw file: what building rows does ARMENIANS actually have, and does
node 104 appear among the ids it can see at all?

If 104 (Monastery) really is absent from ARMENIANS, a granted Missionary would
have no Monastery to be trained at -- so the reading is right and the warning
wording is the thing to decide.  If it IS present, my earlier measurement was
wrong and nothing should change.

Read-only.  Prints raw evidence.
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    trees = CT.load_trees(GAME)
    for civ in ("ARMENIANS", "SPANISH", "BRITONS"):
        t = trees[civ]
        rows = CT.rows_of(t)
        bldg_rows = [r for r in rows if r.get("Use Type") == "Building"]
        unit_rows = CT.unit_rows(t)
        bldg_ids_in_units = sorted({str(r.get("Building ID")) for r in unit_rows})
        all_node_ids = sorted({str(r.get("Node ID")) for r in rows})
        print("\n=== %s ===" % civ)
        print("  total rows %d (building rows %d, unit rows %d)"
              % (len(rows), len(bldg_rows), len(unit_rows)))
        print("  Building IDs referenced by its unit rows: %s" % bldg_ids_in_units)
        print("  is '104' among those references?  %s"
              % ("104" in bldg_ids_in_units))
        print("  does '104' appear as ANY node id in its rows?  %s"
              % ("104" in all_node_ids))
        print("  building rows it has (Node ID -> Name): %s"
              % [(r.get("Node ID"), r.get("Name")) for r in bldg_rows][:10])
        # where is the Monastery for a civ that has one?
        for r in unit_rows:
            if r.get("Name") in ("Monk", "Missionary"):
                print("  its %-12r row: Building ID=%s Age ID=%s"
                      % (r.get("Name"), r.get("Building ID"), r.get("Age ID")))

    print("\n=== raw check: what does the ARMENIANS file actually contain for 104? ===")
    path = os.path.join(CT.trees_dir(GAME), "ARMENIANS.json")
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    hits = []
    for key, val in raw.items():
        if isinstance(val, list):
            for e in val:
                if isinstance(e, dict) and (e.get("Node ID") == 104
                                            or e.get("Building ID") == 104
                                            or e.get("Link ID") == 104):
                    hits.append((key, e.get("Node ID"), e.get("Use Type"),
                                 e.get("Name"), e.get("Building ID")))
    print("  rows touching 104: %s" % hits[:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
