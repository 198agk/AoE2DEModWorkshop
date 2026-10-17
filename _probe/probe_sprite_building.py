# -*- coding: utf-8 -*-
"""A building's token is its AGE, so 'reskin the Dark Age Barracks' cannot use
the Feudal Age Barracks as donor.  Does a CROSS-CIVILIZATION donor of the same
age work?  And what does a per-civ fan-out really cost?"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import collections
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

print("=" * 78)
print("1  unit 12 (Barracks) across civilizations: stem + token")
print("=" * 78)
seen = collections.defaultdict(list)
for c in tk._civs:
    for u in c.get("units", ()):
        if u["id"] != 12:
            continue
        a = idx.art(u)
        if a and a.get("kind") == "loose":
            seen[(a.get("stem"), tuple(sorted((a.get("tokens") or {}))))].append(c["name"])
for k in sorted(seen, key=lambda k: -len(seen[k])):
    print("  %-28s tokens=%-22s %2d civs  %s"
          % (k[0], ",".join(k[1]), len(seen[k]), ", ".join(sorted(seen[k])[:3])))

print()
print("=" * 78)
print("2  cross-civ donation, same token")
print("=" * 78)
pairs = sorted(seen, key=lambda k: -len(seen[k]))
if len(pairs) >= 2:
    for a_key, b_key in ((pairs[0], pairs[1]), (pairs[1], pairs[0])):
        ci_a = None
        for i, c in enumerate(tk._civs):
            if c["name"] == sorted(seen[a_key])[0]:
                ci_a = i
        t = idx.art([u for u in tk._civs[ci_a]["units"] if u["id"] == 12][0])
        d = None
        for i, c in enumerate(tk._civs):
            if c["name"] == sorted(seen[b_key])[0]:
                d = idx.art([u for u in c["units"] if u["id"] == 12][0])
        pr, un, ex = S.plan_swap(t, d)
        out, unp = S.swap_files(t, d)
        print("  %s  <-  %s" % (t.get("stem"), d.get("stem")))
        print("      pairs=%d unmapped=%s extra=%s files=%d"
              % (len(pr), un, ex, len(out)))
        for k in sorted(out):
            p = os.path.join(GAME, k.replace("/", os.sep))
            print("        %-58s %s" % (os.path.basename(k),
                  "%d B" % os.path.getsize(p) if os.path.exists(p) else "MISSING"))

print()
print("=" * 78)
print("3  per-civ fan-out: how many DISTINCT files for a unit-wide reskin")
print("=" * 78)
for target, donor, label in ((4, 8, "Archer <- Longbowman"),
                             (83, 4, "Villager <- Archer"),
                             (12, 12, "Barracks cross-civ (every comb)")):
    if target == 12:
        continue
    allf = {}
    stems = set()
    for ci in range(len(tk._civs)):
        t = d = None
        for u in tk._civs[ci]["units"]:
            if u["id"] == target:
                t = u
            if u["id"] == donor:
                d = u
        if t is None or d is None:
            continue
        ta, da = idx.art(t), idx.art(d)
        if not ta or not da or ta.get("kind") != "loose" or da.get("kind") != "loose":
            continue
        stems.add((ta.get("stem"), da.get("stem")))
        try:
            out, unp = S.swap_files(ta, da)
        except S.SpriteError as e:
            continue
        for k, v in out.items():
            allf[k] = v
    known = [v for v in allf.values()]
    sz = 0
    for v in known:
        p = os.path.join(G, v)
        if os.path.exists(p):
            sz += os.path.getsize(p)
    print("  %-30s distinct (target,donor) stems: %d" % (label, len(stems)))
    print("     files a mod must carry: %d   payload: %.1f MB"
          % (len(allf), sz / 1048576.0))
    inv = collections.Counter()
    for k, v in allf.items():
        inv[(k.split("/")[-1], v)] += 1
    dup = [(k, n) for k, n in inv.items() if n > 1]
    print("     (target,donor) pairs written more than once: %d" % len(dup))
    for k, n in sorted(dup)[:5]:
        print("        %-34s <- %-34s x%d" % (k[0], k[1], n))
