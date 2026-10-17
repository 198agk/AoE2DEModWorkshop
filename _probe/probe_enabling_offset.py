# -*- coding: utf-8 -*-
r"""Locate the byte offset of a unit connection's `EnablingResearch`.

`dsh test v1` proved the engine READS an effect command (B passed: the Longbowman
survived inside the very effect the mod re-pointed), yet an ADDED `(2, 2550, 1)`
granted nothing (C failed).  The measured difference between the unit that works and
the one that does not:

    unit 8    Longbowman      EnablingResearch = 263   owner British   tree row YES
    unit 2550 Champi Scout    EnablingResearch = -1    no owner        tree row NO

So the next experiment is to give unit 2550 an `EnablingResearch` pointing at a
British-owned tech (263).  `P.Parser.stats["tech_tree"]` does NOT model the connection
bodies, so that edit has to be an in-place byte patch -- which is the technique already
proven for unit stats (exact offsets, only the touched bytes change).

This probe finds the offset of each unit connection's `EnablingResearch` i32 and
verifies the patch reads back correctly.
"""
import contextlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s" % (name, "PASS" if ok else "FAIL"))
    if not ok:
        fails.append(name)
    if not ok:
        print("      %s" % detail)


def connection_offsets(pr, raw, gv_):
    """{unit_id: {field: byte_offset}} for every TechTree unit connection.

    Mirrors the documented layout (`read_unit_connection` in the shipped source):
    ID(i32) Status(u8) UpperBuilding(i32) then `read_common`, then VerticalLine(i32),
    one group, LocationInAge(i32), RequiredResearch(i32), LineMode(i32),
    EnablingResearch(i32).
    """
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv_)
    r.pos = stage[1] + 7 * 4
    n_ages, n_bldg = r.u8(), r.u8()
    n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(n_ages):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(n_bldg):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    out = {}
    for _ in range(n_units):
        _id_off = r.pos
        uid = r.i32(); r.u8(); _upper = r.pos
        r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32()
        _req = r.pos
        r.i32()
        r.i32()
        _enab = r.pos
        enab = r.i32()
        out[uid] = {"id_offset": _id_off, "upper_offset": _upper,
                    "required_offset": _req, "enabling_offset": _enab,
                    "enabling": enab}
    return out


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
off = connection_offsets(_p, data, gv)

print("A  the offsets read back the same values we already measured")
for uid, want in ((8, 263), (2550, -1), (41, 270), (5, 85)):
    got = off.get(uid)
    print("     unit %-5s enabling=%-6s offset=%s  (expected %s)"
          % (uid, (got or {}).get("enabling"), (got or {}).get("enabling_offset"),
             want))
    check("unit %d's enabling value matches the earlier measurement" % uid,
          (got or {}).get("enabling") == want)

print()
print("B  an in-place patch of unit 2550's EnablingResearch is well-formed")
rec = off[2550]
o = rec["enabling_offset"]
before = struct.unpack_from("<i", data, o)[0]
print("     offset %d (0x%X): %d" % (o, o, before))
patched = bytearray(data)
struct.pack_into("<i", patched, o, 263)
# verify ONLY those 4 bytes changed
diffs = [i for i in range(len(data)) if data[i] != patched[i]]
print("     bytes changed by the patch: %d at %s" % (len(diffs), diffs))
check("exactly 4 bytes changed", len(diffs) == 4, "%s" % diffs)
check("and they are the 4 at the enabling offset",
      diffs == [o, o + 1, o + 2, o + 3], "%s vs %s" % (diffs, [o, o + 1, o + 2, o + 3]))
check("the value reads back as 263",
      struct.unpack_from("<i", bytes(patched), o)[0] == 263)

print()
print("C  the patched stream still parses to exactly its own length")
with contextlib.redirect_stdout(io.StringIO()):
    p2 = P.Parser(bytes(patched))
    p2.parse()
print("     consumed %d of %d; clean EOF: %s"
      % (p2.r.pos, len(patched), p2.r.pos == len(patched)))
check("clean EOF after the patch", p2.r.pos == len(patched))
off2 = connection_offsets(p2, bytes(patched), gv)
check("and unit 2550 now reads back 263",
      off2[2550]["enabling"] == 263, "%s" % off2[2550])
check("unit 8's own value is untouched", off2[8]["enabling"] == 263)

print()
print("D  what a British-owned tech could be pointed at")
print("     tech 263 'Longbow (make avail)'  civ=1 (British)  effect 251")
print("     -> patching unit 2550's EnablingResearch to 263 makes the Britons the")
print("        cited owner of the Champi Scout.  That is the (a) hypothesis in")
print("        `_probe/probe_grant_missing_link.py`, isolated with no other change.")

print()
print("ENABLING OFFSET: the field is at a byte offset that can be patched in place,")
print("  changing exactly 4 bytes and leaving the stream parseable.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
