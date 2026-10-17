# -*- coding: utf-8 -*-
"""Audit probe 19: decompress the four .dat copies (raw deflate, wbits=-15) and
read the CONTROL (Villager hit_points) + subjects."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, sys, io, zlib, contextlib
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
from aoe2mod.dat import parser as P

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LOCAL = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local"
OUT = _HERE_PATH("_probe", "out_smoke5")
REL = r"resources\_common\dat\empires2_x2_p1.dat"

TARGETS = [
    ("SHIPPED", os.path.join(GAME, REL)),
    ("BUNDLE ", os.path.join(LOCAL, "aoe2mod Bundle VillagerHP plus Britons HandCannon", REL)),
    ("SMOKE5 ", os.path.join(LOCAL, "aoe2mod Smoke5 TreeVsPanel", REL)),
    ("OUT    ", os.path.join(OUT, REL)),
]

def inflate(raw):
    for wb in (-15, 15, 31):
        try:
            return zlib.decompress(raw, wb), wb
        except Exception:
            continue
    return None, None

res = {}
for tag, p in TARGETS:
    raw = open(p, "rb").read()
    data, wb = inflate(raw)
    print()
    print("-- %s size=%d inflate_wbits=%s inflated=%s" % (tag, len(raw), wb,
          len(data) if data else None))
    if data is None:
        print("   INFLATE FAILED; first 8 bytes: %r" % raw[:8])
        continue
    pr = P.Parser(data)
    got = []
    pr._collect_unit = lambda u: got.append(dict(u))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            pr.parse()
    except Exception as e:
        print("   PARSE FAIL %s: %s" % (type(e).__name__, e))
        continue
    print("   units collected: %d" % len(got))
    byid = {}
    for u in got:
        byid.setdefault(u.get("id"), []).append(u)
    res[tag.strip()] = byid
    for uid in (83, 13, 545, 74, 2550):
        us = byid.get(uid) or []
        print("   id %-5s n=%-3d %s" % (uid, len(us), ", ".join(
            "hp=%s name=%s" % (u.get("hit_points"), u.get("name")) for u in us[:2]) or "ABSENT"))

print()
print("=" * 78)
print("19b: the CONTROL -- Villager (id 83) hit_points per copy")
print("=" * 78)
for tag in ("SHIPPED", "BUNDLE", "SMOKE5", "OUT"):
    us = (res.get(tag) or {}).get(83) or []
    print("   %-8s hp=%s" % (tag, us[0].get("hit_points") if us else "ABSENT"))
