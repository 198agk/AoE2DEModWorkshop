# -*- coding: utf-8 -*-
"""Dump the campaign per-member record table region with exact offsets.

We know: the first embedded scenario's version tag sits at some offset F (found via
the 1.xx magic).  Immediately before it there is a table of fixed-stride records.
This script dumps [START, F) with u32 columns so the record layout can be read off
directly instead of guessed.
"""
import os
import re
import struct
import sys

CAMP_DIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"
VER_RE = re.compile(rb"1\.\d\d\x00\x00\x00\x00")
DIFF_RE = re.compile(rb"2\.0\d\x00\x00\x00\x00")

FILES = sorted(f for f in os.listdir(CAMP_DIR) if f.endswith(".aoe2campaign"))


def dump(b, start, end):
    lines = []
    for o in range(start, end, 4):
        chunk = b[o:o + 4]
        if len(chunk) < 4:
            break
        v = struct.unpack("<I", chunk)[0]
        # printable if 4 ASCII chars
        try:
            asc = chunk.decode("ascii")
            printable = all(32 <= c < 127 for c in chunk)
        except Exception:
            asc = ""
            printable = False
        tag = f'"{asc}"' if printable else ""
        lines.append(f"   {o:6d}  {chunk.hex(' ')}  u32={v:<12d} {tag}")
    return "\n".join(lines)


for name in FILES[:6]:
    p = os.path.join(CAMP_DIR, name)
    b = open(p, "rb").read()
    hits = [m.start() for m in VER_RE.finditer(b)]
    diffs = [m.start() for m in DIFF_RE.finditer(b)]
    print("=" * 100)
    print(f"{name}  size={len(b)}  scenario_version_tags={hits}")
    print(f"   diff_version_tags(2.0x)={diffs}")
    if not hits:
        continue
    # last scenario tag before the first member = the campaign's own trailing record?
    F = hits[0]
    # dump from the record table beginning.  Walk back from F in 2-byte steps and
    # find where the table starts by looking for the first u32 equal to a member
    # offset (F itself, or later hits).
    start = None
    for o in range(260, F - 4, 4):
        v = struct.unpack_from("<I", b, o)[0]
        if v in hits and o + 4 <= F:
            start = max(260, o - 8)
            break
    print(f"   first member at F={F}; table dump [{start},{F}) "
          f"len={F - start} / {len(hits)} members = {(F - start) / len(hits):.2f} B/record")
    print(dump(b, start, F))
