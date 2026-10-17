# -*- coding: utf-8 -*-
r"""READ THE RESULT of the two-game experiment from the user's screenshots.

GAME 2 (Sicilians / siege workshop) -- screenshots 3 and 4 show, IN GAME:
    shot 3: '升级到重型投石车（价格：1450食物，1000黄金）将您的中型投石车升级...'
            = the UPGRADE button for tech 320 (Onager -> Siege Onager), hotkey S
    shot 4: '建造重型投石车（价格：160木，135金）...（热键：W）'
            = the UNIT button for unit 588, i.e. the state after the upgrade

Meanwhile `futuravailableunits.json` for SICILIANS / building 49 lists NEITHER 588
nor 320, while `CivTechTrees/SICILIANS.json` grants 588 `ResearchedCompleted`.

So the build menu showed something the panel file never mentions.

Also test the competing explanation for the file's name and shape: that
`futuravailableunits.json` feeds the GREYED-OUT "future items" display, which is
exactly what `EnableFutureItemsDisplay` (IDS_OPT_DISPLAY_FUTURE_ITEMS) toggles --
and which would explain why it lists units the tree refuses.

Verify:
  A  the two files' positions on the subject units, as a table.
  B  what the option strings say (so the "grey preview" explanation is on record).
  C  whether the '升级到精锐炮舰' line the user saw on the POLES dock is a STATIC
     unit description (civ-independent) rather than proof the upgrade is offered.
"""
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

print("=" * 78)
print("A  THE RESULT TABLE")
print("=" * 78)
ROWS = [
    ("GAME 1", "POLES", "Poles", 45, "Dock",
     [("420 Cannon Galleon", 420), ("691 Elite Cannon Galleon", 691)], None),
    ("GAME 2", "SICILIANS", "Sicilians", 49, "Siege Workshop",
     [("550 Onager", 550), ("588 Siege Onager", 588)], 320),
]
for tag, stem, disp, bid, bname, units, upgrade_tech in ROWS:
    t = trees[stem]
    o = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    pu, pt = set(), set()
    for blk in BP.buildings(o, disp):
        if blk.get("ID") == bid:
            pu = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
            pt = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
    print()
    print("  %s  %s / %s (%s %s)" % (tag, stem, disp, bid, bname))
    print("     %-30s %-22s %s" % ("subject", "TREE says", "PANEL says"))
    for label, uid in units:
        st = CT.node_status(t, uid, CT.UNIT_USE_TYPES)
        print("     %-30s %-22s %s"
              % (label, st, "listed in Units" if uid in pu else "SILENT"))
    if upgrade_tech:
        st = CT.node_status(t, upgrade_tech, CT.TECH_USE_TYPES)
        print("     %-30s %-22s %s"
              % ("tech %d (the upgrade)" % upgrade_tech, st or "no tree row",
                 "listed in Techs" if upgrade_tech in pt else "SILENT"))
    print("     tree rows at this building : %d"
          % sum(1 for r in CT.unit_rows(t) if r.get("Building ID") == bid))
    print("     panel Units at this building: %d" % len(pu))

print()
print("=" * 78)
print("B  the 'future items' option -- the competing explanation for the file")
print("=" * 78)
LANG = {}
kd = os.path.join(GAME, "resources", "zh", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        for line in open(os.path.join(kd, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if v.startswith('"') and v.endswith('"'):
                LANG[k.strip()] = v[1:-1]
for key in ("IDS_OPT_DISPLAY_FUTURE_ITEMS", "IDS_OPT_DISPLAY_FUTURE_ITEMS_HELP_TEXT"):
    print("   %-40s %r" % (key, LANG.get(key)))

print()
print("=" * 78)
print("C  is the '升级到精锐炮舰' line the user saw a STATIC unit description?")
print("=" * 78)
# The tooltip the user hovered was for unit 420 (Cannon Galleon).  In AoE2 the
# unit tooltip's '升级：...' lines come from the unit's own help string, so they are
# the same for every civilization that can build the unit -- they do NOT prove the
# civ may research the upgrade.
enk = os.path.join(GAME, "resources", "en", "strings", "key-value")
EN = {}
for fn in sorted(os.listdir(enk)):
    if fn.endswith(".txt"):
        for line in open(os.path.join(enk, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if v.startswith('"') and v.endswith('"'):
                EN[k.strip()] = v[1:-1]
hits = [(k, v) for k, v in LANG.items()
        if isinstance(v, str) and "精锐炮舰" in v and len(v) < 400]
print("   zh strings mentioning 精锐炮舰 (Elite Cannon Galleon): %d" % len(hits))
for k, v in hits[:8]:
    print("      %-8s %r" % (k, v[:150]))
hits2 = [(k, v) for k, v in EN.items()
         if isinstance(v, str) and "Elite Cannon Galleon" in v and len(v) < 400]
print("   en strings mentioning it: %d" % len(hits2))
for k, v in hits2[:8]:
    print("      %-8s %r" % (k, v[:150]))

print()
print("=" * 78)
print("VERDICT")
print("=" * 78)
_sic_t = CT.node_status(trees["SICILIANS"], 588, CT.UNIT_USE_TYPES)
_sic_o = panels[BP.panel_path_for(GAME, "Sicilians")[1]]["obj"]
_pu = {e.get("ID") for blk in BP.buildings(_sic_o, "Sicilians")
       if blk.get("ID") == 49 for e in (blk.get(BP.UNITS_KEY) or [])}
_pt = {e.get("ID") for blk in BP.buildings(_sic_o, "Sicilians")
       if blk.get("ID") == 49 for e in (blk.get(BP.TECHS_KEY) or [])}
print("   GAME 2 observed : the siege workshop OFFERS the upgrade to 重型投石车")
print("   tree says       : %s" % _sic_t)
print("   panel says      : 588 in Units=%s   320 in Techs=%s" % (588 in _pu,
                                                                320 in _pt))
print()
print("   -> the menu is NOT fed by futuravailableunits.json alone.")
print("      The layer that said 'yes' (the tree) is the one that showed up.")
