# -*- coding: utf-8 -*-
"""Build a one-off reference cache of (version, ground-truth deflate offset) for
every scenario-like file on this machine, then dump the exact post-instructions
header region in hex.

The GT offset is used ONLY as a measuring reference for reverse-engineering the
pre-1.36 / odd-length-instructions header grammar.  The deliverable locator
(scenario_header.py) never scans.
"""
import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "gt_cache.json")

ROOTS = [
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario",
]
EXTS = (".aoe2scenario", ".scx")


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def gt_off(b, limit=2048):
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


def collect():
    files = []
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for dp, _d, names in os.walk(root):
            for n in names:
                if n.lower().endswith(EXTS):
                    files.append(os.path.join(dp, n))
    out = []
    for p in sorted(files):
        b = open(p, "rb").read()
        gt, gout = gt_off(b)
        out.append({
            "path": p,
            "size": len(b),
            "version": b[:4].decode("ascii", "replace"),
            "header_length": u32(b, 4),
            "savable": u32(b, 8),
            "timestamp": u32(b, 12),
            "instructions_len": u32(b, 16),
            "gt_offset": gt,
            "gt_out": gout,
        })
    return out


if __name__ == "__main__":
    recs = collect()
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(recs, f, indent=1, ensure_ascii=False)
    print(f"cached {len(recs)} records -> {CACHE}")
    n_ok = sum(1 for r in recs if r["gt_offset"] is not None)
    print(f"gt found: {n_ok}   gt missing: {len(recs) - n_ok}")
    for r in recs:
        if r["gt_offset"] is None:
            print(f"  NO GT: {r['version']} {os.path.basename(r['path'])} size={r['size']}")
