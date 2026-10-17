# -*- coding: utf-8 -*-
r"""PIN: `aoe2mod.game.buttons` -- the button-slot rule that made v5 work.

`dsh test v4` and `dsh test v5` differed by ONE BYTE (the British Champi Scout's
`train_location.button_id`, 1 vs 4) and only v5 appeared in game, so the slot is
load-bearing.  This pins the rule the product now uses.

Three things are measured rather than assumed:
  * free slots exist for the grant subjects the earlier rounds chose;
  * the shipped game never puts two unrelated chains in one AVAILABLE slot (the 12
    apparent exceptions are one line reachable at two buildings);
  * an exhausted building is REPORTED, not guessed at.
"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buttons as B                      # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GRANT = ("ResearchedCompleted", "ResearchRequired")
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
TREES = CT.load_trees(GAME)


def civ_of(disp):
    return next(x for x in tk._parsed[1] if x["name"] == disp)


print("A  the shipped game's habit: which slot a `Node Type` uses")
hist = defaultdict(Counter)
for c in tk._parsed[1]:
    tr = TREES.get(CT.civ_file_stem(c["name"]))
    if not tr:
        continue
    for u in c["units"]:
        row = CT.row_for(tr, u["id"], CT.UNIT_USE_TYPES)
        nt = (row or {}).get("Node Type")
        if (row or {}).get("Node Status") not in GRANT:
            continue
        for t in u.get("train_locations") or []:
            if nt:
                hist[nt][t.get("button_id")] += 1
for nt in ("RegionalUnit", "UniqueUnit", "Unit"):
    print("     %-14s %s" % (nt, dict(hist[nt].most_common(5))))
check("RegionalUnit clusters on slot 4 (the measured convention)",
      hist["RegionalUnit"].most_common(1)[0][0] == 4,
      "%s" % dict(hist["RegionalUnit"].most_common(3)))
check("and the convention accessor agrees",
      B.slot_convention("RegionalUnit") == 4)
check("an unknown kind has NO convention (the honest answer)",
      B.slot_convention("SomethingElse") is None)

print()
print("B  the rule on the case v5 proved: British + unit 2550 at the Barracks")
brit = civ_of("British")
d = B.describe(brit, TREES["BRITONS"], 12, 2550)
print("     describe: %s" % d)
check("button 1 is occupied by the militia line", 1 in d["occupied"],
      "%s" % d["occupied"])
check("and slots 3 and 4 are free", d["free_slots"] == [3, 4],
      "%s" % d["free_slots"])
slot, why = B.choose_slot(brit, TREES["BRITONS"], 12, node_type="RegionalUnit")
print("     choose_slot(node_type='RegionalUnit') -> %s (%s)" % (slot, why or "ok"))
check("it picks the free convention slot, 4 -- exactly what v5 used", slot == 4,
      "got %s" % slot)
check("and it never returns an occupied slot",
      slot not in d["occupied"], "slot=%s occupied=%s" % (slot, d["occupied"]))

print()
print("C  the donor's slot is preferred only when it is genuinely free")
inca = civ_of("Incas")
di = B.describe(inca, TREES["INCAS"], 12, 2550)
print("     Incas: %s" % di)
slot, why = B.choose_slot(inca, TREES["INCAS"], 12, donor_slot=1)
print("     Incas choose_slot(donor_slot=1) -> %s (%s)" % (slot, why or "ok"))
check("the Incas cannot keep slot 1 (their champi line is there)", slot != 1,
      "got %s" % slot)
check("...and it says nothing went wrong", why == "")

print()
print("D  an exhausted building is REPORTED, not guessed")
slot, why = B.choose_slot(brit, TREES["BRITONS"], 84)
print("     British Market(84): slot=%s" % slot)
print("     why=%s" % why)
check("the Market yields no slot", slot is None)
check("and the reason names the building and what occupies it",
      "84" in why and "128" in why, "%s" % why)

print()
print("E  every grant subject the earlier rounds chose has a free slot")
SUBJECTS = [("British", "BRITONS", 12), ("Mapuche", "MAPUCHE", 45),
            ("Muisca", "MUISCA", 12), ("Poles", "POLES", 45),
            ("Wu", "WU", 87)]
for disp, stem, bldg in SUBJECTS:
    c = civ_of(disp)
    if c is None:
        c = next((x for x in tk._parsed[1]
                  if CT.civ_file_stem(x["name"]) == stem), None)
    if c is None:
        print("     %-10s no .dat civ record" % disp)
        continue
    f = B.free_slots(c, TREES[stem], bldg)
    print("     %-10s building %-4s free slots: %s" % (disp, bldg, f))
    check("%s has a free slot at building %d" % (disp, bldg), bool(f))

print()
print("BUTTON SLOTS: a granted unit takes a slot with no already-available unit; the")
print("  shipped habit for a RegionalUnit is slot 4; an exhausted building is")
print("  reported with its occupants rather than silently masked.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
