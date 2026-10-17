# -*- coding: utf-8 -*-
"""Find a DATA-BACKED rule for "same thing, different age".

The replacement graph (effect command type 3) contains both real age families
(Barracks 12->498->132->20) and unrelated morphs (Builder 118->FlemisPikeman
1663).  Naively following every edge would over-reach.

Candidate discriminator: source and target share the same LanguageDLLName (the
display-name string id) AND the same unit type.  That should keep 12/498/132/20
together (all "Barracks", all type 80) and split 118 | 1663.

Measure it over every type-3 edge and report which edges it accepts/rejects.
"""
import os
import sys
import struct
import json
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

data, how = P.load_dat(BASE)
p = P.Parser(data)
p.parse()
st = p.stats
effs = st["effects"]
techs = st["techs"]

# --- per-id identity: LanguageDLLName + type + class, from the first civ copy ---
ident = {}
for u in st["civs"][1]["units"]:          # civ 1 = British, all real units
    ident[u["id"]] = u

# read LanguageDLLName straight out of the record: it is the i32 pair right
# after (type u8, id i16).  We do not have offsets here, so re-walk civ 1 with a
# tiny reader that captures it.
class R(object):
    def __init__(self, b, o, gv):
        self.b, self.o, self.gv = b, o, gv
    def u8(self):
        v = self.b[self.o]; self.o += 1; return v
    def i16(self):
        v = struct.unpack_from("<h", self.b, self.o)[0]; self.o += 2; return v
    def i32(self):
        v = struct.unpack_from("<i", self.b, self.o)[0]; self.o += 4; return v

# simpler: use the authoritative parser on a second pass, capturing dll via the
# mark the locator would record.  parser.read_unit discards it, so read the two
# i32s by hand from the record start.
locs = {}
cur = {}
ci = 0
u_off = None
# Find civ 1's unit record offsets with the locator, which records hit_points.
from aoe2mod.dat import locate as L       # noqa: E402
loc_u = {}
for u in st["civs"][1]["units"]:
    loc_u[u["id"]] = u

# Re-walk civ 1 by hand to grab LanguageDLLName (2 x i32 at record+3).
import importlib
# Use the locator's own walk to get _offs, then read dll from the raw stream.
tk_civs = None
sys.path.insert(0, ROOT)
from aoe2mod import api as A             # noqa: E402
tk = A.open_toolkit()
tk._ensure()
civs = tk._civs

dll = {}
typ = {}
cls = {}
hp = {}
for ci, c in enumerate(civs):
    for u in c["units"]:
        offs = u.get("_offs") or {}
        hpo = offs.get("hit_points")
        if hpo is None:
            continue
        # Record layout: Type u8 @0, ID i16 @1, LanguageDLLName i32 @3,
        # Creation i32 @7, Class i16 @11, ... HitPoints i16 @22.
        # So the record start is hit_points - 22, NOT -11.
        rec = hpo - 22
        d, t = struct.unpack_from("<ii", data, rec + 3)
        dll.setdefault(u["id"], set()).add(d)
        typ.setdefault(u["id"], set()).add(u["type"])
        cls.setdefault(u["id"], set()).add(u["class"])
        hp.setdefault(u["id"], set()).add(u["hit_points"])

# --- every type-3 edge, with its owning tech ---
edges = []
for ti, tech in enumerate(techs):
    ei = tech.get("effect_id")
    if ei is None or ei < 0 or ei >= len(effs):
        continue
    for c in (effs[ei].get("commands") or []):
        if c[0] == 3 and c[1] > 0 and c[2] > 0:
            edges.append((c[1], c[2], ti, tech.get("name")))
print("total type-3 edges: %d" % len(edges))

same_name = same_type = both = 0
rejected = []
for a, b, ti, nm in edges:
    da, db = dll.get(a), dll.get(b)
    ta, tb = typ.get(a), typ.get(b)
    sn = bool(da and db and da == db)
    stp = bool(ta and tb and ta == tb)
    if sn:
        same_name += 1
    if stp:
        same_type += 1
    if sn and stp:
        both += 1
    else:
        rejected.append((a, b, ti, nm, da, db, ta, tb))

print("  share LanguageDLLName : %d / %d" % (same_name, len(edges)))
print("  share unit type       : %d / %d" % (same_type, len(edges)))
print("  share BOTH            : %d / %d" % (both, len(edges)))
print()
print("=== edges REJECTED by 'share both' (sample) ===")
for a, b, ti, nm, da, db, ta, tb in rejected[:25]:
    print("   %-6s -> %-6s  dll %-8s -> %-8s  type %-6s -> %-6s  tech=%s"
          % (a, b, da, db, ta, tb, (nm or "")[:30]))

print()
print("=== the building families we care about, under 'share both' ===")
adj = collections.defaultdict(set)
for a, b, ti, nm in edges:
    da, db = dll.get(a), dll.get(b)
    ta, tb = typ.get(a), typ.get(b)
    if da and db and da == db and ta and tb and ta == tb:
        adj[a].add(b)

def closure(u, seen=None):
    seen = seen if seen is not None else set()
    if u in seen:
        return seen
    seen.add(u)
    for v in adj.get(u, ()):
        closure(v, seen)
    return seen

names = json.load(open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                                    "unit_names.json"), encoding="utf-8"))
for uid in (12, 70, 87, 101, 82, 104, 109, 45, 68, 118, 49, 103, 79, 117, 72, 2556):
    fam = sorted(closure(uid) - {uid})
    e = names.get(str(uid)) or {}
    print("  %-6s %-20s -> %s" % (uid, (e.get("en") or "")[:20],
                                  [(v, sorted(hp.get(v, set()))) for v in fam]))
