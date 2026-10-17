# -*- coding: utf-8 -*-
"""Diff the locator's walk_unit() against the authoritative read_unit().

Both walk the same records.  Any version guard present in the authoritative
reader but missing from the locator shows up here as accumulating drift.
"""
import contextlib
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.dat import parser as P
from aoe2mod.dat import locate as L

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
SUB = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
TARGETS = [
    ("BASE VER 8.9", BASE),
    ("MOD_297820 VER 7.8", os.path.join(
        SUB, "297820_10 倍资源文明联盟3倍科技",
        "resources", "_common", "dat", "empires2_x2_p1.dat")),
]

print("GV_C30 = %d (VER 8.7)   GV_C31 = %d (VER 8.8)" % (P.GV_C30, P.GV_C31))
print()

for tag, path in TARGETS:
    if not os.path.exists(path):
        print("MISSING", tag)
        continue
    data, how = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    gv = p.r.gv
    stage8 = next(t for t in p.stage_offsets if t[0].startswith("8 Civs"))
    n_civ = struct.unpack_from("<h", data, stage8[1])[0]
    civs_start = stage8[1] + 2

    auth = L.Orec(data, civs_start, gv=gv)
    print("=" * 74)
    print("%s   gv=%d  civs_start=0x%X  n_civ=%d" % (tag, gv, civs_start, n_civ))

    # Walk both and compare at each unit boundary.
    drifts = []
    n_units = 0
    for ci in range(n_civ):
        auth.u8()                                    # player_type
        auth.debug_string()                          # name
        n = auth.i16()
        auth.i16(); auth.i16()                       # tech_tree, team_bonus
        auth.f32_array(n)
        auth.u8()                                    # icon_set
        m = auth.i16()
        ptrs = auth.i32_array(m)
        for i in range(m):
            if ptrs[i] == 0:
                continue
            start = auth.o
            P.read_unit(auth)
            end_auth = auth.o
            alt = L.Orec(data, start, gv=gv)
            try:
                L.walk_unit(alt, ci)
                end_alt = alt.o
            except Exception as exc:
                drifts.append((ci, n_units, end_auth - start, str(exc)[:60]))
                n_units += 1
                continue
            n_units += 1
            if end_alt != end_auth:
                drifts.append((ci, n_units, end_auth - end_alt, end_auth - start))

    print("  unit records compared: %d" % n_units)
    print("  records where walk_unit disagrees: %d" % len(drifts))
    for d in drifts[:6]:
        print("    civ %-3d rec#%-6d delta_vs_authoritative=%-6s record_bytes=%s"
              % (d[0], d[1], d[2], d[3]))
    if drifts and isinstance(drifts[0][2], int):
        print("  >>> walk_unit consumes %d byte(s) %s per record on this version"
              % (abs(drifts[0][2]), "fewer" if drifts[0][2] > 0 else "more"))
    else:
        print("  >>> VERDICT: walk_unit agrees with the authoritative reader")
