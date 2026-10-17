# -*- coding: utf-8 -*-
"""Characterise the header of pre-1.36 scenarios (1.21 / 1.33) vs 1.35/1.36.

Compares a failing 1.21 file, a failing 1.33 file, a working 1.35 and a working
1.36, showing aligned bytes so the structural difference is visible.
"""
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenario_header import locate_deflate, parse_file_header, HeaderParseError, decompress_body  # noqa: E402

DRS = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\gamedata_x2"
CAMP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"

CASES = [
    os.path.join(DRS, "real_world_antarctica.scx"),
    os.path.join(DRS, "real_world_nippon.scx"),
    os.path.join(DRS, "special_map_frontline.scx"),
    os.path.join(DRS, "special_map_canyons.scx"),
    os.path.join(DRS, "real_world_world.scx"),
]


def hexdump(b, n):
    out = []
    for i in range(0, min(len(b), n), 16):
        c = b[i:i + 16]
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
        out.append(f"  {i:5d}  {c.hex(' '):<47}  {asc}")
    return "\n".join(out)


for p in CASES:
    if not os.path.isfile(p):
        print(f"!! missing {p}")
        continue
    b = open(p, "rb").read()
    print("=" * 100)
    print(f"{os.path.basename(p)}  size={len(b)}  tag={b[:4]!r}")
    print(hexdump(b, 144))
    # ground truth: find longest eof stream
    best = None
    for off in range(4, min(len(b), 4096)):
        d = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            out = d.decompress(b[off:]) + d.flush()
        except zlib.error:
            continue
        if d.eof:
            if best is None or len(out) > best[1]:
                best = (off, len(out))
    print(f"  ground truth best off={best[0] if best else None} out={best[1] if best else 0}")
    h, data, diag = locate_deflate(b)
    print(f"  structural -> {h['deflate_offset'] if h else None} out={len(data) if data else 0}")
    # try the 1.36-with-IVU layout on the 1.21 file and report why it fails
    for layout in ("with_individual_victories_used", "without_individual_victories_used"):
        try:
            hh = parse_file_header(b, layout)
            print(f"  {layout}: off={hh['deflate_offset']} unknown_value={hh['unknown_value']} "
                  f"player_count={hh['player_count']} amount={hh['amount_of_unknown_numbers']} "
                  f"creator={hh['creator_name']!r} instructions_len={len(hh['scenario_instructions'])}")
        except HeaderParseError as e:
            print(f"  {layout}: {e}")
