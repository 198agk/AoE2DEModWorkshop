# -*- coding: utf-8 -*-
"""Permanent pin: the four tech-side refused families are NOT duplicates of the
shipped intents, and each stays refused for a stated reason.

Rounds 28 and 29 established that "the family with the most rows" is not "the
feature the user asked for", and that a candidate mechanism must be tested by
CONTRAST.  This applies both to the four remaining tech-side families:

    type 101 Tech Cost Modifier       175 rows / 19 techs newly unlockable
    type 103 Tech Time Modifier        71 rows / 16
    type 102 Disable Tech             269 rows / 21
    type 8   Modify Tech               52 rows /  5

The tempting shortcut is "tech.cost and tech.research_time already write tech
costs and times, so these are the same thing".  They are not: they target
ANOTHER tech, conditionally on the carrier being researched, and the carrier is
usually civ-owned -- an observable no shipped intent can produce.

So the correct outcome is not "wire them" (semantics are only partly known) and
not "they are duplicates" (they are not).  It is: name the missing capability,
name the exact reason it stays closed, and pin both so a later round cannot
quietly claim either.

Exit code 0 if every pinned number still holds.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402
from aoe2mod.dat import locate as L                            # noqa: E402
from aoe2mod.game import civtechtrees as CT                    # noqa: E402
from aoe2mod.intent import compiler as C                       # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    trees = CT.load_trees(tk.game_root)

    idx2stem = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            idx2stem[c["index"]] = stem

    fam = collections.defaultdict(list)
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] in (101, 102, 103, 8):
                fam[r["type"]].append((ti, t.get("civ"), r["raw"]))

    print("A pinned: 101/103 target ANOTHER tech -- not an alias of tech.cost")
    check(len(fam[101]) == 175 and len(fam[103]) == 71,
          "the two modifier families still have 175 and 71 rows",
          "%d / %d" % (len(fam[101]), len(fam[103])))
    d101 = sum(1 for ti, _o, rw in fam[101] if rw[1] != ti)
    d103 = sum(1 for ti, _o, rw in fam[103] if rw[1] != ti)
    check(d101 == 172 and d103 == 68,
          "and both overwhelmingly modify a DIFFERENT tech, not themselves",
          "101: %d/175, 103: %d/71" % (d101, d103))
    g101 = sum(1 for _ti, o, _rw in fam[101] if o is None or o < 0)
    g103 = sum(1 for _ti, o, _rw in fam[103] if o is None or o < 0)
    check(g101 == 31 and g103 == 11,
          "and most are carried by a CIV-OWNED tech, so the modifier is per-civ",
          "global-carried 101: %d, 103: %d" % (g101, g103))

    print()
    print("B pinned: the operation vocabulary has no established meaning")
    c101 = collections.Counter(rw[3] for _ti, _o, rw in fam[101])
    c103 = collections.Counter(rw[3] for _ti, _o, rw in fam[103])
    check(sorted(c101) == [-1, 0, 1, 2],
          "101 uses four slot-C codes, only two of which look like set/multiply",
          sorted(c101))
    check(c101[-1] + c101[1] == 24,
          "101 has 24 rows on the two codes with no determined meaning (they "
          "cannot be guessed)", "%d" % (c101[-1] + c101[1]))
    check(sorted(c103) == [0, 2],
          "103 uses only the two codes, but 53 of its rows carry B == -1 "
          "(which resource?)",
          sorted(c103))
    b103 = sum(1 for _ti, _o, rw in fam[103] if rw[2] == -1)
    check(b103 == 53, "103 rows with slot B == -1", b103)
    b101_odd = [r for _ti, _o, r in fam[101] if r[2] not in (-1, 0, 1, 2, 3)]
    check(len(b101_odd) == 1 and b101_odd[0][2] == 507,
          "101 has exactly one row on a resource code outside food/wood/stone/"
          "gold (507 -- the same unmapped resource id seen on unit records)",
          b101_odd)

    print()
    print("C pinned: 102 is NOT a duplicate of a tree row (the round-30 error)")
    rows102 = [(ti, o, int(rw[4])) for ti, o, rw in fam[102]]
    civ102 = [(ti, o, d) for ti, o, d in rows102 if o is not None and o >= 0]
    check(len(rows102) == 269 and len(civ102) == 81,
          "102 has 269 rows, 81 of them civ-carried",
          "%d / %d" % (len(rows102), len(civ102)))
    both_rc = 0
    for ti, o, d in civ102:
        stem = idx2stem.get(o)
        if stem is None:
            continue
        sc = CT.node_status(trees[stem], ti, CT.TECH_USE_TYPES)
        sd = CT.node_status(trees[stem], d, CT.TECH_USE_TYPES)
        if sc == "ResearchedCompleted" and sd == "ResearchedCompleted":
            both_rc += 1
    check(both_rc == 64,
          "64 rows DISABLE a tech the civ's own tree offers as available -- so "
          "'the tree already says it' is false", both_rc)
    self_ref = sum(1 for ti, _o, d in civ102 if ti == d)
    check(self_ref == 26, "26 of them disable the carrier itself", self_ref)
    check(len(civ102) - self_ref == 55,
          "55 disable a sibling (the choose-one-of-two unique techs)",
          len(civ102) - self_ref)
    by_civ = collections.defaultdict(set)
    for ti, o, d in civ102:
        if ti != d:
            by_civ[idx2stem.get(o, "?")].add((ti, d))
    two_way = sum(1 for _c, ps in by_civ.items()
                  for a, b in ps if (b, a) in ps)
    check(two_way == 46,
          "46 sibling edges are mutual, i.e. a real either/or rule no tree row "
          "can express", two_way)
    check(len({idx2stem.get(o) for _ti, o, _d in civ102}) == 13,
          "concentrated in 13 civs, led by the Chronicles set",
          len({idx2stem.get(o) for _ti, o, _d in civ102}))
    known = {("ACHAEMENIDS", 1110, 1111), ("ATHENIANS", 1120, 1121),
             ("SPARTANS", 1130, 1132), ("PURU", 1307, 1308),
             ("WEI", 1056, 1058)}
    have = {(c, a, b) for c, ps in by_civ.items() for a, b in ps}
    check(known <= have or all(any((c, a, b) in have or (c, b, a) in have
                                   for c, a, b in [k]) for k in known),
          "named either/or pairs are the real ones (Sparabaras/Reed Arrows etc.)",
          sorted(known))

    print()
    print("D pinned: type 8 writes a STRING-ID-shaped value, not a number")
    d8 = [int(rw[4]) for _ti, _o, rw in fam[8]]
    check(len(fam[8]) == 52 and len(set(d8)) == 28,
          "52 rows, 28 distinct slot-D values", "%d / %d" % (len(fam[8]), len(set(d8))))
    check(max(d8) == 418073 and min(d8) == 0,
          "range spans 0..418073 -- string-id space, not a quantity (unit/"
          "tech records use the same id blocks)", "%d..%d" % (min(d8), max(d8)))

    print()
    print("E pinned: the shipped intents still cannot reach these families")
    strat = C.load_schema()[0]
    # The pin is that NONE of these is a tech-modifier family, not that the count
    # is frozen: `unit.sprite` was added later and reaches neither 101/102/103/8
    # nor any effect command at all.  Asserting the exact set made an unrelated
    # new intent look like a regression, while asserting only "no modifier" is
    # the property this section exists to protect.
    _declared = set(strat["intents"])
    check({"tech.cost", "tech.research_time", "tech.effect"} <= _declared,
          "the tech-editing intents are still declared", sorted(_declared))
    check(not any("modifier" in k or "disable" in k for k in _declared),
          "the schema still declares no tech-modifier family intent",
          sorted(_declared))
    ops = C._EFFECT_OPERATION if hasattr(C, "_EFFECT_OPERATION") else None
    check(ops is None or not ({101, 102, 103, 8} & set(ops)),
          "and the effect-operation table still excludes 101/102/103/8 "
          "(its meaning is 'slot C is an attribute id', which none of these are)",
          sorted(ops) if ops else "not introspectable")

    print()
    if FAILS:
        print("TECH-SIDE FAMILY PIN: %d FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("TECH-SIDE FAMILY PIN: these four are real missing capabilities, not "
          "duplicate spellings -- and each stays refused for a stated reason.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
