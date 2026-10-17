"""★★★ THE GATE, IN THE .dat: `train_locations` on the per-civ unit record.

The list-aware contrast found `train_locations` differs in 43 of 43 pairs where
one civ's tree says it can build a unit and another's says NotAvailable -- and it
differs for EXACTLY the unit asked about.  `costs` and `type50` differ only
because they carry the unit's stats/price, which are the same unit; `civ` is the
array index.  `train_locations` is the one field that says WHERE a unit is built.

Cross-check against the effect layer: tech[16] (owned by Goths) sets
attribute 42 (train location) = 12 on unit 41.  So the two independent readings
of the same .dat agree: the civ-owned tech writes the unit's train_locations.

This turns "can civ X build unit Y" into a dat-side question with a decisive
test -- does a unit's train_locations list differ between a civ that can build it
and one that cannot, in a way that matches the known AoE2 rosters?
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
dat_civs = tk._civs
trees = CT.load_trees(tk.game_root)


def rec(civ_name, uid):
    for c in dat_civs:
        if c["name"] == civ_name:
            for u in c["units"]:
                if u["id"] == uid:
                    return u
    return None


def tl(civ_name, uid):
    u = rec(civ_name, uid)
    if u is None:
        return "<no record>"
    locs = u.get("train_locations") or []
    return [l.get("id") if isinstance(l, dict) else l for l in locs]


print("=== known rosters, decided by train_locations alone ===")
CASES = [
    (41, "Huskarl",   ["Goths", "British", "Turks"]),
    (8, "Longbowman", ["British", "Goths", "Turks"]),
    (5, "Hand Cannoneer", ["British", "Turks", "Spanish"]),
    (755, "Tarkan",   ["Huns", "British"]),
    (692, "Berserk",  ["Vikings", "British"]),
    (83, "Villager",  ["British", "Goths"]),
]
for uid, label, civs in CASES:
    print("  unit %-4d %-15s" % (uid, label))
    for c in civs:
        print("      %-10s train_locations=%s" % (c, tl(c, uid)))
print()

# Whole-corpus test: does an EMPTY train_locations track the tree's NotAvailable?
empty_na = 0
empty_ok = 0
nonempty_na = 0
nonempty_ok = 0
for stem in trees:
    dname = None
    for c in dat_civs:
        if CT.civ_file_stem(c["name"]) == stem:
            dname = c["name"]
    if dname is None:
        continue
    for row in CT.unit_rows(trees[stem]):
        uid = row.get("Node ID")
        st = row.get("Node Status")
        u = rec(dname, uid)
        if u is None:
            continue
        locs = u.get("train_locations") or []
        able = st != "NotAvailable"
        if not locs and able:
            empty_ok += 1
        elif not locs and not able:
            empty_na += 1
        elif locs and not able:
            nonempty_na += 1
        else:
            nonempty_ok += 1

print("=== tree status x whether the dat record has a train location ===")
print("  can build      + has train_locations : %d" % nonempty_ok)
print("  can build      + NO train_locations : %d" % empty_ok)
print("  NotAvailable   + has train_locations : %d" % nonempty_na)
print("  NotAvailable   + NO train_locations : %d" % empty_na)
print()
print("If train_locations were the gate, the two 'NotAvailable' rows would hold "
      "all the mass and the 'can build + NO locations' row would be ~0.")
