# -*- coding: utf-8 -*-
"""Signal check for the remaining bare reads in the locator.

Round 9 measured t50's seven sub-fields and bound two of them.  Several more
locator reads were still bare (no mark, no dict entry), so nothing could ever
reach them and no test would notice -- nobody asks about a field with no name.

This probe marks them all first, then asks the only two questions that decide
whether one should become an intent:

  1. does it carry SIGNAL  (distinct values / non-default ratio), and
  2. is the VALUE SAFE to write (plain scalar, or a reference to another
     entity / a sentinel / a UI-layer id)?

Question 2 is the one that has bitten before: attack_graphic has 743 distinct
values and is still not an intent, because it names a graphic record.

Read-only against BASE.
"""
import collections
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from aoe2mod.dat import parser as P      # noqa: E402
from aoe2mod.dat import locate as L      # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

# (attr name, C++ field, default, kind) -- kind decides safety:
#   "scalar"  -> a plain number stored on this record
#   "ref"     -> an id naming ANOTHER record (needs an existence guard)
#   "ui"      -> a presentation-layer id (belongs to a UI/graphics intent)
#   "sentinel"-> carries a documented sentinel that is not a value
UNIT_FIELDS = [
    ("garrison_capacity", "GarrisonCapacity", 0, "scalar"),
    ("sort_number", "SortNumber", 0, "ui"),
]

T50_FIELDS = [
    ("defense_terrain_bonus", "DefenseTerrainBonus", 0, "scalar"),
    ("bonus_damage_resistance", "BonusDamageResistance", 0.0, "scalar"),
    ("blast_width", "BlastWidth", 0.0, "scalar"),
    ("projectile_unit_id", "ProjectileUnitID", -1, "ref"),
    ("break_off_combat", "BreakOffCombat", 0, "scalar"),
    ("frame_delay", "FrameDelay", 0, "scalar"),
    ("attack_graphic", "AttackGraphic", -1, "ui"),
]


def stats(name, field, default, kind, values):
    n = len(values)
    if not n:
        print("  %-24s NO VALUES" % name)
        return None
    c = collections.Counter(values)
    nd = sum(1 for v in values if v != default)
    print("  %-24s %-22s n=%6d distinct=%5d  non-default %6d (%5.1f%%)  top=%s"
          % (name, field, n, len(c), nd, 100.0 * nd / n, c.most_common(3)))
    return c


def main():
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _, gv, tail = L.locate(data, parser=p)

    units = [u for cv in civs for u in cv["units"]]
    print("=== unit-record bare reads ===")
    for name, field, default, kind in UNIT_FIELDS:
        vals = [u[name] for u in units if name in u]
        stats(name, field, default, kind, vals)

    print()
    print("=== type50 bare reads ===")
    t50s = [u["type50"] for u in units if u.get("type50")]
    print("  records carrying a type50 block: %d" % len(t50s))
    for name, field, default, kind in T50_FIELDS:
        vals = [t[name] for t in t50s if name in t]
        stats(name, field, default, kind, vals)

    print()
    print("=== how many marks does the walker now record? ===")
    msets = collections.Counter()
    for u in units:
        msets[len(u.get("_offs") or {})] += 1
    print("  distinct mark-count per unit record: %s" % dict(msets))
    allm = set()
    for u in units:
        allm |= set((u.get("_offs") or {}).keys())
    print("  union of marks (%d): %s" % (len(allm), sorted(allm)))


if __name__ == "__main__":
    main()
