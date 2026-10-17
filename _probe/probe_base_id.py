# -*- coding: utf-8 -*-
"""Is there an IN-RECORD age-family signal?

read_unit() ends with two i16s documented as `CopyID` and `BaseID`
(parser.py:803-804).  If Barracks Age2/3/4 carry BaseID == 12, the family is
already in the record and no effect-graph walk is needed.

Also capture LanguageDLLName (the display-name string id, i32 at record+3), which
the family rule uses as its second condition.

Method: walk ONE civ with the authoritative parser, but wrap the reader so that
every unit's record start is remembered, then read the tail fields by hand from
the raw stream using the record offsets the locator produces.
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
from aoe2mod.dat import locate as L     # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data = tk._raw
gv = tk._parsed[3]
civs = tk._civs

# Re-walk civ 1 (British) with Orec so we get per-unit byte offsets, capturing
# LanguageDLLName and the trailing CopyID/BaseID.
civs_start = tk._parsed[2]
r = L.Orec(data, civs_start, gv=gv)
target_civ = 1
recs = []
for ci in range(target_civ + 1):
    r.u8()                       # player_type
    P.read_sized_string(r) if hasattr(P, "read_sized_string") else None
    # civ walking is done by the locator; simpler: use locate's own walker
# Use the locator's civ walk directly.
allc = L.locate(data, parser=None) if False else None

# Simplest reliable route: P.Parser already produced civs, and locate() recorded
# _offs per unit.  Record start = hit_points - 22 (verified layout).
units = civs[target_civ]["units"]
print("civ[%d] %s : %d units" % (target_civ, civs[target_civ]["name"], len(units)))

rows = {}
for u in units:
    o = (u.get("_offs") or {}).get("hit_points")
    if o is None:
        continue
    rec = o - 22
    dll, cre = struct.unpack_from("<ii", data, rec + 3)
    # the trailing pair sits immediately before the end of the unit record; we do
    # not know the end here, so instead find CopyID/BaseID by re-walking with a
    # reader that stops right after them.
    rows[u["id"]] = {"dll": dll, "type": u["type"], "hp": u["hit_points"],
                     "class": u["class"], "rec": rec}

# Re-walk civ 1 with a counting reader to grab CopyID/BaseID precisely.
class R(object):
    def __init__(self, b, o, gv):
        self.b = b; self.o = o; self.gv = gv; self.marks = {}
    def at(self, k):
        self.marks[k] = self.o; return self.o
    def skip(self, n): self.o += n
    def u8(self):
        v = self.b[self.o]; self.o += 1; return v
    def i16(self):
        v = struct.unpack_from("<h", self.b, self.o)[0]; self.o += 2; return v
    def i32(self):
        v = struct.unpack_from("<i", self.b, self.o)[0]; self.o += 4; return v
    def u32(self):
        v = struct.unpack_from("<I", self.b, self.o)[0]; self.o += 4; return v
    def f32(self):
        v = struct.unpack_from("<f", self.b, self.o)[0]; self.o += 4; return v
    def i16_array(self, n):
        v = list(struct.unpack_from("<%dh" % n, self.b, self.o)); self.o += 2 * n
        return v
    def i32_array(self, n):
        v = list(struct.unpack_from("<%di" % n, self.b, self.o)); self.o += 4 * n
        return v
    def f32_array(self, n):
        v = list(struct.unpack_from("<%df" % n, self.b, self.o)); self.o += 4 * n
        return v
    def debug_string(self):
        n = struct.unpack_from("<H", self.b, self.o + 2)[0]
        raw = self.b[self.o + 4:self.o + 4 + n]
        self.o += 4 + n
        z = raw.find(b"\x00")
        return (0, (raw[:z] if z >= 0 else raw).decode("latin-1"))

# Reuse the locator's walk_unit, but append our own capture by monkeypatching:
# walk_unit already consumes CopyID/BaseID blind.  So read them from the stream
# right after the unit's name by re-running the walk and noting r.o.
# Capture CopyID/BaseID precisely: walk_unit ends with
#   u8,u8 (OldAttackReaction, ConvertTerrain); name; i16 CopyID; i16 BaseID.
# Wrap the authoritative walker's string extraction to note where the name ends.
idxs = []
tailinfo = {}


class Cap(R):
    def debug_string(self):
        v = R.debug_string(self)
        idxs.append(self.o + 0)      # position just after the name
        return v


cap = Cap(data, civs_start, gv)
cap.u8(); cap.debug_string()
n = cap.i16(); cap.i16(); cap.i16(); cap.f32_array(n); cap.u8()
m = cap.i16(); ptrs = cap.i32_array(m)
first = None
for i in range(m):
    if ptrs[i] == 0:
        continue
    rec = cap.o
    uid = struct.unpack_from("<h", data, rec + 1)[0]
    dll = struct.unpack_from("<i", data, rec + 3)[0]
    nbefore = len(idxs)
    unit = P.read_unit(cap)
    assert len(idxs) == nbefore + 1
    pos_after_name = idxs[-1]
    copy_id, base_id = struct.unpack_from("<hh", data, pos_after_name)
    tailinfo[uid] = {"copy_id": copy_id, "base_id": base_id, "dll": dll,
                     "hp": unit["hit_points"], "type": unit["type"],
                     "rec": rec, "name": unit["name"]}

print("collected %d unit records from civ 1" % len(tailinfo))
print()
print("=== do age variants point at their base via BaseID/CopyID? ===")
fams = {12: [12, 20, 132, 498], 70: [70, 191, 192, 463, 464, 465],
        87: [87, 10, 14], 101: [101, 86, 153], 109: [109, 71, 141, 142],
        68: [68, 129, 130, 131], 209: [209, 210], 82: [82, 2418],
        4: [4], 83: [83], 38: [38]}
for base, members in fams.items():
    print("  family of %-4d:" % base)
    for x in members:
        t = tailinfo.get(x)
        if t is None:
            print("     %-6d <absent from civ 1>" % x); continue
        print("     %-6d %-22s hp=%-6s copy_id=%-7s base_id=%-7s dll=%s"
              % (x, t["name"][:22], t["hp"], t["copy_id"], t["base_id"], t["dll"]))

distinct = collections.Counter((t["copy_id"], t["base_id"]) for t in tailinfo.values())
print()
print("top (copy_id, base_id) pairs over civ 1: %s" % distinct.most_common(8))
nz = [t for t in tailinfo.values() if t["base_id"] > 0]
print("records with base_id > 0: %d / %d" % (len(nz), len(tailinfo)))
json.dump({str(k): v for k, v in tailinfo.items()},
          open(os.path.join(ROOT, "_probe", "unit_tail_ids.json"), "w",
               encoding="utf-8"), indent=1)
print("wrote _probe/unit_tail_ids.json")
