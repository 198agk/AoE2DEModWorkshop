# -*- coding: utf-8 -*-
r"""Measure the unit -> sprite chain properly, after two of my own bugs.

Bug 1: I keyed `.sld` stems on the full filename, so a name ending in `_x1`
       could never match its `_x2` sibling -- the "x2=0" result was mine.
Bug 2: I assumed the unit record carries a field named `standing_graphic`.
       It does not: `parse_dat.read_unit` reads `r.i16_array(2)` and DROPS it.

So this probe re-reads the field from bytes.  Three questions:
  A  what does `graphics[i]['file']` actually contain (including misses)?
  B  of the pairs, which int16 indexes the graphics array?
  C  for a named unit, what .sld do we land on?
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A
import aoe2mod.dat.parser as P
from aoe2mod.dat import locate as L

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

# stems WITHOUT the _x1/_x2 suffix -> list of real files
_stems = collections.defaultdict(list)
for fn in os.listdir(GP):
    if fn.endswith(".sld") and len(fn) > 7:
        _stems[fn[:-7]].append(fn)
print("sld files: %d   distinct stems: %d" % (sum(len(v) for v in _stems.values()),
                                              len(_stems)))

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_g = tk._stats["graphics"]

print()
print("A  WHAT IS IN `graphics[i]['file']` ?")
c = collections.Counter()
for x in _g:
    f = x.get("file")
    if not isinstance(f, str):
        c["not-a-string:%r" % type(f).__name__] += 1
    elif f == "":
        c["empty"] += 1
    elif f.strip() in ("None", "none", "NULL"):
        c["literal-None"] += 1
    elif f.strip() in _stems:
        c["exact stem hit"] += 1
    else:
        c["string but no .sld"] += 1
for k, v in c.most_common():
    print("     %-24s %d" % (k, v))
_ex = [x for x in _g if isinstance(x.get("file"), str)
       and x["file"].strip() and x["file"].strip() not in _stems][:8]
for x in _ex:
    print("        miss: file=%r name=%r slp=%s id=%s"
          % (x["file"], x["name"], x.get("slp"), x.get("id")))

print()
print("     -- x1 AND x2 for the hits --")
_only1 = _only2 = _both = 0
for f in {x["file"].strip() for x in _g if isinstance(x.get("file"), str)}:
    fs = _stems.get(f)
    if not fs:
        continue
    h1 = any(n.endswith("_x1.sld") for n in fs)
    h2 = any(n.endswith("_x2.sld") for n in fs)
    if h1 and h2:
        _both += 1
    elif h1:
        _only1 += 1
    elif h2:
        _only2 += 1
print("     both x1 and x2 : %d" % _both)
print("     x1 only        : %d" % _only1)
print("     x2 only        : %d" % _only2)

print()
print("B  WHICH int16 OF StandingGraphic INDEXES THE GRAPHICS ARRAY?")
_order = sorted(_g, key=lambda x: (x.get("id") is None, x.get("id")))
_by_pos = {}
for i, x in enumerate(_g):
    _by_pos[i] = x
_by_id = {}
for x in _g:
    if x.get("id") is not None:
        _by_id.setdefault(x["id"], x)
print("     array length %d   distinct `id` values %d" % (len(_g), len(_by_id)))

# read the raw pair straight out of the unit record, using the locator's own walk
_civs = tk._civs
_raw = tk._raw
_marks = {}

def pair_for(unit):
    off = unit.get("_offs", {}).get("class")
    return None

# The locator's Orec records marks; re-walk one civ to get the offset of `class`.
_r = L.Orec(_raw, 0, tk._parsed[3]) if hasattr(L, "Orec") else None
print("     (walk_unit marks available: %s)" % (hasattr(L, "Orec")))

_u83 = None
for c in _civs:
    for u in c["units"]:
        if u["id"] == 83:
            _u83 = u
            break
    if _u83:
        break
print("     unit 83 (_offs keys): %s" % sorted((_u83.get("_offs") or {}).keys()))

# HIT POINTS offset is recorded; StandingGraphic sits 7 bytes earlier
# (i16 class, then i16 x2, i16 dying, i16 undead, u8 undeadmode).
import struct
_hp_off = _u83["_offs"]["hit_points"]
_sg_off = _hp_off - 7
_a, _b = struct.unpack_from("<hh", _raw, _sg_off)
print("     unit 83 StandingGraphic = (%d, %d)" % (_a, _b))
for _v in (_a, _b):
    _rec = _by_pos.get(_v)
    _rid = _by_id.get(_v)
    print("        value %-6d -> graphics[%d] file=%r   | by-id file=%r"
          % (_v, _v, (_rec or {}).get("file"), (_rid or {}).get("file")))

print()
print("C  NAMED UNITS -> .sld")
_iu = tk._stats["unit_headers"]
_names = {}
for u in _iu:
    _names.setdefault(u.get("id"), u.get("name"))
for uid in (83, 4, 38, 74, 93, 125, 448, 692):
    _u = None
    for c in _civs:
        for u in c["units"]:
            if u["id"] == uid:
                _u = u
                break
        if _u:
            break
    if not _u:
        continue
    _o = _u["_offs"]["hit_points"] - 7
    _x, _y = struct.unpack_from("<hh", _raw, _o)
    for label, v in (("first", _x), ("second", _y)):
        _rec = _by_pos.get(v)
        _fs = _stems.get(((_rec or {}).get("file") or "").strip(), [])
        print("     unit %-4d %-22s %-7s=%-6d -> %s"
              % (uid, _names.get(uid), label, v,
                 ", ".join(sorted(_fs)) if _fs else repr((_rec or {}).get("file"))))
