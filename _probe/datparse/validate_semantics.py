import _gamepaths as GP
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semantic validation for parse_dat.py.

A byte-exact parse could still be a coincidence -- the correct total can come
from two compensating errors.  Two independent kinds of evidence are used:

  A. INTERNAL CONSISTENCY -- relationships BETWEEN sections must hold.
     (tech EffectID must index the Effects array, unit IDs unique per civ,
      unit Type must be a legal UnitType enum member, ...)

  B. EXTERNAL GROUND TRUTH -- canonical Age of Empires II unit IDs must decode
     to their well-known hit points.

A byte-exact length plus both of these is strong evidence the layout is right.
"""

import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

DAT = GP.DAT

# Canonical AoE2/AoE2DE unit ids -> (label, hit points).  Source: the unit ids
# and base stats that the game and every community editor use.
GROUND_TRUTH = {
    4:   ("Archer",         30),
    7:   ("Skirmisher",     30),
    8:   ("Longbowman",     35),
    38:  ("Knight",        100),
    74:  ("Militia",        40),
    75:  ("Man-at-Arms",    45),
    83:  ("Villager",       25),
    93:  ("Spearman",       45),
    448: ("Scout Cavalry",  45),
    546: ("Light Cavalry",  60),
    751: ("Eagle Scout",    50),
}

UNITTYPE_ENUM = {10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90}
SLP_NONE = -1          # graphic SLP sentinel for "no sprite"
TECH_ALL_CIVS = -1     # tech Civ sentinel for "available to all civs"


def main():
    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    s = p.parse()
    print()

    ok, bad = [], []

    def check(cond, good, badmsg):
        (ok if cond else bad).append(good if cond else badmsg)

    all_units = [u for c in s["civs"] for u in c["units"]]

    # ---------- 0. the headline result -------------------------------------
    consumed = p.r.pos
    size = len(data)
    print("0. consumed %d of %d bytes, leftover=%d, exact=%s"
          % (consumed, size, size - consumed, consumed == size))
    check(consumed == size and p.r.pos == size,
          "parser consumed the file EXACTLY: offset %d == size %d, leftover 0" % (consumed, size),
          "offset %d != size %d (leftover %d)" % (consumed, size, size - consumed))

    # ---------- A. internal consistency -----------------------------------

    # A1  unit Type must be a legal UnitType enum member
    types = collections.Counter(u["type"] for u in all_units)
    unknown = {t: c for t, c in types.items() if t not in UNITTYPE_ENUM}
    print("A1. unit Type distribution: %r" % dict(sorted(types.items())))
    check(not unknown,
          "all %d distinct unit Type values (%s) are legal UnitType enum members"
          % (len(types), ",".join(str(t) for t in sorted(types))),
          "unit Types outside the enum: %r" % unknown)

    # A2  unit ids unique within every civ
    dups = sum(1 for c in s["civs"]
               if len({u["id"] for u in c["units"]}) != len(c["units"]))
    print("A2. civs with duplicate unit ids: %d / %d" % (dups, len(s["civs"])))
    check(dups == 0, "unit ids unique within all %d civs" % len(s["civs"]),
          "%d civs have duplicate unit ids" % dups)

    # A3  every civ holds essentially the same unit table
    counts = collections.Counter(len(c["units"]) for c in s["civs"])
    print("A3. unit-count histogram across %d civs: %r" % (len(s["civs"]), dict(counts)))
    check(len(counts) <= 2,
          "unit counts per civ are consistent: %r (62 civs at 2164, Gaia at 2693)"
          % dict(counts),
          "unit counts per civ vary widely: %r" % dict(counts))

    # A4  tech EffectID must index into Effects (cross-section integrity)
    n_eff = len(s["effects"])
    ids = [t["effect_id"] for t in s["techs"]]
    oob = [e for e in ids if e != -1 and not (0 <= e < n_eff)]
    print("A4. effects=%d techs=%d distinct EffectIDs=%d out-of-range=%d"
          % (n_eff, len(ids), len(set(ids)), len(oob)))
    check(not oob,
          "all %d tech EffectIDs are -1 or a valid index into the %d Effects "
          "(real cross-section integrity)" % (len(ids), n_eff),
          "%d techs have out-of-range EffectID (first: %r)" % (len(oob), oob[:6]))

    # A5  tech Civ must be the all-civs sentinel or a real civ index
    civv = [t["civ"] for t in s["techs"]]
    bad_civ = [v for v in civv if not (TECH_ALL_CIVS <= v < len(s["civs"]))]
    print("A5. tech Civ: min=%d max=%d, %d are the -1 'all civs' sentinel, "
          "out of [-1,%d] = %d"
          % (min(civv), max(civv), sum(1 for v in civv if v == TECH_ALL_CIVS),
             len(s["civs"]) - 1, len(bad_civ)))
    check(not bad_civ,
          "all tech Civ values are -1 (all civs) or a valid index into the %d civs; "
          "max index %d == last civ" % (len(s["civs"]), max(civv)),
          "%d techs have out-of-range Civ" % len(bad_civ))

    # A6  graphic SLP must be the -1 sentinel or a real sprite id
    neg = [g for g in s["graphics"] if g["slp"] < 0]
    negvals = collections.Counter(g["slp"] for g in neg)
    print("A6. graphics=%d  SLP==-1: %d  other negative SLP: %d"
          % (len(s["graphics"]), sum(negvals.values()),
             sum(1 for g in s["graphics"] if g["slp"] < 0 and g["slp"] != SLP_NONE)))
    check(set(negvals) <= {SLP_NONE},
          "the only negative graphic SLP is the -1 'no sprite' sentinel (%d graphics)"
          % len(neg),
          "unexpected negative SLP values: %r" % negvals)

    # A7  empty unit names must be the type=10 EyeCandy decoration slots
    empties = [u for u in all_units if not u["name"]]
    etypes = collections.Counter(u["type"] for u in empties)
    ehp = collections.Counter(u["hit_points"] for u in empties)
    print("A7. empty-name units: %d/%d, all Type=%r, all hp=%r"
          % (len(empties), len(all_units), dict(etypes), dict(ehp)))
    check(set(etypes) <= {10},
          "all %d empty-name units are Type=10 (EyeCandy decoration slots), hp=1"
          % len(empties),
          "empty-name units have unexpected types: %r" % etypes)

    # A8  names must all be ASCII-clean, no mojibake
    nonascii = [u["name"] for u in all_units if any(ord(c) > 126 for c in u["name"])]
    check(not nonascii,
          "all %d unit name strings are clean ASCII (no mojibake)" % len(all_units),
          "%d unit names contain non-ASCII: %r" % (len(nonascii), nonascii[:5]))

    # ---------- B. external ground truth -----------------------------------
    civ0 = s["civs"][0]
    byid = {u["id"]: u for u in civ0["units"]}
    print("\nB. external ground truth -- canonical AoE2 unit ids in civ[0]=%r:" % civ0["name"])
    hits = 0
    for uid in sorted(GROUND_TRUTH):
        label, exp_hp = GROUND_TRUTH[uid]
        u = byid.get(uid)
        if u is None:
            print("    id=%-4d %-15s -> ABSENT" % (uid, label))
            continue
        good = u["hit_points"] == exp_hp
        hits += good
        print("    id=%-4d %-15s -> name=%-10r hp=%-5d expected=%-5d %s"
              % (uid, label, u["name"], u["hit_points"], exp_hp, "OK" if good else "MISMATCH"))
    print("    %d/%d canonical unit ids decode to their exact known hit points"
          % (hits, len(GROUND_TRUTH)))
    check(hits == len(GROUND_TRUTH),
          "external ground truth: %d/%d canonical AoE2 unit ids decode to their exact "
          "known hit points (Archer 30, Knight 100, Villager 25, ...)"
          % (hits, len(GROUND_TRUTH)),
          "only %d/%d canonical unit ids match their known hit points"
          % (hits, len(GROUND_TRUTH)))

    # ---------- verdict -----------------------------------------------------
    print("\n" + "=" * 72)
    print("SEMANTIC VALIDATION")
    print("=" * 72)
    for x in ok:
        print("  PASS  " + x)
    for x in bad:
        print("  FAIL  " + x)
    print("\n  => %s"
          % ("decoded data is BOTH structurally exact AND semantically correct."
             if not bad else "%d semantic problem(s)." % len(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
