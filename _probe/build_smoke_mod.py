# -*- coding: utf-8 -*-
"""Build the mod that answers the LAST unverified question.

⚠ HISTORICAL (2026-10-19): this script builds the `smoke5` experiment, which the
audit team judged AMBIGUOUS and which was uninstalled.  Both questions below
have since been answered, and NOT in the direction this file assumed:

  * the CivTechTrees/<CIV>.json override IS read by the engine, but it does NOT
    drive the build menu (2026-10-19 `dsh test v15`: two tree files over a
    byte-identical `.dat`, engine logged loading the mod, menu did not move);
  * the task-swap family fix WAS confirmed in game -- the user reported "都是羊了"
    for `dsh test v12`;
  * and the lever that actually moves the build menu is a `.dat` `type 2`
    Enable/Disable Unit command on a technology the civilization owns
    (`dsh test v7` grant, `dsh test v17` revoke).

Kept as a record of the experiment design.  Do not re-run it expecting a verdict.

Two things this project had never observed when the file was written:

  1. a CivTechTrees/<CIV>.json override -- no mod on this machine has ever
     shipped one, so "the engine reads that file" is a measurement, not a
     sighting;
  2. the task-swap family fix -- the user saw villager HP revert on reassignment
     BEFORE the fix (id 83 alone was written while the engine re-pointed the
     object at id 293 / another篮 member).  The fix writes all 27 members.

So this mod deliberately carries BOTH, through the mixed-strategy bundle path:

  * `.dat`  : Villager hit points -> 1000 (every civ, whole swap family)
  * JSON    : Britons may build  Champi Scout (add_row, Dark Age, Barracks)
              Britons may build  Hand Cannoneer (set_status, NotAvailable ->
                                  available; Imperial, Archery Range)

The two checks are independent: if HP holds on reassignment the .dat half works,
if the units appear in the right buildings the tree half works.  A failure tells
us WHICH half, because the halves are different files.

Writes only to the workspace.  Installing is a separate, reversible step.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402
from aoe2mod.game import civtechtrees as CT                    # noqa: E402

OUT = os.path.join(HERE, "out_smoke")
TITLE = "aoe2mod smoke villager HP + Britons units"

INTENTS = [
    # The .dat half: 4x HP so it cannot be mistaken for the base value, applied
    # to the whole task-swap family so reassignment cannot find a 25 HP record.
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 1000},
    # The JSON half, add_row: nothing in the Britons tree mentions this unit.
    {"intent": "unit.availability", "unit": 2550, "civ": "British",
     "action": "grant"},
    # The JSON half, set_status: Britons DOES list this one, as NotAvailable.
    {"intent": "unit.availability", "unit": 5, "civ": "British",
     "action": "grant"},
]


def main():
    tk = A.open_toolkit()
    tk._ensure()
    print("game root : %s" % tk.game_root)
    print()

    plans = [tk.plan(i) for i in INTENTS]
    for p in plans:
        print("  %-58s  edits=%-5s civs=%-3s mode=%s"
              % (p["description"][:58], p.get("edit_count"),
                 p.get("civ_count"), p.get("mode", "-")))
        if p.get("variants"):
            print("      family covers %d records: %s"
                  % (len(p["unit_ids"]), p["unit_ids"][:12]))
        if p.get("warnings"):
            for w in p["warnings"]:
                print("      warn: %s" % w)
    print()

    man = tk.build_bundle(INTENTS, OUT, title=TITLE,
                          author="aoe2mod smoke test",
                          description="Probe: does the game read CivTechTrees?",
                          overwrite=True)
    print("built     : %s" % man.get("dir", OUT))
    print("dat       : %s (%d B)" % (man.get("dat"), man.get("dat_bytes") or 0))
    print("json      : %s" % (man.get("json_overrides"),))
    print("reparse   : ok=%s leftover=%s"
          % (man.get("reparse_ok"), man.get("reparse_leftover")))
    print()

    # Read the emitted files back the way the engine will.
    tree_path = os.path.join(OUT, "resources", "_common", "dat", "CivTechTrees",
                             "BRITONS.json")
    if not os.path.isfile(tree_path):
        print("!! the tree file was not emitted at the engine's path")
        return 1
    back = CT.load_trees(OUT)["BRITONS"]
    print("read back the emitted BRITONS.json through the engine's own path:")
    print("   Champi Scout (2550)  can_build=%s  status=%s"
          % (CT.can_build(back, 2550), CT.node_status(back, 2550)))
    print("   Hand Cannoneer (5)   can_build=%s  status=%s"
          % (CT.can_build(back, 5), CT.node_status(back, 5)))
    print("   unit rows %d (was %d)  tech rows %d"
          % (len(CT.unit_rows(back)),
             len(CT.unit_rows(tk._trees()["BRITONS"])), len(CT.tech_rows(back))))

    dats = []
    for r, _d, f in os.walk(OUT):
        dats += [os.path.join(r, x) for x in f if x.endswith(".dat")]
    print("   .dat files in the mod: %d" % len(dats))
    print()
    print("MANIFEST")
    print(json.dumps({k: v for k, v in man.items()
                      if k in ("title", "dat", "json_overrides",
                               "mod_contains_dat", "verification")},
                     ensure_ascii=False, indent=1)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
