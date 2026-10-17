# -*- coding: utf-8 -*-
"""Hexdump the frame0->frame1 boundary for the 431 stubborn files.
Read-only.
"""
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
PAD = lambda x: x + ((4 - x % 4) % 4)


def frame_hdr(b, o):
    cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, o)
    return dict(o=o, cw=cw, ch=ch, cx=cx, cy=cy, ft=ft, un=un, idx=idx)


def describe(d):
    return "canvas=%dx%d centre=(%d,%d) ft=0x%02x unk=%d idx=%d" % (
        d["cw"], d["ch"], d["cx"], d["cy"], d["ft"], d["un"], d["idx"])


for fn in ["a_bird_condor_flyA_shadow_x1.sld",
           "a_bird_condor_hoverA_shadow_x1.sld",
           "a_hunt_chicken_A_idleA_x1.sld",
           "b_afri_stable_age2_x1.sld",
           "b_ande_mill_age2_x1.sld"]:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("(missing)", fn)
        continue
    b = open(p, "rb").read()
    sig, ver, n, u1, fo, magic = struct.unpack_from("<4s 2H 2H H", b, 0)
    print("=" * 90)
    print("%s  size=%d n=%d fo=%d" % (fn, len(b), n, fo))
    f0 = frame_hdr(b, fo)
    print("  frame0 @%d  %s" % (fo, describe(f0)))
    q = fo + 12
    tot = 0
    for bit, nm in [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"),
                    (4, "playercolor")]:
        if not (f0["ft"] & (1 << bit)):
            continue
        size = struct.unpack_from("<I", b, q)[0]
        print("    %-11s @%-6d declared_size=%-8d layer_end=%d  PAD=%d"
              % (nm, q, size, q + size, PAD(q + size)))
        tot = PAD(q + size)
        q = tot
    print("  computed start of frame1 = %d" % tot)
    lo, hi = max(0, tot - 16), min(len(b) - 14, tot + 20)
    print("  bytes %d..%d:" % (lo, hi))
    for off in range(lo, hi, 16):
        chunk = b[off:off + 16]
        print("    %6d  %-47s  %s" % (off, chunk.hex(" "),
                                      "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))
    print("  sane frame headers found in [%d,%d]:" % (tot - 12, tot + 16))
    for o in range(max(fo + 12, tot - 12), min(len(b) - 14, tot + 16)):
        d = frame_hdr(b, o)
        if 0 < d["cw"] <= 2048 and 0 < d["ch"] <= 2048 and abs(d["cx"]) <= 2048 \
                and abs(d["cy"]) <= 2048 and d["ft"] in (0, 1, 2, 3, 4, 5, 7, 0x0f, 0x17, 0x1f) \
                and d["idx"] <= n:
            print("      @%-7d %s" % (o, describe(d)))
    print()
