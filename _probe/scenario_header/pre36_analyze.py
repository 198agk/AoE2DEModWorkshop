# -*- coding: utf-8 -*-
"""Ground-truth offsets + header prefixes for every scenario the 1.36+ model rejects.
Diagnostic only: the brute force here exists solely to obtain the reference answer
for the pre-1.36 (1.21/1.33) layout, which the structured model does not yet cover.
"""
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenario_header import locate_deflate  # noqa: E402

ROOTS = [
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\scenario",
]
EXTS = (".aoe2scenario", ".scx")


def gt(b, limit=16384):
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


files = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dp, _d, names in os.walk(root):
        for n in names:
            if n.lower().endswith(EXTS):
                files.append(os.path.join(dp, n))

pre36 = []
for p in sorted(files):
    b = open(p, "rb").read()
    h, data, diag = locate_deflate(b)
    if h is None:
        pre36.append((p, b))

print(f"files rejected by the 1.36+ model: {len(pre36)}")
print("=" * 100)
rows = []
for p, b in pre36:
    off, n = gt(b)
    rows.append((b[:4].decode("ascii", "replace"), off, n, len(b), os.path.basename(p), b))
    print(f"{b[:4]!r}  gt_off={off:<6} gt_out={n:<9} size={len(b):<9} {os.path.basename(p)}")
    print(f"    prefix[0:{off}] = {b[:off].hex(' ')}")

print("=" * 100)
print("-- grouped by version tag --")
by_ver = {}
for ver, off, n, sz, name, b in rows:
    by_ver.setdefault(ver, []).append((off, n, sz, name, b))
for ver, items in sorted(by_ver.items()):
    offs = [i[0] for i in items]
    print(f"  {ver}: n={len(items)} gt_offsets={sorted(set(offs))}")

print("-- u32 walk from offset 4 for a few representatives --")
for ver, items in sorted(by_ver.items()):
    for off, n, sz, name, b in items[:2]:
        print(f"\n  {ver} {name} gt_off={off}")
        o = 4
        while o + 4 <= off:
            v = struct.unpack_from("<I", b, o)[0]
            s = ""
            if 0 < v <= 64 and o + 4 + v <= off:
                cand = b[o + 4:o + 4 + v]
                if all(32 <= c < 127 or c == 0 for c in cand):
                    s = f'  str32 "{cand.decode("ascii","replace")}"'
            print(f"      @{o:4d} u32={v:<12d}{s}")
            o += 4
