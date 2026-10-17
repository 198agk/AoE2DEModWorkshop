# -*- coding: utf-8 -*-
r"""Why do 257 of 2528 units not land on a loose .sld?

My hypothesis was "nonzero slp id means legacy SLP resource".  Measurement said
no: 54% of nonzero-slp records DO resolve.  So find the real discriminator.

Candidate: the NAME SHAPE.  Modern DE loose files are lower-case, segmented with
underscores (`u_arc_archer_idleA_x1`).  Legacy resources are ALL-CAPS
abbreviations (`BRSRK_SN`), which is exactly what genieutils warns about
("heavily abbreviated, such as ARRG2NNE").
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
_on_disk = set(fn for fn in os.listdir(GP) if fn.endswith(".sld"))

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_g = tk._stats["graphics"]
_raw = tk._raw
_by_id = {x.get("id"): x for x in _g}

def fname(rec):
    if not isinstance(rec, dict):
        return None
    f = rec.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None

def shape(f):
    if f is None:
        return "no name"
    if "_" in f and f == f.lower():
        return "modern (lower_underscore)"
    if f == f.upper() and "_" not in f:
        return "legacy (ALLCAPS)"
    return "other"

_units = {}
for c in tk._civs:
    for u in c["units"]:
        _units.setdefault(u["id"], u)

print("CORPUS-WIDE: name shape vs whether the .sld exists")
_c = collections.Counter()
for x in _g:
    f = fname(x)
    ok = (f + ".sld") in _on_disk if f else False
    _c[(shape(f), ok)] += 1
for s in ("modern (lower_underscore)", "legacy (ALLCAPS)", "other", "no name"):
    y = _c[(s, True)]
    n = _c[(s, False)]
    print("   %-26s resolves %5d / %-5d (%5.1f%%)"
          % (s, y, y + n, 100.0 * y / max(1, y + n)))

print()
print("UNIT VIEW: the 257 unmatched, by name shape")
_unres = collections.Counter()
_res = collections.Counter()
for uid, u in _units.items():
    offs = u.get("_offs") or {}
    if "hit_points" not in offs:
        continue
    a, b = struct.unpack_from("<hh", _raw, offs["hit_points"] - 9)
    if a < 0:
        continue
    rec = _by_id.get(a)
    f = fname(rec)
    if f and (f + ".sld") in _on_disk:
        _res[shape(f)] += 1
    else:
        _unres[shape(f)] += 1
print("   resolved  : %s" % dict(_res))
print("   unresolved: %s" % dict(_unres))
print("   -> %s" % ("the name shape is the discriminator"
                    if _unres.get("modern (lower_underscore)", 0) == 0
                    else "modern names still fail: %d"
                         % _unres.get("modern (lower_underscore)", 0)))

print()
print("THE UNRESOLVED MODERN NAMES (if any) -- these would be real gaps")
_shown = 0
for uid, u in _units.items():
    offs = u.get("_offs") or {}
    if "hit_points" not in offs:
        continue
    a, b = struct.unpack_from("<hh", _raw, offs["hit_points"] - 9)
    if a < 0:
        continue
    rec = _by_id.get(a)
    f = fname(rec)
    if f and shape(f) == "modern (lower_underscore)" and (f + ".sld") not in _on_disk:
        if _shown < 10:
            print("   unit %-5d graphic %-6d file=%r slp=%s name=%r"
                  % (uid, a, f, (rec or {}).get("slp"), (rec or {}).get("name")))
        _shown += 1
print("   total modern-named misses: %d" % _shown)

print()
print("THE `file='W'` ODDITY (units 17/21/80/81/92)")
for uid in (17, 21, 80, 81, 92):
    u = _units.get(uid)
    if not u:
        continue
    a, b = struct.unpack_from("<hh", _raw, (u["_offs"])["hit_points"] - 9)
    rec = _by_id.get(a) or {}
    print("   unit %-4d graphic %-6d name=%-40r file=%r slp=%s"
          % (uid, a, rec.get("name"), rec.get("file"), rec.get("slp")))
# is the second element a working alternative?
_alt = 0
for uid, u in _units.items():
    offs = u.get("_offs") or {}
    if "hit_points" not in offs:
        continue
    a, b = struct.unpack_from("<hh", _raw, offs["hit_points"] - 9)
    fa = fname(_by_id.get(a))
    fb = fname(_by_id.get(b))
    if fa and (fa + ".sld") not in _on_disk and fb and (fb + ".sld") in _on_disk:
        _alt += 1
print("   units where the SECOND value resolves while the first does not: %d" % _alt)
