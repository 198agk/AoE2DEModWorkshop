"""PIN: the dat-side layers that do NOT gate buildability, and the one that partly does.

The user corrected the project's central assumption (m19924):

    "游戏用的是同名同路径的 empires2_x2_p1.dat 文件 ... 游戏要的是 dat，而不是 json"

So every availability claim must now be checked against the .dat.  This file
pins what that check actually returned, because each of these was measured and
each is easy to re-derive wrongly:

A. MEMBERSHIP IS NOT THE GATE.  Every unit row in a civilization's tree names a
   unit that is present in that civilization's own .dat unit array -- 3,115 of
   3,115 for rows it can build and 571 of 571 for rows it cannot.  If array
   membership spelled availability, one of those columns would be empty.

B. THE PER-CIV UNIT RECORD IS NOT THE GATE.  For every unit that some civs can
   build and others are told NotAvailable, the two civs' records differ only by
   `civ` (the array index) and by 4 cosmetic graphics fields (`type50.attack_graphic`
   3 times, `icon_id` once) -- all on units whose single id resolves to DIFFERENT
   units in different civilizations, so they cannot be the availability lever.
   No train-location, enabled/disabled, or research-prerequisite field differs.
   The first version of this comparison reported 43/43 differences and was WRONG:
   it stripped `_` keys only at the top level, so nested `_off_train_time` /
   `_off_amount` byte offsets made byte-identical records look different.  Compare
   with offsets stripped RECURSIVELY.

C. THE EFFECT LAYER PARTLY REPRODUCES REAL ROSTERS.  A civ-owned tech carrying a
   type-2 Enable Unit command (`tech.civ` names the owner) matches the known owner
   of 11 of 12 unique units.  This is the strongest dat-side signal found -- and it
   is not the whole gate, because:

D. SOMETHING ELSE GATES TOO.  The same layer says Hand Cannoneer is enabled
   GLOBALLY (one `civ == -1` enable, no civ-owned disable anywhere), which would
   make it available to all 63 civilizations -- while the tree tells 38 of them
   NotAvailable.  A layer that says "everyone" where the game says "most" is not
   the gate.  (`Persians`/War Elephant is the one unique-unit miss in C.)

VERDICT: the dat-side gate for "can civ X build unit Y" is still UNIDENTIFIED.
What follows from that is a product claim, not a format claim: the shipped
`unit.availability` intent writes `CivTechTrees/<CIV>.json`, and no in-game result
has ever shown that write changing anything.
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, tail, _how = tk._parsed
techs = L.locate_techs(data, tail, gv)
effects, _ = L.locate_effects(data)
trees = CT.load_trees(tk.game_root)
names = [c["name"] for c in civs]

by_stem = {}
for c in civs:
    by_stem.setdefault(CT.civ_file_stem(c["name"]), c["name"])


def rec(civ_name, uid):
    for c in civs:
        if c["name"] == civ_name:
            for u in c["units"]:
                if u["id"] == uid:
                    return u
    return None


def strip_offsets(v):
    """Drop every key starting with '_' at ANY depth.

    This is the fix for the probe bug described in B.  Byte offsets live in
    nested dicts (`_off_train_time`, `_off_amount`, `_off_class`), so a top-level
    filter cannot see them and every pair looks different.
    """
    if isinstance(v, dict):
        return {k: strip_offsets(x) for k, x in v.items() if not k.startswith("_")}
    if isinstance(v, list):
        return [strip_offsets(x) for x in v]
    return v


# ---------------------------------------------------------------- A
tree_rows = 0
in_dat = 0
missing = 0
na_rows = 0
na_in_dat = 0
for stem, tax in trees.items():
    dname = by_stem.get(stem)
    if dname is None:
        continue
    for row in CT.unit_rows(tax):
        uid = row.get("Node ID")
        if uid is None:
            continue
        tree_rows += 1
        present = rec(dname, uid) is not None
        if present:
            in_dat += 1
        else:
            missing += 1
        if row.get("Node Status") == "NotAvailable":
            na_rows += 1
            if present:
                na_in_dat += 1

print("A. membership in the civ's own .dat unit array")
print("   tree unit rows checked          : %d" % tree_rows)
print("   present in that civ's array     : %d   absent: %d" % (in_dat, missing))
print("   rows told NotAvailable          : %d   of which present: %d"
      % (na_rows, na_in_dat))
assert tree_rows > 3000, "expected thousands of unit rows"
assert missing == 0, "a tree row must name a unit the civ actually ships"
assert na_in_dat == na_rows, "NotAvailable rows must also be present"
print("   -> presence does not separate buildable from blocked\n")

# ---------------------------------------------------------------- B
pairs = {}
for stem, tax in trees.items():
    for row in CT.unit_rows(tax):
        st = row.get("Node Status")
        nid = row.get("Node ID")
        if st == "ResearchedCompleted":
            pairs.setdefault(nid, {})["yes"] = stem
        elif st == "NotAvailable":
            pairs.setdefault(nid, {})["no"] = stem
usable = [(n, d["yes"], d["no"]) for n, d in pairs.items()
          if "yes" in d and "no" in d]

diff_fields = defaultdict(int)
compared = 0
for uid, yes, no in usable:
    a = rec(by_stem[yes], uid)
    b = rec(by_stem[no], uid)
    if a is None or b is None:
        continue
    compared += 1
    ja, jb = strip_offsets(a), strip_offsets(b)
    for k in set(ja) | set(jb):
        if ja.get(k) != jb.get(k):
            diff_fields[k] += 1

print("B. per-civ unit record, offsets stripped recursively")
print("   can/cannot pairs compared       : %d" % compared)
for k, n in sorted(diff_fields.items(), key=lambda kv: -kv[1]):
    print("   field differing: %-16s in %d" % (k, n))
assert compared > 20, "need a meaningful number of contrast pairs"
# Two cosmetic fields also differ, in 4 of 43 pairs, and they are NOT a gate:
# `type50.attack_graphic` (3) and `icon_id` (1) -- both on units 1258 / 2628 /
# 1104, which are the known Chronicles cases where ONE id resolves to DIFFERENT
# units in different civilizations.  A field that tracks which unit the id means
# cannot also be the thing that decides whether the civ may build it.  What the
# assertion protects is the absence of any AVAILABILITY field: no train-location,
# no enabled/disabled, no research prerequisite differs.
assert set(diff_fields) <= {"civ", "type50", "icon_id"}, (
    "no gameplay/availability field may differ; got %s" % sorted(diff_fields))
assert diff_fields.get("civ", 0) == compared, (
    "the civ index must differ in every pair")
assert diff_fields.get("type50", 0) + diff_fields.get("icon_id", 0) <= 5, (
    "the cosmetic differences must stay a handful, or the picture changed")
print("   -> only `civ` (always) plus 4 cosmetic graphics/icon fields differ;")
print("      no availability field does, so the record body is not the gate\n")

# ---------------------------------------------------------------- C
own_enable = defaultdict(set)
glob_enable = defaultdict(int)
for t in techs:
    owner = t.get("civ", -1)
    for r in C.effect_rows(effects, t, fanout=None, ix=None):
        if r["type"] != 2 or r["raw"][2] != 1:
            continue
        unit = r["raw"][1]
        if 0 <= owner < len(names):
            own_enable[unit].add(names[owner])
        else:
            glob_enable[unit] = glob_enable[unit] + 1

UNIQUE = [(8, "British"), (41, "Goths"), (755, "Huns"), (692, "Vikings"),
          (725, "Aztecs"), (291, "Japanese"), (46, "Persians"),
          (282, "Saracens"), (40, "Byzantine"), (25, "Teutons"),
          (73, "Chinese"), (281, "French")]
matched = 0
misses = []
for uid, owner in UNIQUE:
    en = own_enable.get(uid, set())
    if en == {owner}:
        matched += 1
    else:
        misses.append((uid, owner, sorted(en)))

print("C. civ-owned type-2 Enable Unit vs the known unique-unit owner")
print("   unique units matching exactly   : %d of %d" % (matched, len(UNIQUE)))
print("   misses                          : %s" % misses)
assert matched >= 11, "the effect layer must reproduce most unique-unit owners"
assert misses, ("a 12/12 result would mean this file is stale -- the known "
                "War Elephant miss should still be here")
print("   -> the effect layer carries real per-civ ownership information\n")

# ---------------------------------------------------------------- D
blocked_hc = 0
for stem, tax in trees.items():
    for row in CT.unit_rows(tax):
        if row.get("Node ID") == 5 and row.get("Node Status") == "NotAvailable":
            blocked_hc += 1
print("D. the same layer's contradiction")
print("   Hand Cannoneer (5): global enables %d, civ-owned enables %d"
      % (glob_enable.get(5, 0), len(own_enable.get(5, set()))))
print("   civs the tree tells NotAvailable : %d" % blocked_hc)
assert glob_enable.get(5, 0) == 1 and not own_enable.get(5), (
    "the global-only shape is the measured one")
assert blocked_hc > 20, "the tree must block a substantial number of civs"
print("   -> the layer says 'everyone' where the game says 'most',")
print("      so it is not the gate on its own\n")

print("PIN: the dat-side gate for buildability is still UNIDENTIFIED -- "
      "membership, the unit record, and the type-2 layer are each refuted as "
      "the sole mechanism. The shipped unit.availability intent writes "
      "CivTechTrees JSON, which no in-game result has ever shown taking effect.")
