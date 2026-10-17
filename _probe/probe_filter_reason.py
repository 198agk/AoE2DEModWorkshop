# -*- coding: utf-8 -*-
r"""Isolate the kind-P filter on one civilization, with the reason per unit.

`probe_injective_filtered.py` printed ARCHER (4) among HUNS' kind-P subjects.
The tree row for 4 is `ResearchedCompleted` at building 87, so the filter must
have let it through for a reason.  Print the reason.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

stem, disp = "HUNS", "Huns"
tree = trees[stem]
obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
owned = {r.get("Node ID") for r in CT.rows_of(tree)
         if r.get("Use Type") == "Building"}
rows = {r.get("Node ID"): r for r in CT.unit_rows(tree)
        if r.get("Node ID") is not None}

print("owned buildings (%d): %s" % (len(owned), sorted(owned)))
print()

panel_rows = {}
for b_id in sorted(BP.buildings(obj, disp) or []):
    us = BP.entries(obj, disp, b_id, BP.UNITS_KEY) or []
    for e in us:
        panel_rows.setdefault(e.get("ID"), []).append((b_id, e.get("RequiredAge")))

print("panel units whose building is OWNED, with the reason they pass/fail kind-P:")
print("  %-6s %-22s %-22s %-8s %s" % ("unit", "name", "panel bldg(s)",
                                      "owned?", "tree status"))
for uid, places in sorted(panel_rows.items()):
    for b_id, age in places:
        if b_id not in owned:
            continue
        st = rows[uid].get("Node Status") if uid in rows else "(no row)"
        passes = (uid not in rows) or st == "NotAvailable"
        u = idx.get("unit", uid)
        print("  %-6s %-22s %-22s %-8s %-18s %s"
              % (uid, (u.zh or u.en) if u else "?",
                 "b%s a%s" % (b_id, age), "yes", st,
                 "PASSES kind-P" if passes else ""))

print()
print("=> entries that really pass kind-P for HUNS:")
n = 0
for uid, places in sorted(panel_rows.items()):
    for b_id, age in places:
        if b_id not in owned:
            continue
        st = rows[uid].get("Node Status") if uid in rows else None
        if (uid not in rows) or st == "NotAvailable":
            u = idx.get("unit", uid)
            print("   unit %-6s %-22s building %-5s RequiredAge %s"
                  % (uid, (u.zh or u.en) if u else "?", b_id, age))
            n += 1
print("   count = %d" % n)
