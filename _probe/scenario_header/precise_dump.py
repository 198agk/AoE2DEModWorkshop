# -*- coding: utf-8 -*-
"""Precise, byte-addressed field dump for representative scenario headers.
Re-reads the CURRENT bytes on disk; no cached impressions.
The walk follows str32 boundaries so it stays u32-aligned in the real grammar.
"""
import os
import struct
import zlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common"
PROF = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"

CASES = [
    (os.path.join(GAME, "drs", "gamedata_x2", "real_world_britain.scx"), "pre-1.36 short (1.21)"),
    (os.path.join(GAME, "drs", "gamedata_x2", "real_world_antarctica.scx"), "pre-1.36 long (1.21)"),
    (os.path.join(GAME, "drs", "gamedata_x2", "special_map_holyline.scx"), "pre-1.36 long seq (1.21)"),
    (os.path.join(GAME, "drs", "gamedata_x2", "real_world_nippon.scx"), "pre-1.36 long+name (1.33)"),
    (os.path.join(GAME, "campaign", "0_E3_Scenario.aoe2scenario"), "1.35"),
    (os.path.join(GAME, "drs", "gamedata_x2", "special_map_frontline.scx"), "1.35"),
    (os.path.join(GAME, "drs", "gamedata_x2", "special_map_canyons.scx"), "1.36"),
    (os.path.join(PROF, "The Siege.aoe2scenario"), "1.53"),
    (os.path.join(PROF, "7V1变态山谷-炮塔盛宴-变态难.aoe2scenario"), "1.54"),
    (os.path.join(PROF, "default0.aoe2scenario"), "1.59"),
]


def gt(b, limit=200000):
    best = (None, 0)
    for off in range(4, min(len(b), limit)):
        d = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            out = d.decompress(b[off:])
        except zlib.error:
            continue
        if d.eof and len(out) > best[1]:
            best = (off, len(out))
    return best


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


for path, label in CASES:
    if not os.path.isfile(path):
        print(f"MISSING {path}")
        continue
    b = open(path, "rb").read()
    off, n = gt(b)
    print("=" * 112)
    print(f"{label}  ver={b[:4]!r}  size={len(b)}  GT deflate offset={off}  out={n}")
    o = 4
    i = 0
    while o + 4 <= off:
        v = u32(b, o)
        note = ""
        step = 4
        if v == 1000:
            note = "  <-- UNKNOWN_VALUE 1000"
        elif 0 < v <= 64 and o + 4 + v <= off and all(
            32 <= c < 127 or c == 0 for c in b[o + 4:o + 4 + v]
        ):
            note = f'  <str32 "{b[o+4:o+4+v].decode("ascii","replace")}">'
        print(f"    f{i:<2d} @{o:5d}  u32={v:<12d}{note}")
        o += step
        i += 1
    print(f"    (stopped at @{o}; leftover {off - o} byte(s): {b[o:off].hex(' ')})")
