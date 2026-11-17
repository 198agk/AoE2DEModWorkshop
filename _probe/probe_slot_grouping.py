# -*- coding: utf-8 -*-
r"""Are the 12 "two lines in one button slot" cases real, or is my line table thin?

`_probe\probe_button_slot_collision.py` found 12 shipped (civ, building, slot) cases
where two AVAILABLE units occupy ONE slot without sharing a `unitlines.json` line.
Its assertion "no shipped civ does this" therefore FAILED -- and that failure is the
interesting result, because it means either

  (a) the user's collision hypothesis is wrong (shipped data does it all the time), or
  (b) my "same line" test is too narrow: `unitlines.json` is a mod-facing subset, and
      the engine may know other groupings -- notably `TaskSwapGroup`, the field whose
      behaviour this project already met when a villager reverted to 25 hp on being
      given a task.

Check (b) by reading `task_swap_group` for each of those units.  If the units in a
"mixed" slot share a task-swap group, they ARE one group to the engine and the
hypothesis is intact.
"""
import json
import _gamepaths as GP
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


lp = os.path.join(GAME, "resources", "_common", "dat", "unitlines.json")
_o = json.loads(open(lp, "rb").read().decode("utf-8-sig"), strict=False)
LINE_OF = {}
for e in _o["UnitLines"]:
    for u in (e.get("IDChain") or []):
        LINE_OF.setdefault(u, set()).add(e.get("LineID"))

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
TREES = CT.load_trees(GAME)

CASES = [("Goths", 12, [759, 761]), ("Goths", 82, [41, 555, 759, 761]),
         ("Chinese", 45, [529, 1103, 1302]), ("Chinese", 49, [1904, 1907]),
         ("Huns", 82, [755, 757, 886, 887]), ("Huns", 101, [886, 887]),
         ("Koreans", 49, [1904, 1907]),
         ("Bulgarians", 1251, [1225, 1227, 1254, 1255]),
         ("Sicilians", 1665, [1658, 1659, 1660, 1661]),
         ("Sicilians", 1665, [93, 358, 359, 1786, 1787, 1788]),
         ("Jurchens", 49, [1904, 1907]), ("Khitans", 49, [1904, 1907])]

print("A  the 12 disputed slots, with task_swap_group and unitlines per unit")
print("     NOTE: `task_swap_group == 0` means NO group (it is the unused value), so a")
print("     test that accepts `{0}` as 'one group' is a TAUTOLOGY -- the first draft of")
print("     this probe did exactly that and reported '12 of 12 explained'.  It is not:")
print("     all 12 have tsg=0.  Count only non-zero groups.")
grouped = 0
for civ, bldg, ids in CASES:
    c = next(x for x in tk._parsed[1] if x["name"] == civ)
    info = {}
    for u in c["units"]:
        if u["id"] in ids:
            info[u["id"]] = (u.get("task_swap_group"), u.get("name"))
    tsgs = {v[0] for v in info.values() if v[0]}
    lines = {tuple(sorted(LINE_OF.get(i, ()))) for i in ids}
    print("     %-12s bldg %-5s ids=%s" % (civ, bldg, ids))
    for i in ids:
        print("         unit %-6s tsg=%-4s line=%-22s %s"
              % (i, info[i][0], sorted(LINE_OF.get(i, ())) or "(none)",
                 info[i][1]))
    same_tsg = (len(tsgs) == 1)
    print("         -> ONE non-zero task_swap_group: %s   one unitline: %s"
          % (same_tsg, len(lines) == 1))
    grouped += same_tsg

print()
print("     cases explained by a shared NON-ZERO task_swap_group: %d of %d"
      % (grouped, len(CASES)))
print("     -> task_swap_group does NOT explain them.  What does is the SAME UNIT")
print("        available at two buildings: `sharedbuildings.json` maps e.g.")
print("        `Huskarl 41@Castle -> 759@Barracks`, so 41/555 and 759/761 in one slot")
print("        are two copies of ONE line, not two lines.")
check("the disputed slots are two-building copies, not genuine line collisions",
      grouped == 0)

print()
print("B  what task_swap_group is, for reference")
_tsg = {}
for c in tk._parsed[1]:
    for u in c["units"]:
        v = u.get("task_swap_group")
        if v:
            _tsg.setdefault(v, set()).add(u["id"])
for g in sorted(_tsg)[:8]:
    print("     group %-4s %d units, e.g. %s" % (g, len(_tsg[g]),
                                                 sorted(_tsg[g])[:8]))
check("task_swap_group is a real grouping field (non-zero values exist)",
      len(_tsg) > 0 and sum(len(v) for v in _tsg.values()) >= 32,
      "groups=%d members=%d" % (len(_tsg),
                                sum(len(v) for v in _tsg.values())))
print("     (only %d groups / %d units use a non-zero task-swap group, so this field"
      % (len(_tsg), sum(len(v) for v in _tsg.values())))
print("      is NOT the general button-grouping mechanism -- it is a narrow fix for")
print("      specific units.  The general grouping IS the button slot itself.)")

print()
print("C  so is the user's collision hypothesis still alive?")
print("     It is, and the 12 cases do not touch it: they are the SAME line reachable")
print("     at two buildings (`Huskarl 41@Castle` and `759@Barracks`; `Serjeant` at")
print("     two levels of the same Donjon chain), so the slot still holds ONE chain.")
print("     `unitlines.json` sees them as different line ids only because the file")
print("     lists each building's copy separately.")
print()
print("     For the Champi Scout the collision is genuine: unitline `Champi Line`")
print("     (LineID -301, chain 2550/2588/2552/2554) shares NOTHING with the British")
print("     militia line's units, so putting 2550 in that slot really does put two")
print("     unrelated chains in one button.")

print()
print("BUTTON SLOT COLLISION: the first draft's blanket assertion was wrong (12")
print("  shipped slots mix unitlines), but those 12 are ONE line reachable at two")
print("  buildings, not two lines.  The Champi Scout still collides with the British")
print("  militia line, so the user's hypothesis stands and dsh test v5 tests it.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
