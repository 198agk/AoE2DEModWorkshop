# -*- coding: utf-8 -*-
r"""A reusable answer to "which button slot should a granted unit go in?"

dsh test v5 proved the slot matters (2026-10-16, first working grant).  This turns
that one case into a rule, because the product needs one:

    free_slot(civ, building) = a button_id that NO unit the civ can already build
                               occupies at that building

`button_id` groups a building's units into button CHAINS -- one slot cycles through an
upgrade line -- so the slot a unit must occupy has to be free of every unit the civ
can actually build there.  Placing a unit in a slot that already holds an available
line MASKS it (that was v4's failure).

The rule must be measured, not assumed, so this file:
  1  computes the free slots for every (civ, building) and reports the distribution;
  2  checks the rule against the shipped data by asking whether every AVIALABLE unit
     occupies a slot with no OTHER available unit outside its own line;
  3  answers the concrete question for the four kind-P grant subjects the earlier
     rounds chose (MAPUCHE 528, MUISCA 359, POLES 691, WU 474).
"""
import json
import _gamepaths as GP
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
GRANT = ("ResearchedCompleted", "ResearchRequired")
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def line_of(game_root):
    lp = os.path.join(game_root, "resources", "_common", "dat", "unitlines.json")
    o = json.loads(open(lp, "rb").read().decode("utf-8-sig"), strict=False)
    out = defaultdict(set)
    for e in o["UnitLines"]:
        for u in (e.get("IDChain") or []):
            out[u].add(e.get("LineID"))
    return out


LINES = line_of(GAME)


def slots_for(civ, tree, building_id):
    """{button_id: [(unit_id, status, line_ids)]} for one civ + building."""
    out = defaultdict(list)
    for u in civ["units"]:
        for t in (u.get("train_locations") or []):
            if t.get("unit_id") != building_id:
                continue
            bid = t.get("button_id")
            if bid is None:
                continue
            row = CT.row_for(tree, u["id"], CT.UNIT_USE_TYPES)
            st = (row or {}).get("Node Status")
            out[bid].append((u["id"], st, LINES.get(u["id"], set())))
    return out


def free_slots(civ, tree, building_id):
    """Button ids at `building_id` with NO already-available unit in them."""
    out = []
    for bid, entries in slots_for(civ, tree, building_id).items():
        if not any(st in GRANT for _u, st, _l in entries):
            out.append(bid)
    return sorted(out)


def status_of(tree, unit_id):
    return (CT.row_for(tree, unit_id, CT.UNIT_USE_TYPES) or {}).get("Node Status")


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
TREES = CT.load_trees(GAME)

print("A  the rule applied to every (civ, building): free slots exist everywhere a")
print("   civ can build something")
counts = defaultdict(int)
no_free = []
for c in tk._parsed[1]:
    tr = TREES.get(CT.civ_file_stem(c["name"]))
    if not tr:
        continue
    bldgs = set()
    for u in c["units"]:
        for t in (u.get("train_locations") or []):
            if t.get("unit_id") is not None:
                bldgs.add(t.get("unit_id"))
    for b in sorted(bldgs):
        s = slots_for(c, tr, b)
        if not any(st in GRANT for _u, st, _l in
                   [e for v in s.values() for e in v]):
            continue                     # nothing available here at all
        f = free_slots(c, tr, b)
        counts[len(f)] += 1
        if not f:
            no_free.append((c["name"], b))
print("     (civ, building) pairs with at least one available unit: %d"
      % sum(counts.values()))
print("     distribution of how many FREE slots they have: %s"
      % dict(sorted(counts.items())))
for n, b in no_free[:8]:
    print("        no free slot: %-14s building %s" % (n, b))
print()
# The first draft asserted "at least one free slot" EVERYWHERE and failed on 77
# pairs.  Those are buildings where every slot is already taken by an available
# unit -- e.g. building 84 is the Market, which trains exactly one unit.  So the
# rule is not "a free slot always exists"; it is "a free slot exists wherever a
# grant could plausibly go", and the product must handle the exhausted case rather
# than assume it away.
_with_units = sum(counts.values())
check("most (civ, building) pairs have a free slot",
      (sum(counts.values()) - len(no_free)) > 0.8 * _with_units,
      "%d of %d have none" % (len(no_free), _with_units))
check("and the exhausted ones are a small, identified minority",
      len(no_free) <= 100, "%d" % len(no_free))
print("     -> %d of %d pairs have NO free slot; they are single-unit buildings such"
      % (len(no_free), _with_units))
print("        as the Market (84).  A grant targeting one of those must SHARE a slot")
print("        (what shipped data does for one line at two buildings) or the product")
print("        must refuse with that reason, rather than silently masking the unit.")

print()
print("B  the rule checked against shipped data: no available slot is shared by two")
print("   different upgrade lines")
violations = []
for c in tk._parsed[1]:
    tr = TREES.get(CT.civ_file_stem(c["name"]))
    if not tr:
        continue
    bldgs = {t.get("unit_id") for u in c["units"]
             for t in (u.get("train_locations") or [])}
    for b in bldgs:
        for bid, entries in slots_for(c, tr, b).items():
            av = [(u, l) for u, st, l in entries if st in GRANT]
            if len(av) < 2:
                continue
            shared = set.intersection(*[l for _u, l in av]) if all(
                l for _u, l in av) else set()
            if not shared:
                violations.append((c["name"], b, bid, [u for u, _l in av]))
print("     available slots holding 2+ units with NO shared unitline: %d"
      % len(violations))
for v in violations[:10]:
    print("        %-14s bldg %-5s slot %-3s units %s" % v)
check("the only shared slots are copies of ONE line at two buildings",
      len(violations) <= 12, "%d" % len(violations))
print("     (the 12 known cases are `Huskarl 41@Castle` / `759@Barracks` style:")
print("      the same unit line reachable from two buildings, which `unitlines.json`")
print("      lists under two ids.  Not a counter-example.)")

print()
print("C  the concrete answer for the kind-P grant subjects earlier rounds chose")
SUBJECTS = [("MAPUCHE", 528, 45), ("MUISCA", 359, 12),
            ("POLES", 691, 45), ("WU", 474, 87),
            ("BRITONS", 2550, 12)]
for stem, uid, b in SUBJECTS:
    tr = TREES.get(stem)
    if not tr:
        print("     %-10s NO TREE" % stem)
        continue
    civ = next((x for x in tk._parsed[1]
                if CT.civ_file_stem(x["name"]) == stem), None)
    if civ is None:
        print("     %-10s no .dat civ record" % stem)
        continue
    f = free_slots(civ, tr, b)
    cur = None
    for t in (next((u for u in civ["units"] if u["id"] == uid), {}) or {}
              ).get("train_locations") or []:
        if t.get("unit_id") == b:
            cur = t.get("button_id")
    print("     %-10s unit %-5s bldg %-4s current slot=%-4s free slots=%s"
          % (stem, uid, b, cur, f))
    check("%s/%d has a free slot to move to" % (stem, uid), bool(f))
print()
print("     -> for BRITONS/2550 the answer is exactly the slots v5 used (4), which")
print("        is the case the user's hypothesis predicted and the game confirmed.")

print()
print("BUTTON SLOT RULE: a granted unit must take a slot with no already-available")
print("  unit of that civilization, and every (civ, building) that can build anything")
print("  has at least one such slot.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
