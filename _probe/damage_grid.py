# -*- coding: utf-8 -*-
"""Which grid does the `damage` layer's command array index?
damage has the playercolor layout (no rect).  Its span matches main's span in
only 24,612 / 66,620 layers, so it must be indexing SOME other grid.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, ceil4

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def rect_span(rect):
    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    return ((w + 3) // 4) * ((h + 3) // 4), (w, h)


def lay_rect(l):
    r = struct.unpack_from("<4H", l.data, 0)
    fmt, n = struct.unpack_from("<2H", l.data, 8)
    cmds = [struct.unpack_from("<2B", l.data, 12 + 2 * i) for i in range(n)]
    return r, sum(c[1] for c in cmds)


def lay_mask(l):
    fmt, n = struct.unpack_from("<2H", l.data, 0)
    cmds = [struct.unpack_from("<2B", l.data, 4 + 2 * i) for i in range(n)]
    return sum(c[1] for c in cmds), fmt


FILES = [
    "b_afri_archery_range_age2_x1.sld",
    "b_afri_stable_age2_x1.sld",
    "b_afri_house_age2_x1.sld",
    "b_dark_barracks_age1_x1.sld",
    "b_west_town_center_age2_back_x1.sld",
    "b_west_castle_age3_x1.sld",
]
for f in FILES:
    p = os.path.join(GP, f)
    if not os.path.exists(p):
        print("(missing)", f)
        continue
    s = read_sld(p)
    fr = s.frames[0]
    L = fr.layers
    print("\n--- %s frame0 ft=0x%02x canvas=%dx%d" % (f, fr.frame_type, fr.canvas_w, fr.canvas_h))
    for nm in ("main", "shadow", "playercolor", "damage"):
        if nm not in L:
            continue
        if nm in ("main", "shadow"):
            r, sp = lay_rect(L[nm])
            gs, (rw, rh) = rect_span(r)
            print("  %-12s rect=%-24s wh=%dx%d size=%-6d span=%-6d bw*bh=%d %s"
                  % (nm, r, rw, rh, L[nm].size, sp, gs, "MATCH" if sp == gs else ""))
        else:
            sp, fmt = lay_mask(L[nm])
            print("  %-12s fmt=0x%04x size=%-6d span=%-6d"
                  % (nm, fmt, L[nm].size, sp))
    # relations
    if "damage" in L and "main" in L:
        r, msp = lay_rect(L["main"])
        gs, wh = rect_span(r)
        dsp, dfmt = lay_mask(L["damage"])
        pcs = lay_mask(L["playercolor"])[0] if "playercolor" in L else -1
        print("  damage.span %d vs main.span %d vs bw*bh %d vs pc.span %d"
              % (dsp, msp, gs, pcs))
        print("  ratios: d/mains s=%.4f  d/bwbh=%.4f  d/pc=%.4f"
              % (dsp / max(1, msp), dsp / max(1, gs), dsp / max(1, pcs)))

# bulk: what fraction of damage layers have span == bw*bh of main's rect?
print("\n=== bulk relation over all damage layers ===")
cnt = Counter()
ok = 0
tot = 0
for f in os.listdir(GP):
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
        dsp = lay_mask(L["damage"])[0]
        r, msp = lay_rect(L["main"])
        gs, wh = rect_span(r)
        pcs = lay_mask(L["playercolor"])[0] if "playercolor" in L else -1
        if dsp == gs:
            cnt["dspan==bw*bh(main rect)"] += 1
        if dsp == msp:
            cnt["dspan==main.span"] += 1
        if dsp == pcs:
            cnt["dspan==pc.span"] += 1
        # half-res grid?
        hw, hh = (wh[0] + 7) // 8, (wh[1] + 7) // 8
        if dsp == hw * hh:
            cnt["dspan==(w/8)*(h/8)"] += 1
print("total frames with damage+main:", tot)
for k, v in cnt.most_common():
    print("  %-28s %6d  (%.2f%%)" % (k, v, 100.0 * v / max(1, tot)))
