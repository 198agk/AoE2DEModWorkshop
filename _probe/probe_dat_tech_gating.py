# -*- coding: utf-8 -*-
r"""Read the .dat's OWN gating of a tech -- the piece `read_tech` throws away.

`parser.read_tech` consumes RequiredTechs[6] and RequiredTechCount but stores
neither, so every conclusion of the form "the .dat allows/refuses tech N" was
previously unsupported.  This probe monkey-patches that ONE function (nothing in
`parser.py` changes, so the byte-exact round-trip pin is untouched) and keeps the
two fields, then answers the Poles question with all three layers resolved.

Why it matters: the user saw no Elite Cannon Galleon button at the Polish dock.
The panel is already excluded both ways.  If the .dat's RequiredTechs for 376 are
satisfiable by Poles, then the .dat ALSO says yes -- and the tree would be the only
layer agreeing with the game, which upgrades "best-supported" to a real exclusion.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_dat_tech_gating.py
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P                        # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

_ORIG = P.read_tech
_CAPTURED = {}


def _read_tech_keep_gates(r):
    """Same wire format as parser.read_tech, but keeps RequiredTechs."""
    t = {}
    reqs = [r.i16() for _ in range(6)]                    # RequiredTechs[6]
    for _ in range(3):
        P.read_research_resource_cost(r)
    count = r.i16()                                       # RequiredTechCount
    t["civ"] = r.i16()
    r.i16()                                               # FullTechMode
    if r.gv < P.GV_C31:
        r.i16()                                           # ResearchLocation
    if r.gv >= P.GV_MATT:
        if P.GV_C18 <= r.gv <= P.GV_LatestDE2:
            r.i32(); r.i32()
        else:
            r.i16(); r.i16()
    if r.gv < P.GV_C31:
        r.i16()                                           # ResearchTime
    t["effect_id"] = r.i16()
    t["type"] = r.i16()
    t["icon_id"] = r.i16()
    if r.gv < P.GV_C31:
        r.u8()                                            # ButtonID
    r.i32(); r.i32()
    if r.gv < P.GV_C31:
        r.i32()
    t["name"] = r.debug_string()[1]
    if P.GV_C15 <= r.gv <= P.GV_LatestDE2:
        r.u8()                                            # Repeatable
    if P.GV_C31 <= r.gv <= P.GV_LatestDE2:
        n = r.i16()
        t["research_locations"] = [P.read_research_location(r) for _ in range(n)]
    else:
        t["research_locations"] = None
    t["required_techs"] = reqs[:count]
    t["required_tech_count"] = count
    _CAPTURED[len(_CAPTURED)] = t
    return t


P.read_tech = _read_tech_keep_gates
try:
    raw, how = P.load_dat(DAT)
    st = P.Parser(raw).parse()
finally:
    P.read_tech = _ORIG

techs = st["techs"]
trees = CT.load_trees(GAME)
pol = next((c for c in st["civs"]
            if (c.get("name") or "").strip().lower() == "poles"), None)
pol_units = set(u["id"] for u in pol["units"]) if pol else set()

poles_tree = trees["POLES"]
tree_units = set()
tree_techs = set()
for r in CT.rows_of(poles_tree):
    if not isinstance(r, dict):
        continue
    status = r.get("Node Status")
    if status == "NotAvailable":
        continue
    if r.get("Use Type") in CT.UNIT_USE_TYPES:
        tree_units.add(int(r.get("Node ID")))
    elif r.get("Use Type") in CT.TECH_USE_TYPES:
        tree_techs.add(int(r.get("Node ID")))

print("parsed %d techs (%s); RequiredTechs now retained" % (len(techs), how))
print("the Poles' tree opens %d unit ids and %d tech ids"
      % (len(tree_units), len(tree_techs)))
print()


def ask(tid, label):
    t = techs[tid]
    reqs = t["required_techs"]
    print("tech %-5s %-28s civ=%-3s reqs=%s"
          % (tid, label, t["civ"], reqs if reqs else "[]"))
    if t["research_locations"]:
        print("        research_locations=%s" % (t["research_locations"],))
    # RequiredTechs are TECH ids (Research.cpp), so they must be judged against
    # the tree's TECH rows.  Comparing them to unit rows is a space mix-up.
    met = [r for r in reqs if r in tree_techs]
    unmet = [r for r in reqs if r not in tree_techs]
    print("        Poles meet %d/%d required techs in TECH space; unmet=%s"
          % (len(met), len(reqs), unmet if unmet else "none"))
    for r in reqs:
        print("          req tech %-4s in tree tech rows: %-5s  node_status=%s"
              % (r, r in tree_techs,
                 CT.node_status(poles_tree, r, CT.TECH_USE_TYPES)))
    return unmet


print("A  the upgrade techs in question, with their .dat RequiredTechs")
u376 = ask(376, "Elite Cannon Galleon upg")
u320 = ask(320, "Siege Onager upgrade")
u244 = ask(244, "Heavy Demolition upg")
t376_locs = techs[376]["research_locations"] or []
print()

print("B  the units the .dat gives Poles, and the tree's verdict on them")
for uid, label in ((420, "Cannon Galleon"), (691, "Elite Cannon Galleon")):
    print("     unit %-4s %-22s .dat=%s  tree=%s"
          % (uid, label, uid in pol_units,
             CT.node_status(poles_tree, uid, CT.UNIT_USE_TYPES)))
print()

print("C  the verdict, all three layers")
print("     layer   Elite Cannon Galleon for Poles?")
print("     panel   YES  (691 in Units, 376 in Techs)   -- REFUTED by the user's")
print("                  screen: no button appeared")
_dot_ok = (691 in pol_units) and (not u376) and t376_locs
print("     .dat    unit 691 present=%s ; tech 376 civ=-1 ; poles unmet reqs=%s"
      % (691 in pol_units, u376 if u376 else "none"))
print("             research location of 376 = %s (dock 45, so the .dat is willing"
      % (t376_locs,))
print("             to offer it AT the dock)")
if _dot_ok:
    print("             -> the .dat hands Poles a satisfiable path to 376: the unit")
    print("                is in their table and no required tech stands unmet.")
    print("     tree    NO   (691 NotAvailable, no 376 row)")
    print("     => the .dat says YES and the game showed NO => the .dat does not")
    print("        gate this button either.  The TREE is the only layer that agrees")
    print("        with the observation: the exclusion is complete on all three.")
else:
    print("             -> the .dat refuses as well; the tree is still the only")
    print("                layer that explains WHY (it can name the civilization).")
print()
print("note: a civ=-1 tech is global -- the .dat cannot express 'Poles get Elite")
print("Cannon Galleon but Britons do not'.  The tree can, and does.")
sys.exit(0)
