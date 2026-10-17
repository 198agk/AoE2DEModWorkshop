# -*- coding: utf-8 -*-
"""Decide the PRODUCT family rule: effect graph, or plain name grouping?

The tail pair CopyID/BaseID is NOT a family signal (probe_base_id shows
copy_id == base_id == id for all 2693 records).

Two candidate rules:
  GRAPH : union along effect-command type 3 edges, accepting an edge only when
          source and target share a unit type and a NONZERO display name.
  GROUP : ignore effects entirely; group records that share (LanguageDLLName,
          unit type) -- i.e. the same name and type.

GROUP is far cheaper (no effect walk) but may be too coarse.  Measure how they
differ, and inspect every extra id GROUP adds, so the choice is made on data.
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

dll, typ, hp, cls, nm = {}, {}, {}, {}, {}
for c in civs:
    for u in c["units"]:
        o = (u.get("_offs") or {}).get("hit_points")
        if o is None:
            continue
        d, _cre = struct.unpack_from("<ii", data, o - 22 + 3)
        dll.setdefault(u["id"], set()).add(d)
        typ.setdefault(u["id"], set()).add(u["type"])
        cls.setdefault(u["id"], set()).add(u["class"])
        hp.setdefault(u["id"], set()).add(u["hit_points"])
        nm.setdefault(u["id"], set()).add(u.get("name") or "?")

edges = set()
for tech in techs:
    ei = tech.get("effect_id")
    if ei is None or ei < 0 or ei >= len(effs):
        continue
    for c in (effs[ei].get("commands") or []):
        if c[0] == 3 and c[1] > 0 and c[2] > 0:
            edges.add((c[1], c[2]))


def named(u):
    return {d for d in dll.get(u, ()) if d}


# ---- GRAPH ---------------------------------------------------------------
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


for a, b in sorted(edges):
    ta, tb = typ.get(a), typ.get(b)
    if not ta or ta != tb:
        continue
    na, nb = named(a), named(b)
    if not na or not nb or not (na & nb):
        continue
    union(a, b)
graph_group = collections.defaultdict(list)
for x in list(parent):
    graph_group[find(x)].append(x)
graph_of = {}
graph_fams = []
for v in graph_group.values():
    if len(v) < 2:
        continue
    v = sorted(v)
    graph_fams.append(v)
    for x in v:
        graph_of[x] = v
graph_fams.sort(key=lambda v: (-len(v), v[0]))

# ---- GROUP ---------------------------------------------------------------
by_key = collections.defaultdict(list)
for uid in dll:
    ns = named(uid)
    ts = typ.get(uid, set())
    if len(ns) != 1 or len(ts) != 1:
        continue                      # multi-valued: cannot be a simple key
    by_key[(next(iter(ns)), next(iter(ts)))].append(uid)
group_fams = sorted([sorted(v) for v in by_key.values() if len(v) > 1],
                    key=lambda v: (-len(v), v[0]))

print("GRAPH families: %d   (ids %d)" % (len(graph_fams), sum(map(len, graph_fams))))
print("      size hist: %s" % dict(sorted(collections.Counter(
    len(f) for f in graph_fams).items())))
print("GROUP families: %d   (ids %d)" % (len(group_fams), sum(map(len, group_fams))))
print("      size hist: %s" % dict(sorted(collections.Counter(
    len(f) for f in group_fams).items())))
print("      multi-valued (excluded from GROUP): %d"
      % sum(1 for uid in dll
            if len(named(uid)) != 1 or len(typ.get(uid, ())) != 1))

print()
print("=== GROUP families that are LARGER than the corresponding GRAPH family ===")
gof = {}
for v in group_fams:
    for x in v:
        gof[x] = v
seen = set()
extra_total = 0
for v in group_fams:
    # every graph family inside this group
    inner = [g for g in graph_fams if g[0] in v]
    gids = set()
    for g in inner:
        gids |= set(g)
    extra = sorted(set(v) - gids)
    if not extra:
        continue
    key = (v[0], tuple(v))
    if key in seen:
        continue
    seen.add(key)
    extra_total += len(extra)
    print("  GROUP[%2d] dll=%-12s type=%s" % (len(v), sorted(named(v[0])),
                                             sorted(typ.get(v[0], ()))))
    print("      all : %s" % v)
    if inner:
        print("      graph sub-families: %s" % inner)
    print("      extra (in GROUP, not reachable by the effect graph): %s" % extra)
    for x in extra:
        print("         %-6s %-24s hp=%-8s class=%s dll=%s"
              % (x, sorted(nm.get(x, ()))[0][:24], sorted(hp.get(x, ())),
                 sorted(cls.get(x, ())), sorted(dll.get(x, ()))))
print()
print("total ids GROUP adds beyond GRAPH: %d" % extra_total)

print()
print("=== GRAPH families the user would see as ONE name but that stay separate ===")
byname = collections.defaultdict(list)
for v in graph_fams:
    byname[tuple(sorted(named(v[0])))].append(v)
for k, vs in sorted(byname.items(), key=lambda kv: -len(kv[1])):
    if len(vs) < 2:
        continue
    print("  name dll=%s : %d separate graph families" % (list(k), len(vs)))
    for v in vs:
        print("      [%d] %s" % (len(v), v))
