"""The dat's OWN tech tree, and the per-civ unit pointer array.

Two dat-side structures neither the intents nor the probe suite have ever read:

1. The single `TechTree` object at the tail of the .dat (genieutils
   `DatFile.h`: `genie::TechTree TechTree;`).  Its `UnitConnection` records carry
   `Status`, `RequiredResearch` ("Upgrades unit") and `EnablingResearch` ("Makes
   available.  Used by units, which need a research to be available") -- and our
   parser reads and throws all three away (`parser.py:read_unit_connection`).

2. `Civ.UnitPointers` -- a per-civ int32 array.  Every civ reports
   `unit_pointers_total == 2750`, but the number of NON-ZERO pointers differs
   (Gaia 2693, British 2164).  That is the classic AoK availability mechanism:
   a zero pointer means "this civilization does not have this unit".

The question both must answer: does EITHER of them separate the civs that can
build Hand Cannoneer (24) from the 38 the tree calls NotAvailable?

Key facts to beat (measured earlier, pinned in test_dat_availability_layers.py):
  * 3,686/3,686 tree rows name a unit present in that civ's own unit list, and
    all 571 NotAvailable rows are present too.
  * the per-civ unit RECORD differs only in `civ` plus 4 cosmetic fields.
  * the type-2 Enable layer matches 11 of 12 unique units but calls Hand
    Cannoneer globally enabled.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.parser as P  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, tail, _how = tk._parsed
tt = tk._stats["tech_tree"]
print("=" * 72)
print("1. the dat's own TechTree section (counts as the parser recorded them)")
print("=" * 72)
print("   %s" % tt)

# --- walk it raw, capturing the fields our parser discards ----------------
# `tail` from locate() is the start of the TECH section (0x058C1923), not the
# TechTree.  The TechTree is the very last structure in the file: after the 1,510
# techs come stage 10's seven i32 scalars, then `read_tech_tree`.  Derive the
# offset instead of hardcoding it: walk the parser to the end of stage 9 and read
# its recorded boundary.
import io as _io
import contextlib as _ctx

_p = P.Parser(data)
with _ctx.redirect_stdout(_io.StringIO()):
    try:
        _p.parse(stop_after=9)
    except SystemExit:
        pass
_tech_end = _p.stage_offsets[-1][2]
assert _tech_end == 0x058E2A14, "tech array boundary moved: %#x" % _tech_end

r = P.Reader(data, gv=gv)
r.pos = _tech_end + 7 * 4
tt_start = r.pos
n_ages = r.u8()
n_bldg = r.u8()
n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
n_res = r.i16() if r.gv == P.GV_CCV2 else r.u8()
groups = r.i32()
print("   TechTree starts at 0x%08X (tech array ends 0x%08X)"
      % (tt_start, _tech_end))
print("   parser recorded : %s" % tt)
print("   raw walk: ages=%d buildings=%d units=%d research=%d groups=%d"
      % (n_ages, n_bldg, n_units, n_res, groups))
assert (n_ages, n_bldg, n_units, n_res) == (tt["ages"], tt["buildings"],
                                            tt["units"], tt["research"]), (
    "the raw walk must reproduce the parser's counts, or the offset is wrong")

age_status = []
for _ in range(n_ages):
    r.i32(); age_status.append(r.u8())
    for _ in range(3):
        k = r.u8()
        if k:
            r.i32_array(k)
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()

b_stat, b_enab = [], []
for _ in range(n_bldg):
    r.i32(); b_stat.append(r.u8())
    for _ in range(3):
        k = r.u8()
        if k:
            r.i32_array(k)
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.u8(); r.skip(5); r.skip(5); r.i32(); b_enab.append(r.i32())

u_id, u_stat, u_upper, u_req, u_enab = [], [], [], [], []
for _ in range(n_units):
    u_id.append(r.i32())
    u_stat.append(r.u8())
    u_upper.append(r.i32())
    r.i32(); r.i32_array(10); r.i32_array(10)
    r.i32()
    k = r.u8()
    if k:
        r.i32_array(k)
    r.i32()
    u_req.append(r.i32())
    r.i32()
    u_enab.append(r.i32())

print("   age Status        : %s" % Counter(age_status).most_common())
print("   building Status   : %s" % Counter(b_stat).most_common())
print("   unit Status       : %s" % Counter(u_stat).most_common())
print("   unit RequiredResearch distinct=%d %s"
      % (len(set(u_req)), Counter(u_req).most_common(6)))
print("   unit EnablingResearch distinct=%d %s"
      % (len(set(u_enab)), Counter(u_enab).most_common(6)))
print("   unit UpperBuilding distinct=%d" % len(set(u_upper)))

print()
print("=" * 72)
print("2. do the two sharpest units appear in the dat's tree connections?")
print("=" * 72)
for uid, label in ((5, "Hand Cannoneer"), (21, "War Galley"),
                   (8, "Longbowman"), (2550, "Champi Scout")):
    if uid in u_id:
        i = u_id.index(uid)
        print("   %-16s id=%-5d status=%-3d upper=%-6d required=%-6d enabling=%-6d"
              % (label, uid, u_stat[i], u_upper[i], u_req[i], u_enab[i]))
    else:
        print("   %-16s NOT in the dat's tree connections" % label)
print("   connections total %d, distinct ids %d" % (len(u_id), len(set(u_id))))

print()
print("=" * 72)
print("3. Civ.UnitPointers -- the classic zero-pointer gate")
print("=" * 72)
print("   civ                    pointers  nonzero  has 5  has 21  has 2550")
trees = CT.load_trees(tk.game_root)
by_stem = {CT.civ_file_stem(c["name"]): c for c in civs}


def status_of(stem, uid):
    tax = trees.get(stem)
    if tax is None:
        return "(no file)"
    for row in CT.unit_rows(tax):
        if row.get("Node ID") == uid:
            return row.get("Node Status")
    return None


sample = ["BRITONS", "GOTHS", "TURKS", "SPANISH", "INDIANS", "MONGOLS",
          "JAPANESE", "CELTS", "ITALIANS", "KOREANS"]
for stem in sample:
    c = by_stem.get(stem)
    if c is None:
        continue
    ids = {u["id"] for u in c["units"]}
    print("   %-18s %-9d %-8d %-6s %-7s %-8s"
          % (c["name"], c["unit_pointers_total"], len(ids),
             "yes" if 5 in ids else "no", "yes" if 21 in ids else "no",
             "yes" if 2550 in ids else "no"))

print()
print("   cross-tab over every civ, unit 5 (Hand Cannoneer):")
tab = Counter()
for stem, tax in trees.items():
    c = by_stem.get(stem)
    if c is None:
        continue
    ids = {u["id"] for u in c["units"]}
    st = status_of(stem, 5)
    can = st is not None and st != "NotAvailable"
    tab[(can, 5 in ids)] += 1
for k, v in sorted(tab.items()):
    print("     can_build=%-5s present_in_unit_list=%-5s  %d" % (k[0], k[1], v))
print("   -> if presence ever separates the two, this table shows it")
