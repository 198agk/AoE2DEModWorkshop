# -*- coding: utf-8 -*-
"""Systematic structural hypothesis test for the `unknown2` layer.

All 4,737,215 unknown2 layers start with the literal u32 5 (u16 tag 5, u16 0).
We test candidate layouts and report the fraction that consume `size` EXACTLY.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

LIMIT = 200000
mods = Counter()
u32s = Counter()
sizes = []
payloads = []

n = 0
for f in sorted(os.listdir(GP)):
    if not f.endswith(".sld"):
        continue
    p = os.path.join(GP, f)
    if os.path.getsize(p) == 0:
        continue
    try:
        s = read_sld(p)
    except Exception:
        continue
    for fr in s.frames:
        u = fr.layers.get("unknown2")
        if u is None:
            continue
        mods["size %% 2  = %d" % (u.size % 2)] += 1
        mods["size %% 4  = %d" % (u.size % 4)] += 1
        mods["size %% 8  = %d" % (u.size % 8)] += 1
        mods["(size-4) %% 8 = %d" % ((u.size - 4) % 8)] += 1
        mods["(size-8) %% 8 = %d" % ((u.size - 8) % 8)] += 1
        if len(u.data) >= 12:
            u32s[struct.unpack_from("<I", u.data, 4)[0] & 0xFFFF] += 1
        if len(payloads) < 400:
            payloads.append((f, fr.index, u.size, bytes(u.data)))
        n += 1
        if n >= LIMIT:
            break
    if n >= LIMIT:
        break

print("=== sampled layers:", n, "===")
for k in sorted(mods):
    print("  %-20s %8d" % (k, mods[k]))
print("\n=== u16 value at payload offset 4 (top 12) ===")
print("  ", u32s.most_common(12))


# ---- candidate layouts: check exact consumption across the sample ----
def cand_try(name, fn):
    good = 0
    tot = 0
    for f, idx, size, d in payloads:
        tot += 1
        try:
            if fn(size, d):
                good += 1
        except Exception:
            pass
    print("  %-46s %6d / %6d" % (name, good, tot))
    return good


print("\n=== candidate exact-consumption tests (%d layers) ===" % len(payloads))

def h_u32_n_then_8(size, d):
    c = struct.unpack_from("<I", d, 0)[0]
    return 4 + 8 * c == size

def h_u16_tag_u16_n_then_8(size, d):
    tag, c = struct.unpack_from("<2H", d, 0)
    return 4 + 8 * c == size

def h_u32_n_then_pairs(size, d):
    c = struct.unpack_from("<I", d, 0)[0]
    return 4 + 4 * c == size

def h_u32_n_then_bytes(size, d):
    c = struct.unpack_from("<I", d, 0)[0]
    return 4 + c == size

def h_u32_n_then_2(size, d):
    c = struct.unpack_from("<I", d, 0)[0]
    return 4 + 2 * c == size

def h_u32_n_then_u16_then_8(size, d):
    c = struct.unpack_from("<I", d, 0)[0]
    return 6 + 8 * c == size

def h_lead2_8(size, d):
    # u16 tag, u16 n, then n 8-byte records, then varying tail
    tag, c = struct.unpack_from("<2H", d, 0)
    return 4 + 8 * c <= size

def h_u32_n_runs(size, d):
    # u32 count, then count u16 values, then 8-byte blocks for the rest
    c = struct.unpack_from("<I", d, 0)[0]
    rest = size - 4 - 2 * c
    return c < 4096 and rest >= 0 and rest % 8 == 0

for nm, fn in [("A u32 n | n*8B", h_u32_n_then_8),
               ("B u16 tag,u16 n | n*8B", h_u16_tag_u16_n_then_8),
               ("C u32 n | n*4B", h_u32_n_then_pairs),
               ("D u32 n | n bytes", h_u32_n_then_bytes),
               ("E u32 n | n*2B", h_u32_n_then_2),
               ("F u32 n | u16 pad | n*8B", h_u32_n_then_u16_then_8),
               ("G u16 tag,u16 n | n*8B <=size", h_lead2_8),
               ("H u32 n | n*u16 | (size-4-2n)%8==0", h_u32_n_runs)]:
    cand_try(nm, fn)

# ---- show raw payloads grouped by size for eyeballing ----
print("\n=== 6 raw payloads (first 96 bytes) ===")
seen = set()
for f, idx, size, d in payloads:
    if size in seen:
        continue
    seen.add(size)
    print("  %s f%d size=%d" % (f, idx, size))
    print("     ", d[:96].hex(" "))
    if len(seen) >= 6:
        break
