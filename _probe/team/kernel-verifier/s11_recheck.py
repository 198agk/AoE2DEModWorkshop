# -*- coding: utf-8 -*-
"""Recheck claims 2 and 5 against the CURRENT working tree.

The tree moved under me mid-audit (aoe2mod/dat/locate.py lost its demo main(),
aoe2mod/dat/writer.py was touched).  Claims 1 and 2 were measured before that,
so claim 2 is re-derived here from a fresh build, with stdlib zlib only.
"""
import hashlib
import json
import os
import shutil
import sys
import zlib

sys.path.insert(0, r"D:\Software\AI\帝国项目")
import aoe2mod.api as A

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(ROOT, r"resources\_common\dat\empires2_x2_p1.dat")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "r1")


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


if os.path.isdir(OUT):
    shutil.rmtree(OUT)

tk = A.Toolkit(ROOT)
it = {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'displayed_attack', 'delta': 2}
p = tk.plan(it)
man = tk.build(it, os.path.join(OUT, "m"), title="recheck", author="kv")

base = inflate(BASE)
mod_p = os.path.join(OUT, "m", r"resources\_common\dat\empires2_x2_p1.dat")
mod = inflate(mod_p)

diffs = [i for i in range(len(base)) if base[i] != mod[i]]
runs = []
for i in diffs:
    if runs and i == runs[-1][-1] + 1:
        runs[-1].append(i)
    else:
        runs.append([i])

print("plan edit_count        :", p.get("edit_count"))
print("build edit_count       :", man.get("edit_count"))
print("base raw / mod raw     :", len(base), "/", len(mod), "delta", len(mod) - len(base))
print("mod file bytes         :", os.path.getsize(mod_p))
print("changed bytes          :", len(diffs))
print("runs                   :", len(runs), "widths", sorted({len(r) for r in runs}))
print("first / last offset    :", diffs[0], "/", diffs[-1])
print("two-byte-slots (pairs) :", len(diffs) // 2,
      "constant gap          :", {diffs[i + 1] - diffs[i] for i in range(0, len(diffs) - 1, 2)}
      if len(diffs) % 2 == 0 else "odd count")
print("byte patterns          :",
      {(base[a], mod[a], base[b], mod[b]) for a, b in zip(diffs[0::2], diffs[1::2])})
viol = 0
for d in diffs:
    for j in range(max(0, d - 200), min(len(base), d + 201)):
        if base[j] != mod[j] and j not in set(diffs):
            viol += 1
print("+/-200 window violations:", viol)
print("debug markers base/mod :", base.count(b"\x60\x0a"), "/", mod.count(b"\x60\x0a"))
print("verification keys      :", sorted(man["verification"]))
print("proven / not_proven    :",
      "proven" in man["verification"], "/", "not_proven" in man["verification"])
print("sha256 base raw        :", hashlib.sha256(base).hexdigest())
print("sha256 mod  raw        :", hashlib.sha256(mod).hexdigest())
