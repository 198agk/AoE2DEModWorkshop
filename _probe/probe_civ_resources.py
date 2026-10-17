"""The civ Resources array: the last per-civ structure nobody has tested.

`aoe2mod/dat/locate.py:296` does `r.f32_array(n)` and throws the result away.
Every other per-civ datum is now refuted as the gate for "can Aztecs build a
Hand Cannoneer":

  * membership in the civ's own unit array  -- unit 5 is in all 63
  * the unit record                          -- identical for all 63 but `civ`
  * effect type 2 / 102                      -- unit 5's enable is global (tech 85)
  * the dat TechTree                        -- one global object
  * transitive Chemistry availability        -- Chemistry is universal

So read the array that got dropped, and compare the civs that CAN build unit 5
against the ones that cannot.  If a resource index separates the two groups,
that is the gate.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                         # noqa: E402
import aoe2mod.game.civtechtrees as CT          # noqa: E402
from aoe2mod.dat import parser as P             # noqa: E402

tk = A.open_toolkit()
tk._ensure()

data, civs, civs_start, gv, tail, how = tk._parsed
trees = tk._trees()


def tree_status(civ_name, node_id, use=CT.UNIT_USE_TYPES):
    t = trees.get(CT.civ_file_stem(civ_name))
    return CT.node_status(t, node_id, use) if t else None


def read_civs_with_resources():
    """Re-walk from civs_start, capturing the Resources array walk_civ drops."""
    r = P.Reader(data, gv=gv)
    r.pos = civs_start
    out = []
    count = r.i16()
    for _ in range(count):
        player_type = r.u8()
        name = r.debug_string()[1]
        n = r.i16()
        tree_id = r.i16()
        team_bonus = r.i16()
        res = [r.f32() for _ in range(n)]
        r.u8()                                            # icon_set
        m = r.i16()
        ptrs = r.i32_array(m)
        for p in ptrs:
            if p != 0:
                r.skip(0)                                 # units consumed lazily
                break
        out.append({"name": name, "player_type": player_type, "tree_id": tree_id,
                    "team_bonus": team_bonus, "resources": res, "unit_ptrs": m})
        break                                             # one civ is enough for n
    return out, count


first, total = read_civs_with_resources()
print("civ count %d ; first civ %r resources length %d"
      % (total, first[0]["name"], len(first[0]["resources"])))
arr = first[0]["resources"]
nz = [(i, v) for i, v in enumerate(arr) if v != 0.0]
print("non-zero entries in the first civ's array: %d" % len(nz))
for i, v in nz[:25]:
    print("    res[%d] = %r" % (i, v))

# ---------------------------------------------------------------- per-civ sizes
print()
print("=" * 74)
print("Resources-array length per civ (re-walk, civs only, skipping units)")
print("=" * 74)

# Walk civs properly: we must skip unit bodies to reach the next civ.  Use the
# authoritative walker for the units, and only re-read the array header.
r = P.Reader(data, gv=gv)
r.pos = civs_start
count = r.i16()
lengths = {}
arrays = {}
for _ in range(count):
    r.u8()
    name = r.debug_string()[1]
    n = r.i16()
    r.i16()
    r.i16()
    res = [r.f32() for _ in range(n)]
    r.u8()
    m = r.i16()
    ptrs = r.i32_array(m)
    for p in ptrs:
        if p != 0:
            # consume one unit record using the product walker
            raise SystemExit("reached a unit body; use locate.walk_civ instead")
    lengths.setdefault(n, []).append(name)
    arrays[name] = res

print("distinct Resources-array lengths: %s"
      % {k: len(v) for k, v in sorted(lengths.items())})
print()
print("%-14s %-18s %s" % ("civ", "tree status of unit 5", "non-zero resources"))
for c in civs:
    nm = c["name"]
    if nm not in arrays:
        continue
    nz = [(i, round(v, 4)) for i, v in enumerate(arrays[nm]) if v != 0.0]
    print("%-14s %-18s %s" % (nm, tree_status(nm, 5), nz if nz else "-- none --"))
