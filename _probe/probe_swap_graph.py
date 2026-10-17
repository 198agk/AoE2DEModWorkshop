# -*- coding: utf-8 -*-
"""PROOF: a building's stats are swapped out on AGE-UP.

probe_swap_mechanism printed, inside effect commands:
   tech 101 Feudal Age   -> (3, 12, 498, -1, 0.0)
   tech 102 Castle Age   -> (3, 12, 132, -1, 0.0)
   tech 103 Imperial Age -> (3, 12,  20, -1, 0.0)
and the .dat says 12='Barracks Age1' hp 1200, 498=Age2 hp 1500, 132=Age3 hp 1800,
20=Age4 hp 2100 -- the real per-age Barracks HP.

So effect command type 3 is a unit REPLACEMENT.  Consequence for the tool:
editing only the canonical id makes the change VANISH at the next age-up.

This probe builds the whole replacement graph and reports, for every canonical
buildable unit, which ids become reachable -- i.e. what an edit must cover.
"""
import os
import sys
import json
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P   # noqa: E402
from aoe2mod.semantic import index as S  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

data, how = P.load_dat(BASE)
p = P.Parser(data)
p.parse()
st = p.stats
effs = st["effects"]
techs = st["techs"]

# --- 1. which effect command types look like a swap? group by type ---
print("=== effect command arity by type (a,b,c are i16, d is f32) ===")
by_type = collections.defaultdict(list)
for eff in effs:
    for c in (eff.get("commands") or []):
        by_type[c[0]].append(c)
for t in sorted(by_type):
    cs = by_type[t]
    print("  type %-4s n=%-6d sample=%s" % (t, len(cs), cs[:3]))

# --- 2. gather every type-3 command as a directed edge a -> b ---
edges = collections.defaultdict(set)
edge_tech = {}
for ti, tech in enumerate(techs):
    ei = tech.get("effect_id")
    if ei is None or ei < 0 or ei >= len(effs):
        continue
    for c in (effs[ei].get("commands") or []):
        if c[0] == 3 and c[1] > 0 and c[2] > 0:
            edges[c[1]].add(c[2])
            edge_tech.setdefault((c[1], c[2]), []).append(ti)

print()
print("=== type-3 replacement edges: %d distinct sources ===" % len(edges))

# --- 3. closure: everything a canonical id can become ---
def closure(u, seen=None):
    seen = seen or set()
    if u in seen:
        return seen
    seen.add(u)
    for v in edges.get(u, ()):
        closure(v, seen)
    return seen

ix = S.index()
names = json.load(open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                                    "unit_names.json"), encoding="utf-8"))

print()
print("=== replacement families for well-known buildings ===")
INTEREST = [70, 12, 87, 101, 82, 71, 109, 104, 49, 103, 45, 79, 234, 235, 236,
            117, 155, 72, 487, 598, 209, 199, 13, 118, 2556]
for uid in INTEREST:
    fam = sorted(closure(uid) - {uid})
    e = names.get(str(uid)) or {}
    if not fam:
        print("  %-6s %-22s -> (no replacement)" % (uid, (e.get("en") or "")[:22]))
        continue
    detail = " ".join("%s(%s,hp%s)" % (v, (names.get(str(v)) or {}).get("internal"),
                                       None) for v in fam)
    hps = []
    for v in [uid] + fam:
        # hp is not in unit_names.json; read it from the dat walk instead
        pass
    print("  %-6s %-22s -> %-3d more: %s" % (uid, (e.get("en") or "")[:22], len(fam), detail))

# --- 4. how many canonical placeable units have a replacement family? ---
print()
print("=== how many of the 36 placeable builders have an age family? ===")
FAU = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")
fau = json.load(open(FAU, encoding="utf-8"))
builders = set()
for civ, blk in fau.items():
    if not isinstance(blk, dict):
        continue
    for b in blk.get("Buildings", []) or []:
        builders.add(b["ID"])
print("  distinct builders: %d" % len(builders))
withfam = sorted(u for u in builders if closure(u) - {u})
print("  builders with a replacement family: %d" % len(withfam))
for u in withfam:
    e = names.get(str(u)) or {}
    print("    %-6s %-24s -> %s" % (u, (e.get("en") or "")[:24], sorted(closure(u) - {u})))
