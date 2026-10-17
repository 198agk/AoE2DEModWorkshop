# -*- coding: utf-8 -*-
"""CONFIRM the defect on the real product path.

Hypothesis: `unit.stat` on a building writes only the canonical id, so the edit
stops applying the moment the player advances an age (the engine swaps id 12 for
498/132/20).  Prove it by compiling the intent and listing every unit id written.
"""
import os
import sys
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                      # noqa: E402
from aoe2mod.dat import locate as L               # noqa: E402
from aoe2mod.intent import compiler as C          # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data = tk._raw
_, bindings = C.load_schema()
schema = C.load_schema()[0]

def ids_written(intent):
    r = C.resolve(intent, schema, bindings=bindings)
    buf, edits = C.compile_edits(data, tk._civs, r, bindings, schema,
                                 tail=tk._parsed[4], gv=tk._parsed[3])
    return r, edits, len(edits)

print("=== what does an edit on Barracks actually touch? ===")
for label, it in (
    ("Barracks hp +100", {"intent": "unit.stat", "unit": 12, "stat": "hit_points", "delta": 100}),
    ("House hp +100",    {"intent": "unit.stat", "unit": 70, "stat": "hit_points", "delta": 100}),
    ("Archer hp +5",     {"intent": "unit.stat", "unit": 4,  "stat": "hit_points", "delta": 5}),
):
    try:
        r, edits, n = ids_written(it)
        # which .dat unit ids do the edited offsets belong to?
        touched = collections.Counter()
        for uid in (4, 10, 12, 14, 20, 70, 86, 87, 101, 132, 153, 191, 192,
                    463, 464, 465, 498):
            for ci, _cn, u in L.find_units(tk._civs, uid):
                off = (u.get("_offs") or {}).get("hit_points")
                if off is None:
                    continue
                if any(e.off == off for e in edits):
                    touched[uid] += 1
        print("  %-18s entity id %-5s -> %d edits | ids actually written: %s"
              % (label, r.entity.id, n, dict(touched)))
    except Exception as ex:
        print("  %-18s -> %s: %s" % (label, type(ex).__name__, ex))

print("=== what does an edit on Barracks actually touch? ===")
for label, it in (
    ("Barracks hp +100", {"intent": "unit.stat", "unit": 12, "stat": "hit_points", "delta": 100}),
    ("House hp +100",    {"intent": "unit.stat", "unit": 70, "stat": "hit_points", "delta": 100}),
    ("Archer hp +5",     {"intent": "unit.stat", "unit": 4,  "stat": "hit_points", "delta": 5}),
):
    try:
        r, edits, n = ids_written(it)
        print("  %-18s -> %d edits, distinct civ records touched: %d"
              % (label, n, len({e.where.split()[0] for e in edits})))
        print("        first 3: %s" % [e.where for e in edits[:3]])
    except Exception as ex:
        print("  %-18s -> %s: %s" % (label, type(ex).__name__, ex))

print()
print("=== the ids the game will use after each age-up, per replacement graph ===")
# Rebuild the type-3 edge set straight from the parsed dat.
p = tk._parsed[0]      # raw bytes are index 0; parse again for effects
from aoe2mod.dat import parser as P   # noqa: E402
pp = P.Parser(data)
pp.parse()
st = pp.stats
edges = collections.defaultdict(set)
for tech in st["techs"]:
    ei = tech.get("effect_id")
    if ei is None or ei < 0 or ei >= len(st["effects"]):
        continue
    for c in (st["effects"][ei].get("commands") or []):
        if c[0] == 3 and c[1] > 0 and c[2] > 0:
            edges[c[1]].add(c[2])

for uid, label in ((12, "Barracks"), (70, "House"), (87, "Archery Range"),
                   (101, "Stable"), (82, "Castle"), (104, "Monastery")):
    fam = sorted(edges.get(uid, ()))
    hps = []
    for v in [uid] + fam:
        hits = L.find_units(tk._civs, v)
        hps.append((v, hits[0][2].get("hit_points") if hits else None))
    print("  %-14s id %-5s -> %s" % (label, uid, hps))

print()
print("=== verdict ===")
print("  A user who says 'make Barracks tougher' gets ONE record edited;")
print("  the engine swaps that record out at Feudal/Castle/Imperial age.")
