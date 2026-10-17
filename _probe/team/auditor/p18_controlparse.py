# -*- coding: utf-8 -*-
"""Audit probe 18: parse all four .dat copies and compare the CONTROL
(Villager hit_points) plus the two subjects, to prove/disprove the control's
attribution power."""
import os, sys, json
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod.dat import parser as P

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LOCAL = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\out_smoke5"
REL = r"resources\_common\dat\empires2_x2_p1.dat"

TARGETS = [
    ("SHIPPED", os.path.join(GAME, REL)),
    ("BUNDLE ", os.path.join(LOCAL, "aoe2mod Bundle VillagerHP plus Britons HandCannon", REL)),
    ("SMOKE5 ", os.path.join(LOCAL, "aoe2mod Smoke5 TreeVsPanel", REL)),
    ("OUT    ", os.path.join(OUT, REL)),
]


def allunits(path):
    pr = P.Parser(open(path, "rb").read())
    got = []
    pr._collect_unit = lambda u: got.append(dict(u))
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pr.parse()
    return got, pr


print("=" * 78)
print("18a: control (Villager) + subjects in each .dat copy")
print("=" * 78)
res = {}
for tag, p in TARGETS:
    print()
    print("-- %s %s (%d B)" % (tag, p, os.path.getsize(p)))
    try:
        units, pr = allunits(p)
    except Exception as e:
        print("   PARSE FAIL %s: %s" % (type(e).__name__, e))
        continue
    print("   units collected: %d" % len(units))
    byid = {}
    for u in units:
        byid.setdefault(u.get("id"), []).append(u)
    res[tag.strip()] = byid
    for uid in (74, 2550, 83, 13, 545):
        us = byid.get(uid) or []
        if us:
            print("   id %-5s n=%-4d %s" % (uid, len(us),
                  ", ".join("hp=%s name=%s" % (u.get("hit_points"), u.get("name")) for u in us[:3])))
        else:
            print("   id %-5s ABSENT" % uid)

print()
print("=" * 78)
print("18b: control comparison -- does the control DISTINGUISH smoke5 from bundle?")
print("=" * 78)
for uid in (83, 13, 545):
    row = []
    for tag in ("SHIPPED", "BUNDLE", "SMOKE5", "OUT"):
        us = (res.get(tag) or {}).get(uid) or []
        row.append("%s=%s" % (tag, us[0].get("hit_points") if us else "ABSENT"))
    print("   id %-5s %s" % (uid, "  |  ".join(row)))
