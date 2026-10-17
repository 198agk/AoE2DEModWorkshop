# -*- coding: utf-8 -*-
"""unknown2 -- split the tail at the cumulative offsets given by the head.

If the increasing u16 run is a cumulative-offset table, slicing the tail at
those offsets must yield N self-similar records with a small leftover.
That is a falsifiable prediction: garbage slicing looks like garbage.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def run_vals(d, base=4):
    vals = []
    prev = -1
    k = 0
    while base + 2 * (k + 1) <= len(d):
        v = struct.unpack_from("<H", d, base + 2 * k)[0]
        if v > prev:
            vals.append(v)
            prev = v
            k += 1
        else:
            break
    return vals


def show(name, fi=0):
    p = os.path.join(GP, name)
    if not os.path.exists(p):
        print("missing", name)
        return
    s = read_sld(p)
    fr = s.frames[fi]
    L = fr.layers
    u = L["unknown2"]
    d = u.data
    vals = run_vals(d)
    hdr = 4 + 2 * len(vals)
    tail = d[hdr:]
    print("=" * 76)
    print("%s f%d  size=%d payload=%d  K=%d  header=%d  tail=%d  leftover=%d"
          % (name, fi, u.size, len(d), len(vals), hdr, len(tail),
             len(tail) - (vals[-1] if vals else 0)))
    print("  offsets:", vals)
    prev = 0
    for i, v in enumerate(vals):
        seg = tail[prev:v]
        print("   rec%-3d len=%-5d %s" % (i, len(seg), seg.hex(" ")))
        prev = v
    if prev < len(tail):
        print("   LEFT  len=%-5d %s" % (len(tail) - prev, tail[prev:].hex(" ")))


for nm, fi in (("u_arc_archer_idlea_x1.sld", 0),
               ("u_inf_militia_idlea_x1.sld", 0),
               ("u_cav_knight_idlea_x1.sld", 0),
               ("a_alfred_decayA_x1.sld", 41)):
    show(nm, fi)

# ---- population test: is the slicing self-similar? ----
print()
print("=" * 76)
print("population: segment-length structure")
print("=" * 76)
c = Counter()
seg_len_hist = Counter()
leftover_hist = Counter()
n = 0
for f in sorted(os.listdir(GP))[:4000]:
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
        L = fr.layers
        if not isinstance(L, dict) or "unknown2" not in L:
            continue
        d = L["unknown2"].data
        vals = run_vals(d)
        if not vals:
            continue
        hdr = 4 + 2 * len(vals)
        tail = d[hdr:]
        n += 1
        leftover_hist[len(tail) - vals[-1]] += 1
        prev = 0
        for v in vals:
            seg_len_hist[v - prev] += 1
            prev = v
        # does every segment start with the same byte?
        prev = 0
        for v in vals:
            if v > prev and v <= len(tail):
                c["seg[0]=0x%02x" % tail[prev]] += 1
            prev = v
print("  layers examined:", n)
print("  segment first-byte histogram (top 12):", c.most_common(12))
print("  segment length histogram (top 12):", seg_len_hist.most_common(12))
print("  leftover histogram (top 12):", leftover_hist.most_common(12))
