"""Can a reskin be a .dat retarget instead of 438 MB of copied pixels?

Idea under test: a unit record names ONE graphic id (`standing_graphic[0]`).
The engine then finds the sibling animations by the graphics record's `name`
field ("Sheep (Walk)").  So pointing the unit at the DONOR's graphic id would
give it the donor's whole animation set -- using files that already ship --
instead of copying every pixel under the target's filenames.

That is a 2-byte edit per unit record.  This probe measures, for the villager
family and the sheep donor:
  * what the retarget would be (per civ, because 6 Chronicles civs differ)
  * whether the donor's animation set covers the target's needs
  * the resulting mod size (the .dat only) against the copy approach
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, sys, collections

sys.path.insert(0, _HERE_PATH(".."))

import aoe2mod.api as A
from aoe2mod.game import sprites as SP
from aoe2mod.game import civtechtrees as CT
from aoe2mod.intent import reskin as RK

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(GAME)
tk._ensure()

idx = tk._reskin_art()
fam = tk._families()
members = fam.get(83) or [83]
print("family members:", len(members))

# per civ, resolve each member's art and the donor's art
tables = RK._units_by_id(tk._parsed[1])
civnames = [c["name"] for c in tk._parsed[1]]

want = ["attack", "carry", "death", "decay", "idle", "idlec", "seed", "task", "walk", "work"]

# the donor: unit 594 (Sheep)
rows = []
per_civ_targets = collections.defaultdict(set)
for ci, table in enumerate(tables):
    d_rec = table.get(594)
    if d_rec is None:
        continue
    d_art = idx.art(d_rec)
    d_keys = set(d_art.get("tokens") or {})
    missing = [k for k in want if k not in d_keys]
    rows.append((civnames[ci], d_art.get("stem"), len(d_keys), tuple(missing)))
    for m in members:
        rec = table.get(m)
        if rec is None:
            continue
        a = idx.art(rec)
        if a.get("kind") != "loose":
            continue
        per_civ_targets[civnames[ci]].add((m, a.get("stem"), a.get("graphic_id")))

print()
print("donor 'Sheep' per civ (stem, #keys, keys it lacks):")
seen = set()
for r in rows:
    key = (r[1], r[2], r[3])
    if key in seen:
        continue
    seen.add(key)
    print("   %-14s stem=%-22s keys=%d missing=%s" % (r[0], r[1], r[2], r[3]))
print("   (distinct donor shapes: %d across %d civs)" % (len(seen), len(rows)))

# how many distinct (member -> donor graphic id) retargets?
print()
tot = 0
for civ in list(per_civ_targets)[:3]:
    print("civ %-14s members with art: %d" % (civ, len(per_civ_targets[civ])))
    for m, stem, gid in sorted(per_civ_targets[civ])[:6]:
        print("     unit %-5d stem=%-24s standing graphic id=%s" % (m, stem, gid))
for civ in per_civ_targets:
    tot += len(per_civ_targets[civ])
print("total (civ, member) pairs: %d" % tot)

# size comparison
copy_bytes = 0
out = os.path.join(_HERE_PATH("_probe"), "out_dshtest_v12")
for r, _, fs in os.walk(out):
    for f in fs:
        copy_bytes += os.path.getsize(os.path.join(r, f))
dat = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
print()
print("copy approach (v12)      : %d B (%.1f MB)" % (copy_bytes, copy_bytes / 1e6))
print("retarget approach (.dat) : %d B (%.1f MB)" % (os.path.getsize(dat), os.path.getsize(dat) / 1e6))
print("ratio                    : %.1fx smaller" % (copy_bytes / os.path.getsize(dat)))
