# -*- coding: utf-8 -*-
"""Analyse the .aoe2campaign header to find a structural member table.

Strategy: parse the campaign "FileHeader" (version 2.00), then look for u32 runs
that equal the known member start offsets, or u32 fields whose values are member
counts / sizes.  Compare across several campaign files so the conclusion is not
an artefact of one file.
"""
import os
import re
import struct
import sys

CAMP_DIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"
VER_RE = re.compile(rb"1\.\d\d\x00\x00\x00\x00")

FILES = ["acam1.aoe2campaign", "acam2.aoe2campaign", "acam3.aoe2campaign",
         "xcam1.aoe2campaign", "acam4.aoe2campaign"]


def u32s(b, start, end):
    out = []
    for o in range(start, min(end, len(b)) - 3, 4):
        out.append((o, struct.unpack_from("<I", b, o)[0]))
    return out


for name in FILES:
    p = os.path.join(CAMP_DIR, name)
    if not os.path.isfile(p):
        print(f"!! missing {p}")
        continue
    b = open(p, "rb").read()
    hits = [m.start() for m in VER_RE.finditer(b)]
    print("=" * 100)
    print(f"{name}  size={len(b)}  version={b[:4]!r}  magic_hits={len(hits)} at {hits[:12]}")
    if hits:
        print(f"  first member header offset = {hits[0]}")
        print(f"  bytes[0:hits[0]] = {b[:hits[0]].hex(' ')[:1200]}")
    # look for u32 values equal to member offsets, in the pre-first-member region
    pre = hits[0] if hits else min(4096, len(b))
    print(f"  -- u32 scan of [0,{pre}) that look like member offsets/sizes --")
    for o, v in u32s(b, 0, pre):
        if v in hits:
            print(f"     off={o:5d} value={v}  == MEMBER OFFSET (hit index {hits.index(v)})")
    # also look for pairs
    print("  -- 8-byte pairs (u32,u32) in [0,%d) that look like (size,offset) --" % pre)
    for o, v in u32s(b, 0, pre - 8):
        _, w = struct.unpack_from("<II", b, o)
        if w in hits and 0 < v < len(b):
            print(f"     off={o:5d} pair=({v}, {w})  -> (size={v}, member_offset={w})")
