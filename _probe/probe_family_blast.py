# -*- coding: utf-8 -*-
"""Blast radius of the age-variant family rule.

Build the replace graph (effect command type 3), accept an edge only when source
and target share a display name (LanguageDLLName) and a unit type, then compute
connected components.  Report every family with >= 2 members so the fix's reach
is known before any product code is written.

Two variants of "share a display name" are compared, because set EQUALITY is
strict: an id that appears in several civs under different names (standard id +
Chronicles 405xxx alias) has a multi-valued set.
  strict : the two dll sets are equal
  loose  : the two dll sets intersect
"""
import os
import sys
import struct
import json
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A            # noqa: E402
from aoe2mod.dat import parser as P     # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data = tk._raw
st = P.Parser(data); st.parse(); stats = st.stats
techs, effs, civs = stats["techs"], stats["effects"], tk._civs

dll, typ, hp, cls = {}, {}, {}, {}
for c in civs:
    for u in c["units"]:
        o = (u.get("_offs") or {}).get("hit_points")
        if o is None:
            continue
        d, t = struct.unpack_from("<ii", data, o - 22 + 3)
        dll.setdefault(u["id"], set()).add(d)
        typ.setdefault(u["id"], set()).add(u["type"])
        cls.setdefault(u["id"], set()).add(u["class"])
        hp.setdefault(u["id"], set()).add(u["hit_points"])

edges = set()
for tech in techs:
    ei = tech.get("effect_id")
    if ei is None or ei < 0 or ei >= len(effs):
        continue
    for c in (effs[ei].get("commands") or []):
        if c[0] == 3 and c[1] > 0 and c[2] > 0:
            edges.add((c[1], c[2]))
print("distinct type-3 (src,tgt) pairs: %d" % len(edges))

names = json.load(open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                                   "unit_names.json"), encoding="utf-8"))


def nm(uid):
    e = names.get(str(uid)) or {}
    return e.get("en") or "?"


def components(mode):
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    accepted = 0
    for a, b in edges:
        da, db, ta, tb = dll.get(a), dll.get(b), typ.get(a), typ.get(b)
        if not da or not db or not ta or not tb or ta != tb:
            continue
        ok = (da == db) if mode == "strict" else bool(da & db)
        if ok:
            union(a, b)
            accepted += 1
    groups = collections.defaultdict(list)
    for x in list(parent):
        groups[find(x)].append(x)
    fams = sorted([sorted(v) for v in groups.values() if len(v) > 1],
                  key=lambda v: (-len(v), v[0]))
    return accepted, fams


for mode in ("strict", "loose"):
    acc, fams = components(mode)
    print()
    print("=== mode=%s : accepted %d edges, %d families ===" % (mode, acc, len(fams)))
    print("   family size histogram: %s" % dict(sorted(collections.Counter(
        len(f) for f in fams).items())))
    print("   ids inside a family: %d" % sum(len(f) for f in fams))
    for f in fams:
        dls = set()
        for x in f:
            dls |= dll.get(x, set())
        print("   [%2d] %-22s type=%-4s hp=%-11s ids=%s"
              % (len(f), (nm(f[0]) or "?")[:22], sorted(typ.get(f[0], [])),
                 sorted({h for x in f for h in hp.get(x, ())}), f))
        for x in f:
            print("          %-6s %-20s dll=%-14s hp=%s"
                  % (x, (names.get(str(x)) or {}).get("internal", "?")[:20],
                     sorted(dll.get(x, ())), sorted(hp.get(x, ()))))
