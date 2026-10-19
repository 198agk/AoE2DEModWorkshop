# -*- coding: utf-8 -*-
r"""Close the Poles case: what do the three layers each say, and which one is refuted?

The user looked at the Polish dock in the shipped game (2026-10-18) and reports:

    there is NO Elite Cannon Galleon upgrade button.

That kills any layer that says YES.  This probe prints the three answers side by
side, using only facts read from shipped files, plus one correction to earlier
scripts: `read_tech` stores no id (tech ids ARE array indices), and it does not
parse RequiredTechs -- so "the tree has no row for 376" is not the same claim as
"the .dat refuses 376".

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_poles_verdict.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.game import buildpanel as BP                 # noqa: E402
from aoe2mod.dat import parser as P                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
raw, how = P.load_dat(DAT)
st = P.Parser(raw).parse()

pol = None
for c in st["civs"]:
    if (c.get("name") or "").strip().lower() == "poles":
        pol = c
        break

print("=" * 78)
print("THE OBSERVATION: Poles, dock, shipped game -> no Elite Cannon Galleon button.")
print("=" * 78)
print()

print("1  TREE  CivTechTrees/POLES.json")
tree = trees["POLES"]
u691 = [r for r in CT.rows_of(tree)
        if isinstance(r, dict) and r.get("Use Type") in CT.UNIT_USE_TYPES
        and _int(r.get("Node ID")) == 691]
t376 = [r for r in CT.rows_of(tree)
        if isinstance(r, dict) and _int(r.get("Node ID")) == 376]
print("     unit 691 row: %s" % ([(r.get("Name"), r.get("Node Status"))
                                for r in u691] or "ABSENT"))
print("     tech 376 row: %s" % ([(r.get("Name"), r.get("Use Type"))
                                for r in t376] or "ABSENT"))
print("     -> the tree says NO (twice over: the unit is NotAvailable and the")
print("        upgrade tech has no row at all)")
print()

print("2  PANEL  futuravailableunits.json / Poles / Dock(45)")
pk = BP.civ_key_for(panels, "POLES")
blk = BP.building_block(panels[pk]["obj"], pk, 45)
pu = {_int(e.get("ID")): e for e in (blk.get("Units") or [])}
pt = {_int(e.get("ID")): e for e in (blk.get("Techs") or [])}
print("     unit 691 in Units: %s  %s" % (691 in pu,
                                         pu.get(691, {}).get("Name")))
print("     tech 376 in Techs: %s  %s" % (376 in pt,
                                         pt.get(376, {}).get("Name")))
print("     -> the panel says YES (twice over: unit and upgrade tech both listed)")
print()

print("3  .DAT   empires2_x2_p1.dat")
ids = set(u["id"] for u in pol["units"])
print("     Poles' unit table contains 691: %s" % (691 in ids))
print("     Poles' unit table contains 420: %s" % (420 in ids))
tt = st["techs"][376] if len(st["techs"]) > 376 else None
print("     tech 376 record: %s" % (None if tt is None
                                    else {"civ": tt.get("civ"),
                                          "name": tt.get("name"),
                                          "research_locations":
                                              tt.get("research_locations")}))
print("     NOTE: read_tech() does not retain RequiredTechs, so the .dat's own")
print("     gating for 376 is NOT resolved here -- it is a wide-open question.")
print()

print("=" * 78)
print("WHAT THIS BUYS")
print("  * The panel is REFUTED as the source of the dock's button set: it lists")
print("    both the unit and its upgrade tech, and the user saw neither.")
print("  * The tree is CONSISTENT with the observation.")
print("  * The .dat is unresolved (it has the unit; its tech gating is unparsed),")
print("    so 'the menu reads the tree' is the best-supported hypothesis rather")
print("    than a proof -- the .dat could still be the real gate.")
print("=" * 78)
sys.exit(0)
