# -*- coding: utf-8 -*-
"""unknown2 layer -- fresh ground-truth dump.

Dumps the first N unknown2 layers in full hex together with the sibling
`main` layer's geometry, so every hypothesis can be tested against real bytes
instead of a remembered summary.
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

WANT = ["u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld",
        "u_cav_knight_idlea_x1.sld", "a_alfred_attackA_x1.sld",
        "u_monk_west_idlea_x1.sld", "a_herd_sheep_idleA_x1.sld"]

print("=" * 78)
print("A. targeted dumps")
print("=" * 78)
for name in WANT:
    p = os.path.join(GP, name)
    if not os.path.exists(p):
        print("missing:", name)
        continue
    s = read_sld(p)
    for fr in s.frames[:2]:
        L = fr.layers
        if not isinstance(L, dict) or "main" not in L:
            continue
        r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        x1, y1, w, h, bw, bh = grid_of(r)
        mspan = sum(b for a, b in mcmds)
        print("\n--- %s f%d  ft=0x%02x canvas=%dx%d" %
              (name, fr.index, fr.frame_type, fr.canvas_w, fr.canvas_h))
        print("    layers: %s" % sorted(L))
        print("    main: rect=(%d,%d,%d,%d) %dx%d  grid=%dx%d (%d cells)"
              "  fmt=0x%04x ncmd=%d span=%d size=%d"
              % (x1, y1, w, h, w, h, bw, bh, bw * bh, mfmt, mn, mspan,
                 L["main"].size))
        if "unknown2" not in L:
            print("    unknown2: ABSENT")
            continue
        u = L["unknown2"]
        d = u.data
        print("    unknown2: size=%d  payload=%d B  pad=%d"
              % (u.size, len(d), ((4 - u.size % 4) % 4)))
        print("      hex: %s" % d.hex(" "))
        # interpret as u16 list
        n16 = len(d) // 2
        vals = list(struct.unpack_from("<%dH" % n16, d, 0))
        print("      u16[0:%d]: %s" % (min(n16, 40), vals[:40]))
        if len(d) % 2:
            print("      (odd length: last byte 0x%02x)" % d[-1])

print()
print("=" * 78)
print("B. population statistics over the whole tree")
print("=" * 78)
c = Counter()
ex = []
files = sorted(f for f in os.listdir(GP) if f.endswith(".sld"))
for f in files:
    p = os.path.join(GP, f)
    if os.path.getsize(p) == 0:
        continue
    try:
        s = read_sld(p)
    except Exception:
        continue
    for fr in s.frames:
        L = fr.layers
        if not isinstance(L, dict) or "main" not in L or "unknown2" not in L:
            continue
        u = L["unknown2"]
        d = u.data
        r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
        x1, y1, w, h, bw, bh = grid_of(r)
        g = bw * bh
        mspan = sum(b for a, b in mcmds)
        c["layers"] += 1
        c["payload even"] += 1 if len(d) % 2 == 0 else 0
        c["payload odd"] += 1 if len(d) % 2 else 0
        if len(d) >= 4:
            c["u32@0 == 5"] += 1 if struct.unpack_from("<I", d, 0)[0] == 5 else 0
            c["u16@0 == 5"] += 1 if struct.unpack_from("<H", d, 0)[0] == 5 else 0
            c["u16@2 == 0"] += 1 if struct.unpack_from("<H", d, 2)[0] == 0 else 0
        # strictly-increasing u16 run from offset 0 and from offset 4
        for base, tag in ((0, "off0"), (4, "off4")):
            prev = -1
            k = 0
            while base + 2 * (k + 1) <= len(d):
                v = struct.unpack_from("<H", d, base + 2 * k)[0]
                if v > prev:
                    prev = v
                    k += 1
                else:
                    break
            c["%s run>0" % tag] += 1 if k else 0
            c["%s run==%d" % (tag, k)] += 1
            if k:
                c["%s last==grid" % tag] += 1 if prev == g else 0
                c["%s last<grid" % tag] += 1 if prev < g else 0
                c["%s last>grid" % tag] += 1 if prev > g else 0
                c["%s consumes-all" % tag] += 1 if base + 2 * k == len(d) else 0
        # does size equal 4 + 2*K for K = number of increasing values?
        # mask-layout test
        if len(d) >= 4:
            fmt, n = struct.unpack_from("<2H", d, 0)
            if 4 + 2 * n <= len(d):
                cmds = [struct.unpack_from("<2B", d, 4 + 2 * i) for i in range(n)]
                span = sum(b for a, b in cmds)
                cells = sum(a + b for a, b in cmds)
                c["masklayout size-ok"] += 1 if u.size == 8 + 2 * n + 8 * span else 0
                c["masklayout span==grid"] += 1 if span == g else 0
                c["masklayout cells==grid"] += 1 if cells == g else 0
        if len(ex) < 6 and len(d) < 60:
            ex.append((f, fr.index, u.size, len(d), g, mfmt, mn, mspan,
                       d.hex(" ")))
print()
for k in sorted(c):
    print("  %-28s %10d" % (k, c[k]))
print()
print("  small-layer examples:")
for e in ex:
    print("   ", e)
