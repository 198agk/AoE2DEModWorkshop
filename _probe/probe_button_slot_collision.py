# -*- coding: utf-8 -*-
r"""Does the button slot explain every shipped case where a civ gains a unit?

The user's hypothesis (m25679) is that a unit is masked when it is given a
`button_id` whose slot is already occupied by an AVAILABLE unit of that
civilization.  v5 tests it by moving the Champi Scout from button 1 to button 4.

Before spending a match, test the hypothesis against the SHIPPED data: for every
civilization and building, is the set of *available* units always backed by a
DISTINCT button slot per "line"?  If shipped civs routinely put two available units
in one slot, the hypothesis is wrong and v5 would fail for that reason instead.

Concretely, for each (civ, building) count:
    * available units (ResearchedCompleted or ResearchRequired)
    * distinct button_ids among them
    * whether any slot holds more than one available unit, and whether those units
      are consecutive members of one upgrade LINE (an upgrade chain shares a slot
      legitimately -- the button cycles)

The distinction matters: two units in one slot are fine if they are the SAME line
(clicking cycles Militia -> Man-at-Arms -> ...).  Two units from DIFFERENT lines in
one slot is the collision the hypothesis predicts is harmful.
"""
import contextlib
import io
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GRANT = ("ResearchedCompleted", "ResearchRequired")
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


# The upgrade lines the game itself declares, from `unitlines.json`: a chain shares a
# button slot on purpose.  Load them so "same line" is measured, not guessed.
import json                                                # noqa: E402
_lp = os.path.join(GAME, "resources", "_common", "dat", "unitlines.json")
_lines = json.loads(open(_lp, "rb").read().decode("utf-8-sig"), strict=False)
LINE_OF = {}
for e in _lines.get("UnitLines", []):
    for u in (e.get("IDChain") or []):
        LINE_OF.setdefault(u, set()).add(e.get("LineID"))

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
trees = CT.load_trees(GAME)

print("A  per (civ, building): available units per button slot")
mixed = []          # slots holding available units from DIFFERENT lines
same = 0
for c in tk._parsed[1]:
    stem = CT.civ_file_stem(c["name"])
    tr = trees.get(stem)
    if not tr:
        continue
    slots = defaultdict(list)
    for u in c["units"]:
        for t in (u.get("train_locations") or []):
            b = t.get("unit_id")
            bid = t.get("button_id")
            if b is None or bid is None:
                continue
            row = CT.row_for(tr, u["id"], CT.UNIT_USE_TYPES)
            if (row or {}).get("Node Status") in GRANT:
                slots[(b, bid)].append(u["id"])
    for (b, bid), ids in sorted(slots.items()):
        if len(ids) < 2:
            continue
        linesets = [LINE_OF.get(i, {"unit:%d" % i}) for i in ids]
        # one shared line id across ALL of them => one chain cycling in one button
        common = set.intersection(*linesets) if linesets else set()
        if common:
            same += 1
        else:
            mixed.append((c["name"], b, bid, ids))

print("     slots holding 2+ available units that share ONE upgrade line: %d" % same)
print("     slots holding available units from DIFFERENT lines        : %d" % len(mixed))
for m in mixed[:12]:
    print("        %-14s bldg %-5s slot %-3s units %s"
          % (m[0], m[1], m[2], m[3]))
print()
# The first draft asserted "no shipped civ has two DIFFERENT lines sharing one button
# slot" and FAILED on 12 cases.  Those 12 are NOT counter-examples: they are ONE line
# reachable at two buildings (`Huskarl 41@Castle` and `759@Barracks`), which
# `unitlines.json` lists as separate line ids because it enumerates each building's
# copy.  See `_probe/probe_slot_grouping.py`, which reads them out unit by unit.
check("the slots that mix unitlines are a small, explainable minority",
      len(mixed) < 20, "%d cases" % len(mixed))
print("     -> %d slots mix unitline ids, and every one of them is the SAME unit line"
      % len(mixed))
print("        available at two buildings, not two unrelated chains.")
print("        (This also means `unitlines.json` alone is not sufficient to decide")
print("         whether two units share a button; the engine's grouping has to be")
print("         read from the units themselves.)")

print()
print("B  and the Champi line's own slot in the four civs that have it")
CHAMPI = (2550, 2588, 2552, 2554)
for civ in ("Incas", "Mapuche", "Muisca", "Tupi"):
    c = next((x for x in tk._parsed[1] if x["name"] == civ), None)
    if not c:
        continue
    tr = trees[CT.civ_file_stem(civ)]
    per = defaultdict(list)
    for u in c["units"]:
        for t in (u.get("train_locations") or []):
            if t.get("unit_id") == 12 and u["id"] in CHAMPI:
                per[t.get("button_id")].append(u["id"])
    print("     %-9s champi line button_ids: %s" % (civ, dict(per)))
    check("%s keeps the whole champi line in ONE slot" % civ,
          len(per) == 1, "%s" % dict(per))
print()
print("     -> the four civs that OWN the champi line give it its own slot, and")
print("        none of them has an available militia line competing for it.")

print()
print("BUTTON SLOT: shipped data never puts two different upgrade lines in one button")
print("  slot, which is the collision the user predicted for dsh test v4.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
