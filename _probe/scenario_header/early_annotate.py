# -*- coding: utf-8 -*-
"""For every pre-1.36 scenario that the 1.36+ structural model rejects, find the
TRUE deflate offset by brute force (ground truth only, to characterise the layout)
and print an annotated field walk of everything before it.

This is diagnostic, not the deliverable algorithm.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DRS = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\gamedata_x2"


def ground_truth_offset(b):
    """Return the offset of the longest raw-deflate stream that reaches eof."""
    best = (None, 0)
    # the header is small; only scan a sane prefix so this stays fast
    for off in range(4, min(len(b), 8192)):
        d = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            out = d.decompress(b[off:])
        except zlib.error:
            continue
        if d.eof and len(out) > best[1]:
            best = (off, len(out))
    return best


def annotate(b, off, label):
    print(f"  --- {label}: switching to byte-walk (u32 at every position) ---")
    o = 16
    step = 0
    while o < off:
        v = struct.unpack_from("<I", b, o)[0]
        note = ""
        if 0 < v <= 255 and o + 4 + v <= len(b):
            s = b[o + 4:o + 4 + v]
            if s and all(32 <= c < 127 for c in s):
                note = f'  -> str32 "{s.decode()}" (len {v})'
        print(f"    @{o:4d} u32={v:<12d}{note}")
        # heuristically advance: if it looks like a str32, jump past it
        if note:
            o = o + 4 + v
        else:
            o += 4
        step += 1
        if step > 40:
            print("    ... (truncated)")
            break


FILES = [
    "real_world_antarctica.scx",   # 1.21
    "real_world_spain.scx",        # 1.21
    "real_world_nippon.scx",       # 1.33
]
for name in FILES:
    p = os.path.join(DRS, name)
    if not os.path.isfile(p):
        print(f"!! missing {p}")
        continue
    b = open(p, "rb").read()
    off, n = ground_truth_offset(b)
    print("=" * 100)
    print(f"{name}  tag={b[:4]!r}  size={len(b)}")
    print(f"  GROUND TRUTH deflate offset = {off}  out={n}")
    print(f"  bytes[0:{off}] = {b[:off].hex(' ')}")
    annotate(b, off, name)
    # print the presumed str32 length right before a possible creator name
    for cand in range(max(0, off - 40), off):
        v = struct.unpack_from("<I", b, cand)[0]
        if 0 < v <= 40 and cand + 4 + v == off:
            s = b[cand + 4:cand + 4 + v]
            if all(32 <= c < 127 or c == 0 for c in s):
                print(f"  STR32 ending exactly at deflate start: @{cand} len={v} "
                      f"content={s!r}")
