# -*- coding: utf-8 -*-
"""Find two CONFOUND-FREE test subjects with opposite halves.

The 2026-10-14 test granted Hand Cannoneer to Britons and nothing appeared.
That proved nothing: unit 5 carries `RequiredAge 4` (Imperial Age), so a Dark
Age game gates it whichever file the menu reads.

The decisive question is: **does the running game read the TREE file, the PANEL
file, or both?**  One game session can answer it if the two halves DISAGREE:
put one unit in the tree only and a different unit in the panel only.  Then

    tree unit shows up   -> the game read the tree
    panel unit shows up  -> the game read the panel
    both / neither       -> it reads both / neither

Both subjects must be Dark-Age (Age ID == 1) so no age gate can hide them, and
both must live at a building the civ really has.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

CIV = "Britons"
STEM = CT.civ_file_stem(CIV)

tk = A.open_toolkit()
trees = CT.load_trees(tk.game_root)
panels = BP.load_all(tk.game_root)
brit = trees[STEM]
brit_key = BP.panel_path_for(tk.game_root, CIV)[1]
print("civ %s -> tree stem %s / panel key %s" % (CIV, STEM, brit_key))

have = set()
for r in CT.unit_rows(brit):
    have.add(r.get("Node ID"))
print("Britons tree rows: %d" % len(have))

# Every shipped panel entry that is Dark Age and sits at a building, grouped by
# the unit id.  This is the pool the panel half can copy from.
pool = BP.entry_pool(panels[brit_key]["obj"], BP.UNITS_KEY)
print("panel entries (by node id): %d" % len(pool))

cands = []
for node_id, rows in sorted(pool.items()):
    if node_id in have:
        continue                      # Britons already has a row -> not a grant
    for ck, bldg, e in rows:
        if e.get("RequiredAge") != 1:
            continue                  # age-gated -> the previous test's mistake
        # the donor civ must really be able to build it, in the Dark Age
        donor = trees.get(CT.civ_file_stem(ck))
        if donor is None:
            continue
        dr = CT.row_for(donor, node_id)
        if dr is None or CT.node_status(donor, node_id) != "ResearchedCompleted":
            continue
        if dr.get("Age ID") != 1:
            continue
        if dr.get("Building ID") != 87 and dr.get("Building ID") != 12:
            continue
        cands.append((node_id, e.get("Name"), bldg, ck, dr.get("Building ID")))

print()
print("candidates (Dark Age, not in Britons' tree, donor builds it):")
seen = set()
for node_id, name, bldg, ck, trow_b in cands:
    if node_id in seen:
        continue
    seen.add(node_id)
    print("  unit %-6d %-26s panel@%-4s tree@%-4s donor %s"
          % (node_id, str(name), bldg, trow_b, ck))
print("  total distinct: %d" % len(seen))

# What building numbers do Britons actually have in the tree?  A granted row at
# a building Britons does not own would be invisible for a boring reason.
bset = sorted({r.get("Building ID") for r in CT.unit_rows(brit)
               if r.get("Building ID")})
print()
print("building ids Britons' unit rows point at: %s" % bset)
print("bridge 12 (Barracks) present: %s   87 (Archery Range) present: %s"
      % (12 in bset, 87 in bset))
