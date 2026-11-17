# -*- coding: utf-8 -*-
r"""PIN: the panel's `Builder` block is NOT the complete villager build menu.

=============================================================================
CORRECTION (2026-10-15).  THIS FILE'S ORIGINAL CLAIM WAS A MISREADING.
=============================================================================
It used to assert "each basic building appears in ZERO civs' panels" and conclude
"the panel is a DIFFERENT model from the tree -- it omits buildings every
civilization can certainly build".

That is **wrong**.  Building 12 (Barracks) IS in every civilization's panel, as a
**BLOCK with its own `Units` array**:

    BP.buildings(obj, "Britons") -> [(118,'Builder'), (13,'Fishing Ship'),
        (87,'Archery Range'), (12,'Barracks'), (101,'Stable'), ...]

What was actually measured is that 12 is absent from the **`Builder` (118) block's
`Units` list** -- because the Barracks is not something the *Builder* manufactures;
the Barracks is itself a container.  The panel has two kinds of building reference:

    a BLOCK  (ID/Name/Units/Techs)   <- somewhere you can produce
    an ENTRY inside a block's `Units` <- something produced there

"Absent from a `Units` array" and "absent from the panel" are statements about
different things, and 434 (basic building x civ) pairs demonstrate it: absent from
every `Units` list, present as blocks.  See `test_panel_shape.py` for the correct
model.

What SURVIVES from the original finding, and is still worth pinning: the `Builder`
block's `Units` list is much smaller than the tree's building set, so the `Builder`
block alone cannot be the whole villager build menu.  That narrower statement is
what this file now asserts.
"""
import os
import _gamepaths as GP
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
fails = []
BUILDER = 118


def check(name, ok, detail=""):
    print("  %-64s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

civs = {}
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        if stem in trees:
            civs[stem] = (disp, rec["obj"])

print("A  the Builder(118) block vs the tree's building set")
tree_counts, panel_counts, missing_sets = [], [], {}
for stem, (disp, obj) in sorted(civs.items()):
    t = {r.get("Node ID") for r in CT.rows_of(trees[stem])
         if r.get("Use Type") == "Building"}
    blk = next((b for b in BP.buildings(obj, disp) if b.get("ID") == BUILDER),
               None)
    p = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])} if blk else set()
    tree_counts.append(len(t))
    panel_counts.append(len(p))
    missing_sets[stem] = sorted(t - p)
print("     tree Building rows per civ  : %s" % dict(Counter(tree_counts)))
print("     Builder(118) Units per civ  : %s" % dict(Counter(panel_counts)))
check("every civ has a Builder(118) block", all(panel_counts),
      "civs without one: %d" % sum(1 for c in panel_counts if not c))
check("the Builder block is SMALLER than the tree's building set for every civ",
      all(a > b for a, b in zip(tree_counts, panel_counts)))
check("the Builder block lists far fewer entries than the tree has buildings",
      max(panel_counts) < min(tree_counts),
      "max Builder %d vs min tree %d" % (max(panel_counts), min(tree_counts)))

print()
print("B  the CORRECTION: the basics are present -- as their own BLOCKS")
BASICS = {12: "Barracks", 70: "House", 68: "Mill", 562: "Lumber Camp",
          584: "Mining Camp", 72: "Palisade Wall"}
n_civ = len(civs)
check("the census actually covered civilizations", n_civ >= 60,
      "only %d civs in scope" % n_civ)
as_block, in_builder_units = {}, {}
for bid, nm in sorted(BASICS.items()):
    as_block[bid] = sum(1 for _s, (d, o) in civs.items()
                        if any(b.get("ID") == bid for b in BP.buildings(o, d)))
    in_builder_units[bid] = sum(
        1 for _s, (d, o) in civs.items()
        if bid in {e.get("ID")
                   for b in BP.buildings(o, d) if b.get("ID") == BUILDER
                   for e in (b.get(BP.UNITS_KEY) or [])})
    print("     %-16s as a BLOCK in %2d/%d civs   in Builder's Units: %d"
          % (nm, as_block[bid], n_civ, in_builder_units[bid]))
check("every basic building is a BLOCK in the great majority of civilizations",
      all(as_block[b] >= 50 for b in BASICS),
      "as blocks: %s" % as_block)
check("none of them appears in the Builder block's Units list",
      all(in_builder_units[b] == 0 for b in BASICS),
      "nonzero: %s" % {b: v for b, v in in_builder_units.items() if v})
print("     -> the earlier claim 'the panel omits the basics' was a misreading: it")
print("        measured the Builder's Units list, not the panel's blocks.")

print()
print("C  so the Builder block alone is not the whole build menu")
_brit = missing_sets.get("BRITONS", [])
print("     BRITONS buildings absent from its Builder Units list (%d): %s"
      % (len(_brit), _brit))
check("BRITONS' Builder Units omits at least 10 buildable buildings",
      len(_brit) >= 10, "missing %d" % len(_brit))
check("that missing set includes the Barracks, House, Mill and Lumber Camp",
      {12, 70, 68, 562} <= set(_brit), "missing=%s" % _brit)

print()
print("BUILDER BLOCK: the Builder's `Units` list is much smaller than the tree's")
print("  building set, so that list alone is not the villager build menu.  But the")
print("  basics ARE in the panel, as their own blocks -- see test_panel_shape.py.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)

