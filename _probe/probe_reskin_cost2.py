# -*- coding: utf-8 -*-
"""Reskin cost, deduplicated.  Also: why did the Barracks age-variant pair
report ZERO pairs instead of refusing?"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

ROOT = _HERE_PATH()
sys.path.insert(0, ROOT)
import aoe2mod.api as A
from aoe2mod.game import sprites as S

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk._ensure()
idx = S.art_index(GAME, tk._stats["graphics"])
G = S.graphics_dir(GAME)

def find_civ(name):
    for i, c in enumerate(tk._civs):
        if c["name"] == name:
            return i
    return None

def rec(uid, ci):
    for u in tk._civs[ci]["units"]:
        if u["id"] == uid:
            return u

def cost(target, donor, ci):
    t, d = rec(target, ci), rec(donor, ci)
    if t is None or d is None:
        return None
    ta, da = idx.art(t), idx.art(d)
    pairs, unmapped, extra = S.plan_swap(ta, da)
    files = {}
    for tn, dn in pairs:
        for suffix in ("_x1", "_x2"):
            tb = (tn[:-3] + suffix) if tn.endswith("_x1") else tn
            db = (dn[:-3] + suffix) if dn.endswith("_x1") else dn
            p = os.path.join(G, db + ".sld")
            files[tb + ".sld"] = os.path.getsize(p) if os.path.exists(p) else None
    return ta, da, pairs, unmapped, files

print("=" * 78)
print("1  Archer(4) <- Longbowman(8): the SAME target in every civilization")
print("=" * 78)
allfiles = {}
stems = {}
for ci, c in enumerate(tk._civs):
    r = cost(4, 8, ci)
    if r is None:
        continue
    ta, da, pairs, unmapped, files = r
    stems.setdefault((ta.get("stem"), da.get("stem")), []).append(c["name"])
    for k, v in files.items():
        allfiles[k] = v
print("  (target stem, donor stem) -> civs")
for k, v in sorted(stems.items(), key=lambda kv: -len(kv[1])):
    print("    %-22s <- %-22s  %d civs  e.g. %s"
          % (k[0], k[1], len(v), ", ".join(sorted(v)[:4])))
known = {k: v for k, v in allfiles.items() if v is not None}
print("  DISTINCT files a mod must carry : %d" % len(allfiles))
print("  ...total size                   : %.1f MB"
      % (sum(known.values()) / 1048576.0))
for k in sorted(allfiles):
    print("    %-34s %s" % (k, ("%,d B".replace(",", "") % allfiles[k])
                            if allfiles[k] else "MISSING"))

print()
print("=" * 78)
print("2  the Barracks age-variant pair reported 0 pairs -- why?")
print("=" * 78)
for ci, label in ((find_civ("British"), "British"),):
    for uid in (12, 498, 132, 20):
        u = rec(uid, ci)
        if u is None:
            print("  unit %-5d %s: no record" % (uid, label))
            continue
        a = idx.art(u)
        print("  unit %-5d %-42s kind=%-6s stem=%-26s anims=%s"
              % (uid, str(a and a.get("file")), a and a.get("kind"),
                 a and a.get("stem"), a and a.get("anims")))
    a12, a498 = idx.art(rec(12, ci)), idx.art(rec(498, ci))
    print("  names of 12 : %s" % [n for n, _ in (a12.get("anims") or [])])
    print("  names of 498: %s" % [n for n, _ in (a498.get("anims") or [])])

print()
print("=" * 78)
print("3  smallest useful reskins")
print("=" * 78)
cases = [
    ("Archer <- Longbowman", 4, 8, 1),
    ("Villager <- Archer", 83, 4, 1),
    ("Spearman <- Militia", 93, 74, 1),
    ("Barracks <- Feudal Barracks", 12, 498, 1),
    ("Militia <- Villager", 74, 83, 1),
    ("Champi Scout <- Archer", 2550, 4, find_civ("Incas")),
    ("Gold Mine <- Stone Mine", 66, 102, find_civ("British")),
    ("Sheep <- Deer", 594, 597, find_civ("British")),
]
for label, t, d, ci in cases:
    if ci is None:
        print("  %-30s (civ not found)" % label)
        continue
    try:
        r = cost(t, d, ci)
    except S.SpriteError as exc:
        print("  %-30s REFUSED: %s" % (label, exc))
        continue
    if r is None:
        print("  %-30s (a record is missing)" % label)
        continue
    ta, da, pairs, unmapped, files = r
    sz = sum(v for v in files.values() if v)
    miss = [k for k, v in files.items() if v is None]
    print("  %-30s %d pairs / %d files / %6.2f MB / unmapped=%s%s"
          % (label, len(pairs), len(files), sz / 1048576.0,
             unmapped or "-", "  MISSING %s" % miss if miss else ""))

print()
print("=" * 78)
print("4  do the swapped-in files differ byte for byte?  (identical = wasted write)")
print("=" * 78)
for label, t, d, ci in (("Archer <- Longbowman", 4, 8, 1),
                        ("Villager <- Archer", 83, 4, 1),
                        ("Barracks <- Feudal Barracks", 12, 498, 1)):
    if ci is None:
        continue
    r = cost(t, d, ci)
    if r is None:
        print("  %-30s (missing)" % label)
        continue
    ta, da, pairs, unmapped, files = r
    same = diff = missing = 0
    for k in files:
        dn = k[:-4] + ".sld"
        # recompute the target name for this file
        tn = None
        for a, b in pairs:
            for suffix in ("_x1", "_x2"):
                tb = (a[:-3] + suffix) if a.endswith("_x1") else a
                db = (b[:-3] + suffix) if b.endswith("_x1") else b
                if db + ".sld" == k:
                    tn = tb + ".sld"
        if tn is None:
            continue
        tp = os.path.join(G, tn)
        dp = os.path.join(G, dn)
        if not os.path.exists(tp) or not os.path.exists(dp):
            missing += 1
        elif open(tp, "rb").read() == open(dp, "rb").read():
            same += 1
        else:
            diff += 1
    print("  %-30s identical %d / different %d / missing %d"
          % (label, same, diff, missing))
