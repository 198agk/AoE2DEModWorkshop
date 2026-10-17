# -*- coding: utf-8 -*-
r"""Derive the animation vocabulary from coverage instead of guessing it.

A token like `idleA` appears under thousands of different prefixes (every unit
has one).  A token like `oak` or `gold` appears under one or two.  So the
vocabulary is a threshold on "how many distinct prefixes does this token occur
under", and the threshold can be read off the distribution rather than invented.
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_gfx = tk._stats["graphics"]

seen = {}          # token -> set(prefix)
for x in _gfx:
    f = x.get("file")
    if not isinstance(f, str):
        continue
    f = f.strip()
    if not f or f == "None" or not f.endswith("_x1"):
        continue
    stem = f[:-3]
    p, _, t = stem.rpartition("_")
    if not p:
        continue
    seen.setdefault(t, set()).add(p)

rows = sorted(seen.items(), key=lambda kv: -len(kv[1]))
print("distinct tokens: %d" % len(rows))
print()
print("%-16s %8s" % ("token", "prefixes"))
for t, ps in rows[:70]:
    print("%-16s %8d" % (t, len(ps)))
print("   ...")
for t, ps in rows[-10:]:
    print("%-16s %8d" % (t, len(ps)))

print()
print("distribution of prefix-counts:")
buckets = collections.Counter()
for t, ps in rows:
    n = len(ps)
    for lo, hi, lab in ((0, 1, "1"), (2, 4, "2-4"), (5, 19, "5-19"),
                        (20, 99, "20-99"), (100, 499, "100-499"),
                        (500, 1999, "500-1999"), (2000, 10 ** 9, ">=2000")):
        if lo <= n <= hi:
            buckets[lab] += 1
            break
for lab in ("1", "2-4", "5-19", "20-99", "100-499", "500-1999", ">=2000"):
    print("   %-8s %4d" % (lab, buckets[lab]))

print()
print("tokens with >=100 prefixes (candidate ANIMATION vocabulary):")
cand = sorted(t for t, ps in seen.items() if len(ps) >= 100)
print("   %d tokens: %s" % (len(cand), cand))

print()
print("tokens with 20..99 prefixes (borderline -- inspect):")
mid = sorted((len(ps), t) for t, ps in seen.items() if 20 <= len(ps) < 100)
for n, t in mid:
    print("   %-16s %4d   e.g. %s" % (t, n, sorted(seen[t])[:3]))
