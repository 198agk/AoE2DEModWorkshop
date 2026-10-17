# -*- coding: utf-8 -*-
r"""GAME 2's own completeness: does the TREE supply 588's upgrade path?

The Round 49 fix established the criterion "the layer that promises the unit must
supply a COMPLETE path".  For GAME 1 the promising layer is the panel, and the
panel has tech 429 -- good.

For GAME 2 the promising layer is the TREE (Sicilians' tree says 588
`ResearchedCompleted`).  But `probe_gate_sweep.py` printed

    tree upgrade tech : None        <- `node_status(tree, 320, TECH)` is None

i.e. Sicilians' tree has NO tech row for 320, the Siege Onager research.  If the
engine needs that research, Siege Onager may be unreachable even when the tree
drives the menu -- the SAME failure I just fixed on the other side.

Check how the upgrade tech is represented for every civ whose tree grants 588, and
whether GAME 2 needs a different subject.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

print("A  Sicilians' tree: is tech 588's upgrade (320) present in ANY form?")
sc = trees["SICILIANS"]
for tid in (320, 257, 255, 96):
    print("   tech %-5s unit-space=%r tech-space=%r row=%s"
          % (tid, CT.node_status(sc, tid, CT.UNIT_USE_TYPES),
             CT.node_status(sc, tid, CT.TECH_USE_TYPES),
             "yes" if CT.row_for(sc, tid, CT.TECH_USE_TYPES) else "NO"))

print()
print("B  Sicilians' tree rows at building 49 (Siege Workshop)")
for r in sorted(CT.unit_rows(sc), key=lambda r: r.get("Node ID") or 0):
    if r.get("Building ID") == 49:
        print("   unit %-6s %-22s status=%-18s age=%s trigTech=%r"
              % (r.get("Node ID"), r.get("Name"), r.get("Node Status"),
                 r.get("Age ID"), r.get("Trigger Tech ID")))

print()
print("C  every civ whose tree grants 588 -- does it also have tech 320?")
grant = []
for stem, tree in sorted(trees.items()):
    if CT.node_status(tree, 588, CT.UNIT_USE_TYPES) == "ResearchedCompleted":
        t320 = CT.node_status(tree, 320, CT.TECH_USE_TYPES)
        grant.append((stem, t320))
print("   civs granting 588         : %d" % len(grant))
print("   of those with tech 320    : %d"
      % sum(1 for _s, t in grant if t is not None))
print("   distribution of t320 value: %s" % Counter(t for _s, t in grant))
for stem, t in grant:
    print("      %-13s tech320=%r" % (stem, t))

print()
print("D  what does the PANEL say for those same civs about 320?")
for stem, _t in grant[:8]:
    # find the display name for this stem
    disp = None
    for d in sorted(panels):
        if CT.civ_file_stem(d) == stem:
            disp = d
            break
    if disp is None:
        print("      %-13s (no panel entry)" % stem)
        continue
    o = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    techs = {e.get("ID") for blk in BP.buildings(o, disp)
             for e in (blk.get(BP.TECHS_KEY) or [])}
    units = {e.get("ID") for blk in BP.buildings(o, disp)
             for e in (blk.get(BP.UNITS_KEY) or [])}
    print("      %-13s panel: 588 in Units=%s  320 in Techs=%s"
          % (stem, 588 in units, 320 in techs))

print()
print("E  verdict input: if the TREE grants 588 but lacks tech 320, is 588")
print("   reachable when the tree drives?  Look at civs where the panel is NOT")
print("   silent, as a control for what a complete path looks like.")
import aoe2mod.api as A                                    # noqa: E402
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
# the .dat side: does 588 have a train location, and does any tech unlock it?
print("   (see section F below)")
print()
print("F  the .dat's own view: which techs reference unit 588?")
eff = tk._effect_records()
hits = []
for rec in eff:
    for c in rec.get("commands") or []:
        if c.get("type") == 2 and c.get("a") == 588:
            hits.append((rec.get("index"), rec.get("name"), c.get("a"),
                         c.get("b")))
print("   effect commands of type 2 (enable/disable unit) naming 588: %d" % len(hits))
for h in hits:
    print("      effect %-6s %-30s a=%s b=%s" % h)
