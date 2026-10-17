# -*- coding: utf-8 -*-
"""Decisive, INDEPENDENT test of the scenario header claim (bounded window).

Claim under test:
    deflate_offset = size of HEADER_LAYOUT[savable],  savable = s32 @8

Because the claimed true offsets top out at 1183, a window of 16..1400 is
sufficient to find the stream for every instance WITHOUT knowing the layout.
That tests the *claim's consequence* -- "a unique exactly-consuming stream
exists at a small offset determined by the header" -- from scratch.

Cheap pre-filter: a raw-deflate stream starts with a block header whose
BTYPE bits (bits 1..2 of the first byte) are 01 (fixed) or 10 (dynamic).
"""
import os
import struct
import zlib
from collections import Counter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
LO, HI = 16, 1400


def collect():
    out = []
    for root in (GAME, USER):
        if not os.path.isdir(root):
            continue
        for b, s, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith((".aoe2scenario", ".scx")):
                    out.append(os.path.join(b, f))
    return sorted(set(out))


def deflate_ok(b, off):
    d = zlib.decompressobj(-15)
    try:
        raw = d.decompress(b[off:])
        raw += d.flush()
    except zlib.error:
        return None
    if not d.eof or d.unused_data:
        return None
    return raw


def plausible(b, off):
    v = b[off]
    return ((v >> 1) & 3) in (1, 2)


def scan(b):
    hits = []
    for off in range(LO, min(HI, len(b))):
        if not plausible(b, off):
            continue
        r = deflate_ok(b, off)
        if r is not None and len(r) > 1000:
            hits.append((off, len(r)))
    return hits


files = collect()
print("standalone scenario files:", len(files))
rows = []
for p in files:
    b = open(p, "rb").read()
    hits = scan(b)
    rows.append(dict(name=os.path.basename(p), size=len(b),
                     ver=b[0:4].decode("latin1"),
                     hlen=struct.unpack_from("<I", b, 4)[0],
                     sav=struct.unpack_from("<i", b, 8)[0],
                     ilen=struct.unpack_from("<I", b, 16)[0],
                     hits=hits))

print()
print("=== TEST 1: exactly-consuming stream exists for every instance ===")
no = [r for r in rows if not r["hits"]]
print("resolved %d / %d ; with no stream: %d"
      % (len(rows) - len(no), len(rows), len(no)))
for r in no:
    print("   NO STREAM:", r["name"], r["size"], r["ver"], "sav", r["sav"])
print()
multi = [r for r in rows if len(r["hits"]) > 1]
print("instances with MULTIPLE candidate offsets: %d"
      % len(multi))
for r in multi[:8]:
    print("   ", r["name"][:46], r["hits"])

print()
print("=== TEST 2: the two 'long header' cases are inside 1400 ===")
for target in ("default0.aoe2scenario", "7V1变态山谷-炮塔盛宴-变态难.aoe2scenario"):
    for r in rows:
        if r["name"] == target:
            print("  %-46s ver=%s size=%d hits=%s"
                  % (r["name"][:46], r["ver"], r["size"], r["hits"]))

print()
print("=== TEST 3/4: str32 unpadded vs u32-aligned ===")
print("  naive_after_instr = 20 + ilen ; aligned = naive + pad4(ilen)")
odd_exceed = even_exceed = 0
odd_n = even_n = 0
odd_examples = []
for r in rows:
    if not r["hits"]:
        continue
    true_off = max(r["hits"], key=lambda t: t[1])[0]
    ilen = r["ilen"]
    naive = 20 + ilen
    aligned = 20 + ilen + ((4 - ilen % 4) % 4)
    if ilen % 2 == 1:
        odd_n += 1
        if aligned > true_off:
            odd_exceed += 1
        if len(odd_examples) < 10:
            odd_examples.append((r["name"], ilen, naive, aligned, true_off))
    else:
        even_n += 1
        if aligned > true_off:
            even_exceed += 1
print("  odd ilen : n=%d  aligned-skip EXCEEDS true offset in %d" % (odd_n, odd_exceed))
print("  even ilen: n=%d  aligned-skip EXCEEDS true offset in %d" % (even_n, even_exceed))
print()
print("  %-44s %6s %6s %6s %6s" % ("file", "ilen", "naive", "algn", "true"))
for nm, il, nv, al, tr in odd_examples:
    print("  %-44s %6d %6d %6d %6d" % (nm[:44], il, nv, al, tr))

print()
print("=== savable / version / header_length (independent) ===")
d = {}
h = {}
for r in rows:
    d.setdefault(r["sav"], Counter())[r["ver"]] += 1
    h.setdefault(r["sav"], Counter())[r["hlen"]] += 1
for k in sorted(d):
    print("  savable=%s  versions=%s  header_length=%s"
          % (k, dict(d[k]), dict(h[k])))
