# -*- coding: utf-8 -*-
"""Walk the pre-1.35 FileHeader with u32 alignment taken from the END of the
scenario_instructions str32, and try candidate grammar families against the
measured ground-truth deflate offset.  Diagnostic + hypothesis test.
"""
import os
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
SENTINEL = 1000


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


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


files = []
for root in ROOTS:
    for dp, _d, names in os.walk(root):
        for n in names:
            if n.lower().endswith(EXTS):
                files.append(os.path.join(dp, n))

pre = []
for p in sorted(files):
    b = open(p, "rb").read()
    h, data, diag = locate_deflate(b)
    if h is None:
        pre.append((p, b))

print(f"pre-1.35 files: {len(pre)}")
print("=" * 110)
for p, b in pre:
    off, n = gt(b)
    ver = b[:4].decode("ascii", "replace")
    hl = u32(b, 4)
    sv = u32(b, 8)
    ts = u32(b, 12)
    ilen = u32(b, 16)
    istart = 20
    ins = b[istart:istart + ilen]
    post = istart + ilen
    print(f"\n{ver} {os.path.basename(p):38s} size={len(b):<8} gt={off:<5} out={n}")
    print(f"   HL={hl} SV={sv} TS={ts} inslen={ilen} ins={ins[:20]!r} post_ins={post}")
    o = post
    idx = 0
    while o + 4 <= off:
        v = u32(b, o)
        mark = "  <== 1000 sentinel" if v == SENTINEL else ""
        s = ""
        if 0 < v <= 40 and o + 4 + v <= off:
            cand = b[o + 4:o + 4 + v]
            if all(32 <= c < 127 or c == 0 for c in cand):
                s = f'  str32 "{cand.decode("ascii", "replace")}"'
        print(f"     f{idx:<2d} @{o:<5} = {v:<12d}{s}{mark}")
        o += 4
        idx += 1
    if o != off:
        print(f"     TAIL not u32-aligned: {off - o} leftover byte(s) -> {b[o:off].hex(' ')}")
