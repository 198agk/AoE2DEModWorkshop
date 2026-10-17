# -*- coding: utf-8 -*-
"""Refine the age-variant family rule and decide the product form.

Problem with the first pass: requiring only "same display name" merged projectile
records because several have LanguageDLLName == 0, and 0 == 0.

Refined rule: source and target must share a unit type AND share a NONZERO
display-name string id.  Rationale: the game itself shows these ids as one named
thing, which is exactly what the user means when they name it.

Measures, for each candidate rule:
  - how many type-3 edges each accepts
  - the resulting families, split into "named" (all members have a display name)
    and "unnamed" (dll == 0), so the answer for a tool is visible
Also dumps the accepted family map to JSON for the product module to consume.
"""
import os
import sys
import struct
import json
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import contextlib
import io

from aoe2mod import api as A            # noqa: E402
from aoe2mod.dat import parser as P     # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data = tk._raw
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
stats = p.stats
techs, effs, civs = stats["techs"], stats["effects"], tk._civs
gv = tk._parsed[3]
print("gv=%d" % gv)

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


def named(uid):
    """The nonzero display-name ids this unit carries, if any."""
    return {d for d in dll.get(uid, ()) if d}


def build(require_named=True, require_same_class=False):
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

    acc = 0
    for a, b in edges:
        ta, tb = typ.get(a), typ.get(b)
        if not ta or not tb or ta != tb:
            continue
        if require_same_class and cls.get(a) != cls.get(b):
            continue
        if require_named:
            na, nb = named(a), named(b)
            if not na or not nb or not (na & nb):
                continue
        else:
            if dll.get(a) != dll.get(b):
                continue
        union(a, b)
        acc += 1
    groups = collections.defaultdict(list)
    for x in list(parent):
        groups[find(x)].append(x)
    return acc, [sorted(v) for v in groups.values() if len(v) > 1]


for rn, rsc in ((True, False), (True, True), (False, False)):
    acc, fams = build(require_named=rn, require_same_class=rsc)
    named_f = [f for f in fams if all(named(x) for x in f)]
    un_f = [f for f in fams if not all(named(x) for x in f)]
    print()
    print("=== require_named=%s require_same_class=%s -> %d edges, %d families "
          "(named %d / unnamed %d, ids %d) ==="
          % (rn, rsc, acc, len(fams), len(named_f), len(un_f),
             sum(len(f) for f in fams)))
    if un_f:
        print("   unnamed families:")
        for f in sorted(un_f, key=len, reverse=True)[:8]:
            print("     ids=%s dll=%s type=%s"
                  % (f, [sorted(dll.get(x, ())) for x in f],
                     [sorted(typ.get(x, ())) for x in f]))
    print("   named family size histogram: %s"
          % dict(sorted(collections.Counter(len(f) for f in named_f).items())))
    for f in sorted(named_f, key=lambda v: (-len(v), v[0])):
        d = named(f[0])
        print("     [%2d] dll=%-12s type=%-4s hp=%-24s ids=%s"
              % (len(f), sorted(d), sorted({t for x in f for t in typ.get(x, ())}),
                 sorted({h for x in f for h in hp.get(x, ())}), f))

acc, fams = build(require_named=True)
out = {}
for f in fams:
    for x in f:
        out[str(x)] = f
dst = os.path.join(ROOT, "_probe", "family_map.json")
json.dump({"edges": sorted("%d>%d" % e for e in edges),
           "families": sorted(fams), "lookup": out},
          open(dst, "w", encoding="utf-8"), indent=1)
print()
print("wrote %s (%d families, %d ids)"
      % (dst, len(fams), sum(len(f) for f in fams)))
