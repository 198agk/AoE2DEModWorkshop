# -*- coding: utf-8 -*-
r"""Settle the unit -> sprite chain by measurement, after fixing two of my bugs.

Bug A  `graphics[i]['file']` already ENDS in `_x1`; the file on disk is exactly
       that string + ".sld".  My previous probe stripped `_x1.sld` off the
       on-disk name, so nothing could ever match.
Bug B  StandingGraphic is 9 bytes before `hit_points`, not 7
       (class i16 + pair i16x2 + dying i16 + undead i16 + mode u8).

Then the real question: is the pair's index into the graphics array by ARRAY
POSITION or by the record's own `id` field?  Both are tried; the one with the
better on-disk hit rate is the answer.
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

_on_disk = set()
for fn in os.listdir(GP):
    if fn.endswith(".sld"):
        _on_disk.add(fn)
print("sld files on disk: %d" % len(_on_disk))

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_g = tk._stats["graphics"]
_raw = tk._raw

def fname(rec):
    if not isinstance(rec, dict):
        return None
    f = rec.get("file")
    if not isinstance(f, str) or not f.strip() or f.strip() == "None":
        return None
    return f.strip()

_by_pos = list(_g)
_by_id = {}
_dup = 0
for x in _g:
    i = x.get("id")
    if i in _by_id:
        _dup += 1
    _by_id.setdefault(i, x)
print("graphics: %d records, %d distinct ids, %d duplicate ids"
      % (len(_g), len(_by_id), _dup))

print()
print("A  HOW MANY RECORDS NAME A REAL .sld (correct keying)?")
_n = _hit = 0
for x in _g:
    f = fname(x)
    if f is None:
        continue
    _n += 1
    if f + ".sld" in _on_disk:
        _hit += 1
print("     records with a usable file string : %d of %d" % (_n, len(_g)))
print("     ... of which the .sld exists      : %d (%.1f%%)"
      % (_hit, 100.0 * _hit / max(1, _n)))
_none = sum(1 for x in _g if isinstance(x.get("file"), str)
            and x["file"].strip() == "None")
_empty = sum(1 for x in _g if not (x.get("file") or "").strip())
print("     file is the literal text \"None\"  : %d" % _none)
print("     file is empty                     : %d" % _empty)

print()
print("B  WHICH INDEXING?  unit.StandingGraphic -> graphics record")
_units = {}
for c in tk._civs:
    for u in c["units"]:
        _units.setdefault(u["id"], u)
print("     distinct unit ids                 : %d" % len(_units))

_scores = collections.Counter()
_miss_ex = collections.defaultdict(list)
for uid, u in _units.items():
    offs = u.get("_offs") or {}
    if "hit_points" not in offs:
        continue
    base = offs["hit_points"] - 9
    a, b = struct.unpack_from("<hh", _raw, base)
    for slot, v in (("first", a), ("second", b)):
        for scheme, tbl in (("by_pos", _by_pos), ("by_id", _by_id)):
            if scheme == "by_pos":
                rec = tbl[v] if 0 <= v < len(tbl) else None
            else:
                rec = tbl.get(v)
            if not isinstance(rec, dict):
                _scores[(slot, scheme, "no-record")] += 1
                continue
            f = fname(rec)
            if f is None:
                _scores[(slot, scheme, "no-file")] += 1
            elif f + ".sld" in _on_disk:
                _scores[(slot, scheme, "HIT")] += 1
            else:
                _scores[(slot, scheme, "file-not-on-disk")] += 1
                if len(_miss_ex[(slot, scheme)]) < 4:
                    _miss_ex[(slot, scheme)].append((uid, v, f))

for slot in ("first", "second"):
    for scheme in ("by_pos", "by_id"):
        h = _scores[(slot, scheme, "HIT")]
        tot = sum(_scores[(slot, scheme, k)]
                  for k in ("HIT", "file-not-on-disk", "no-file", "no-record"))
        print("     %-7s %-7s HIT %5d / %-5d  (%.1f%%)   %s"
              % (slot, scheme, h, tot, 100.0 * h / max(1, tot),
                 {k[2]: _scores[(slot, scheme, k)]
                  for k in ("file-not-on-disk", "no-file", "no-record")}))
        for e in _miss_ex[(slot, scheme)]:
            print("          miss unit %-5d value %-6d file=%r" % e)

print()
print("C  DO NAMED UNITS LAND ON A SENSIBLE SPRITE?")
_hdr = tk._stats["unit_headers"]
_nm = {}
for h in _hdr:
    _nm.setdefault(h.get("id"), h.get("name"))
for uid in (83, 4, 38, 74, 93, 125, 448, 692, 13, 41):
    u = _units.get(uid)
    if not u:
        continue
    base = (u.get("_offs") or {}).get("hit_points", 0) - 9
    a, b = struct.unpack_from("<hh", _raw, base)
    ra = (_by_id.get(a) if a in _by_id else (_by_pos[a] if 0 <= a < len(_by_pos) else None))
    rb = (_by_id.get(b) if b in _by_id else (_by_pos[b] if 0 <= b < len(_by_pos) else None))
    print("     unit %-5d %-18r  pair=(%d, %d)  id->(%s | %s)"
          % (uid, _nm.get(uid), a, b, fname(ra), fname(rb)))
