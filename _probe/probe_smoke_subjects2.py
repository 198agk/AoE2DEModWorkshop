# -*- coding: utf-8 -*-
"""Pick subjects for a DECISIVE one-session experiment.

Question: does the running game read the TREE file, the PANEL file, or both?

One game session answers it if the two halves DISAGREE.  Build a mod with:

  U2  written into the TREE only  (no panel entry)
  U3  written into the PANEL only (no tree row)

Then: U2 shows up -> the game read the tree.  U3 shows up -> it read the panel.
Both -> both.  Neither -> neither.  A `unit.stat` sentence (villager HP, which
the user already saw work in-game) proves the mod itself loaded, so "neither"
cannot be confused with "the mod was not loaded".

Requirements for a subject:
  * Britons has NO tree row for it (otherwise the grant changes nothing)
  * Dark Age (Age ID == 1 / RequiredAge == 1) -- the previous test died on an
    Imperial-Age gate, so no subject may carry one
  * it sits at a building Britons really owns, or it would be invisible for a
    boring reason
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

have = {r.get("Node ID") for r in CT.unit_rows(brit)}
bldgs = sorted({r.get("Building ID") for r in CT.unit_rows(brit)
                if r.get("Building ID")})
print("Britons owns buildings: %s" % bldgs)
print("Britons already has %d unit rows" % len(have))

# ---------------------------------------------------------------------------
# U2 candidates: the TREE can grant these.  The donor row carries the donor's
# own `Building ID`, so only donors at a building Britons owns will be visible.
# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("U2 -- grantable via the TREE (donor exists, Dark Age, owned building)")
print("=" * 78)
tree_cands = {}
for ck, tree in sorted(trees.items()):
    for r in CT.unit_rows(tree):
        nid = r.get("Node ID")
        if nid in have or r.get("Age ID") != 1:
            continue
        if r.get("Building ID") not in bldgs:
            continue
        if CT.node_status(tree, nid) != "ResearchedCompleted":
            continue
        tree_cands.setdefault(nid, (r.get("Name String ID"), ck,
                                    r.get("Building ID")))
for nid, (sid, ck, b) in sorted(tree_cands.items())[:40]:
    print("  unit %-6d stringid %-8s donor %-14s building %s" % (nid, sid, ck, b))
print("  total: %d" % len(tree_cands))

# ---------------------------------------------------------------------------
# U3 candidates: the PANEL has a Dark-Age entry for them, at a building Britons
# owns, and Britons has no tree row.  Insert that shipped entry into Britons.
# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("U3 -- writable into the PANEL only (shipped entry, Dark Age, owned bldg)")
print("=" * 78)
panel_cands = {}
obj = panels[brit_key]["obj"]
for nid, rows in sorted(BP.entry_pool(obj, BP.UNITS_KEY).items()):
    if nid in have:
        continue
    for ck, b, e in rows:
        if e.get("RequiredAge") != 1 or b not in bldgs:
            continue
        panel_cands.setdefault(nid, (e.get("Name"), ck, b))
        break
for nid, (nm, ck, b) in sorted(panel_cands.items())[:40]:
    print("  unit %-6d %-28s donor %-14s building %s" % (nid, nm, ck, b))
print("  total: %d" % len(panel_cands))

# ---------------------------------------------------------------------------
# Overlap: units that BOTH halves can carry -- usable as the "both" control.
# ---------------------------------------------------------------------------
both = sorted(set(tree_cands) & set(panel_cands))
print()
print("units both halves can carry (control candidates): %s" % both[:20])
print()
print("PICK: one from U2 for the tree, a DIFFERENT one from U3 for the panel.")
