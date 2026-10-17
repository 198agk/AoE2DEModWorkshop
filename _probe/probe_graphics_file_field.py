# -*- coding: utf-8 -*-
r"""Is `graphics[i]['file']` the .sld filename?  Measure it, do not assume it.

The first probe showed `file='b_east_archery_range_age2_rubble_x1'` and the tree
really contains `b_east_archey_range_age2_rubble_x1.sld` (x1 AND x2).  If that
holds corpus-wide, then the unit -> sprite index this project has been calling
"the single highest-value missing piece" already exists inside the .dat, and
nothing needs to be guessed from name conventions.

Four measurements:
  A  how many `file` values have a matching .sld on disk (x1 and x2),
  B  which units reach which graphics (unit record -> graphics id -> file),
  C  the reverse map, and whether it is 1:1,
  D  the two-sided check: names that do NOT match, and WHY.
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

fails = []
def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name[:72], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_g = tk._stats["graphics"]

_on_disk = {}
for fn in os.listdir(GP):
    if fn.endswith(".sld"):
        _on_disk.setdefault(fn[:-4], []).append(fn)

print("A  DOES `file` NAME A REAL .sld?")
_named_file = [x for x in _g if (x.get("file") or "").strip()]
_exact = _x1 = _x2 = 0
_missing = []
for x in _named_file:
    stem = x["file"].strip()
    hits = _on_disk.get(stem)
    if hits is None:
        hits = _on_disk.get(stem[:-3] if stem.endswith("_x1") else stem)
    if hits:
        _exact += 1
        if stem + ".sld" in hits:
            _exact_plain = True
        if any(h.endswith("_x1.sld") for h in hits):
            _x1 += 1
        if any(h.endswith("_x2.sld") for h in hits):
            _x2 += 1
    elif len(_missing) < 12:
        _missing.append(stem)
print("     graphics records with a `file` string : %d" % len(_named_file))
print("     of those, a matching .sld on disk     : %d (%.1f%%)"
      % (_exact, 100.0 * _exact / max(1, len(_named_file))))
print("       ... offering an _x1 file            : %d" % _x1)
print("       ... offering an _x2 file            : %d" % _x2)
print("     first misses: %s" % _missing)
check("the .dat's `file` field names real .sld files (>90%)",
      _exact > 0.9 * len(_named_file),
      "%d/%d" % (_exact, len(_named_file)))
check("practically all of them come as an x1/x2 pair",
      _x1 > 0.95 * _exact and _x2 > 0.95 * _exact,
      "x1=%d x2=%d of %d" % (_x1, _x2, _exact))

print()
print("B  UNIT -> GRAPHICS -> FILE  (is the chain unbroken?)")
_civs = tk._civs
_samples = {}
for c in _civs:
    for u in c["units"]:
        _samples.setdefault(u["id"], u)
print("     distinct unit ids                : %d" % len(_samples))
_id_to_gfx = {x.get("id"): x for x in _g}
def gfx_file(u):
    for k in ("standing_graphic", "graphic_id", "graphics_id"):
        gid = u.get(k)
        if isinstance(gid, int) and gid in _id_to_gfx:
            return gid, (_id_to_gfx[gid].get("file") or "")
    return None, ""
_u_keys = sorted(_samples[83].keys()) if 83 in _samples else []
print("     a unit record's keys             : %s" % _u_keys)
_resolved = 0
_ex = []
for uid, u in _samples.items():
    gid, f = gfx_file(u)
    if f:
        _resolved += 1
        if len(_ex) < 5:
            _ex.append((uid, u.get("name"), gid, f))
print("     units whose graphic resolves     : %d" % _resolved)
for e in _ex:
    print("        unit %-5s %-22r -> graphic %-6s %s" % e)

print()
print("C  REVERSE MAP: is one file shared by many units?")
_rev = collections.defaultdict(set)
for uid, u in _samples.items():
    gid, f = gfx_file(u)
    if f:
        _rev[f].add(uid)
print("     distinct files reachable         : %d" % len(_rev))
_fan = collections.Counter(len(v) for v in _rev.values())
print("     units per file histogram         : %s" % dict(sorted(_fan.items())[:8]))

print()
print("D  WHAT THE MISSES ARE")
for m in _missing[:12]:
    near = [k for k in _on_disk if m.lower() in k.lower()][:3]
    print("     %-46r near: %s" % (m, near))

print()
if fails:
    print("KERNEL GFX: %d FAILED" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("KERNEL GFX: the .dat already contains the unit -> sprite index.")
