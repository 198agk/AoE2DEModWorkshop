# -*- coding: utf-8 -*-
"""Pin down what grid the `damage` layer indexes.

Verified: damage uses the MASK header layout (no rect):
    size == 8 + 2*ncmd + 8*sum(draw)      [66620/66620]
but its fmt is 0x0100 (same code as main) -- so it is a COLOUR layer, not a
BC4 mask.  Its span matches main.span in only 36.9% of layers, so it must
reuse some other layer's rectangle.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def lay_rect(l):
    r = struct.unpack_from("<4H", l.data, 0)
    fmt, n = struct.unpack_from("<2H", l.data, 8)
    cmds = [struct.unpack_from("<2B", l.data, 12 + 2 * i) for i in range(n)]
    return r, fmt, n, sum(c[1] for c in cmds)


def lay_mask(l):
    fmt, n = struct.unpack_from("<2H", l.data, 0)
    cmds = [struct.unpack_from("<2B", l.data, 4 + 2 * i) for i in range(n)]
    return fmt, n, sum(c[1] for c in cmds)


def gs(rect):
    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    return ((w + 3) // 4) * ((h + 3) // 4)


cnt = Counter()
tot = 0
mism = []
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
        L = fr.layers
        if not isinstance(L, dict) or "damage" not in L or "main" not in L:
            continue
        tot += 1
        dfmt, dn, dsp = lay_mask(L["damage"])
        mrect, mfmt, mn, msp = lay_rect(L["main"])
        cands = {
            "main.span": msp,
            "main bw*bh": gs(mrect),
        }
        if "shadow" in L:
            srect, sfmt, sn, ssp = lay_rect(L["shadow"])
            cands["shadow.span"] = ssp
            cands["shadow bw*bh"] = gs(srect)
        if "playercolor" in L:
            cands["pc.span"] = lay_mask(L["playercolor"])[2]
        cands["canvas/4 grid"] = ((fr.canvas_w + 3) // 4) * ((fr.canvas_h + 3) // 4)
        hit = [k for k, v in cands.items() if v == dsp]
        if hit:
            for k in hit:
                cnt[k] += 1
        else:
            cnt["NONE"] += 1
            if len(mism) < 6:
                mism.append((f, fr.index, dsp, msp, gs(mrect), dfmt, dn, mn))
        cnt["dmg_bits==3"] += 1

print("total damage layers:", tot)
for k, v in cnt.most_common(12):
    print("  %-16s %7d  (%.2f%%)" % (k, v, 100.0 * v / tot))
print("\nmismatch examples (file, idx, dspan, main.span, main bw*bh, dfmt, dncmd, mncmd):")
for m in mism:
    print("   ", m)

# how many damage layers match main's grid AND have dtype fmt == main fmt
print("\n=== does the damage block count equal its span? ===")
eq = 0
ne = 0
for f in sorted(os.listdir(GP))[:3000]:
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
        if not isinstance(L, dict) or "damage" not in L:
            continue
        d = L["damage"]
        fmt, n, sp = lay_mask(d)
        nb = (d.size - 8 - 2 * n) // 8
        if nb == sp:
            eq += 1
        else:
            ne += 1
print("blocks==span: %d   mismatch: %d" % (eq, ne))
