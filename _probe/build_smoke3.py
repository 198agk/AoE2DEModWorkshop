r"""Build the CORRECTED single-variable smoke test.

Why the previous test proved nothing
------------------------------------
The last mod granted Hand Cannoneer (unit 5) to the Britons and the archery
range did not list it.  But Hand Cannoneer's row carries ``RequiredAge: 4``
(Imperial Age) -- the shipped panel says so for the Turks, who really do have
it.  A game that starts in the Dark Age cannot show an Imperial-Age unit in a
building menu no matter which file the menu is read from.  So that test had a
confound and settles nothing.

This build removes the confound:
  * target unit = Champi Scout (id 2550), ``RequiredAge: 1`` (Dark Age) and
    ``Building ID: 12`` (Barracks).  It exists today only in Incas / Mapuche /
    Muisca / Tupi, so granting it to the Britons is a real change.
  * positive control = villager hit points -> 1000, a ``.dat`` edit that the
    user has already seen work twice.  If the villagers show 1000, the mod
    loaded; if the British barracks still has no Champi Scout, the panel file
    is what failed -- not the installation.

Usage:
    $env:PYTHONPATH='D:\Software\DeepSeek Harness\工作区2'
    & $py _probe\build_smoke3.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_smoke3")

TITLE = "aoe2mod Smoke3 Panel Champi"
INTENTS = [
    {"intent": "unit.stat", "unit": "Villager", "stat": "hit_points", "value": 1000},
    {"intent": "unit.availability", "unit": 2550, "civ": "British", "action": "grant"},
]


def main():
    tk = A.open_toolkit()
    print("game root : %s" % tk.game_root)

    # --- what the game ships, before we touch anything ---------------------
    trees = tk._trees()
    main_path, paphos_path = BP.panel_paths(tk.game_root)
    _t, shipped = BP.load_panel(main_path)
    print("panel     : %s (%d B)" % (main_path, os.path.getsize(main_path)))
    print("  shipped Britons Barracks(12) lists 2550: %s"
          % BP.find_entry(shipped, "Britons", 2550, BP.UNITS_KEY)[1])
    row = None
    for r in CT.unit_rows(trees["BRITONS"]):
        if r.get("Node ID") == 2550:
            row = r
    print("  shipped BRITONS tree row for 2550: %s" % (row,))
    print("  shipped INCAS   tree row for 2550: %s"
          % [r for r in CT.unit_rows(trees["INCAS"]) if r.get("Node ID") == 2550])

    # --- plan, then build --------------------------------------------------
    plan = tk.plan_bundle(INTENTS)
    print("  plan keys: %s" % sorted(plan.keys()))
    for d in plan.get("descriptions", []):
        print("      %s" % d)
    print("  edit_count=%s  overlap_count=%s  civs_edited=%s"
          % (plan.get("edit_count"), plan.get("overlap_count"), plan.get("civs_edited")))

    man = tk.build_bundle(INTENTS, OUT, title=TITLE, author="aoe2mod probe",
                          overwrite=True)
    print()
    print("built -> %s" % OUT)
    print("  files: %s" % json.dumps(man.get("files", man), ensure_ascii=False)[:400])

    # --- verify the two halves independently ------------------------------
    dat_rel = os.path.join("resources", "_common", "dat")
    panel_out = os.path.join(OUT, dat_rel, "futuravailableunits.json")
    tree_out = os.path.join(OUT, dat_rel, "CivTechTrees", "BRITONS.json")

    print()
    print("== the panel half ==")
    if os.path.exists(panel_out):
        _t2, edited = BP.load_panel(panel_out)
        found = BP.find_entry(edited, "Britons", 2550, BP.UNITS_KEY)
        print("  size %d B (shipped %d B)"
              % (os.path.getsize(panel_out), os.path.getsize(main_path)))
        print("  Britons lists 2550 now: %s   at building %s  entry %s"
              % (found[1] is not None, found[0], found[1]))
        b12 = BP.building_block(edited, "Britons", 12)
        if b12:
            print("  Britons Barracks(12) Units: %s"
                  % [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
                     for e in b12.get("Units", [])])
        # surgery check: everything outside the insert must be untouched
        btxt = open(panel_out, "rb").read().decode("utf-8-sig")
        stxt = open(main_path, "rb").read().decode("utf-8-sig")
        ok, info = BP.verify_surgical(stxt, btxt)
        print("  surgical: %s %s" % (ok, info))
        # other civs must be byte-identical
        print("  Incas still lists 2550: %s"
              % (BP.find_entry(edited, "Incas", 2550, BP.UNITS_KEY)[1] is not None))
    else:
        print("  MISSING: %s" % panel_out)

    print()
    print("== the tree half ==")
    if os.path.exists(tree_out):
        _t3, obj = BP.load_panel(tree_out)
        r = None
        for x in obj.get("civ_techs_units", []):
            if x.get("Node ID") == 2550:
                r = x
        print("  size %d B" % os.path.getsize(tree_out))
        print("  BRITONS tree row for 2550 now: %s" % (r,))
        print("  can_build(2550): %s" % CT.can_build(obj, 2550))
    else:
        print("  MISSING: %s" % tree_out)

    print()
    print("== the .dat half (positive control) ==")
    dat_out = os.path.join(OUT, dat_rel, "empires2_x2_p1.dat")
    print("  %s  %d B" % (dat_out, os.path.getsize(dat_out) if os.path.exists(dat_out) else -1))

    print()
    print("SMOKE3 BUILD: the mod carries a dark-age unit into the British barracks,")
    print("so no age gate can hide the result.  The villager HP is the control.")


if __name__ == "__main__":
    main()
