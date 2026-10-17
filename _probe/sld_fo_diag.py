# -*- coding: utf-8 -*-
"""The 431 files that read frame_offset=14 still fail one frame later.
Compare a FAILING shadow-only file (a_bird_condor_hoverA_shadow_x1) with a
WORKING shadow-only file (a_bird_condor_flyA_shadow_x1) byte by byte around
the frame 0 -> frame 1 boundary. Read-only.
"""
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
PAD = lambda x: x + ((4 - x % 4) % 4)

for fn in ["a_bird_condor_flyA_shadow_x1.sld", "a_bird_condor_hoverA_shadow_x1.sld",
           "a_hunt_chicken_A_idleA_x1.sld", "a_hunt_sheep_idleA_x1.sld",
           "b_afri_stable_age2_x1.sld"]:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("(missing)", fn)
        continue
    b = open(p, "rb").read()
    sig, ver, n, u1, u2, magic = struct.unpack_from("<4s 2H 2H H", b, 0)
    fo = u2
    print("=" * 78)
    print("%s   size=%d  n=%d  hdr: u1=0x%04x fo=u2=%d magic=0x%04x"
          % (fn, len(b), n, u1, fo, magic))
    print("  hdr bytes 0..24: %s" % b[:24].hex(" "))
    p = fo
    for fi in range(3):
        if p + 12 > len(b):
            print("  frame %d: past EOF @%d" % (fi, p))
            break
        cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, p)
        print("  frame %d @%-6d canvas=%dx%d centre=(%d,%d) ft=0x%02x unk=%d idx=%d"
              % (fi, p, cw, ch, cx, cy, ft, un, idx))
        q = p + 12
        for bit, nm in [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"),
                        (4, "playercolor")]:
            if not (ft & (1 << bit)):
                continue
            size = struct.unpack_from("<I", b, q)[0]
            base = 16 if nm in ("main", "shadow") else 8
            if nm in ("main", "shadow"):
                rect = struct.unpack_from("<4H", b, q + 4)
                fmt, ncmd = struct.unpack_from("<2H", b, q + 12)
                cmds = [(b[q + 16 + 2 * i], b[q + 17 + 2 * i]) for i in range(ncmd)]
                comp = base + 2 * ncmd + 8 * sum(c[1] for c in cmds)
                print("      %-11s @%-6d size=%-7d rect=%-22s fmt=0x%04x ncmd=%-3d comp=%-7d %s"
                      % (nm, q, size, str(rect), fmt, ncmd, comp,
                         "OK" if comp == size else "MISMATCH"))
            else:
                print("      %-11s @%-6d size=%-7d (no rect)" % (nm, q, size))
            nxt = PAD(q + size)
            print("      -> next candidate %d   (PAD(%d+%d))" % (nxt, q, size))
            q = nxt
        p = q
    # brute: where does the NEXT frame header really sit?
    print("  scanning for next sane frame header after frame 0:")
    q = fo + 12
    # walk frame 0 layers to get candidate end
    cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, fo)
    cand = fo + 12
    for bit, nm in [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"),
                    (4, "playercolor")]:
        if not (ft & (1 << bit)):
            continue
        size = struct.unpack_from("<I", b, cand)[0]
        cand = PAD(cand + size)
    print("    computed end-of-frame-0 = %d" % cand)
    for o in range(max(fo + 12, cand - 8), min(len(b) - 12, cand + 24)):
        cw2, ch2, cx2, cy2, ft2, un2, idx2 = struct.unpack_from("<2H 2h 2B H", b, o)
        if 0 < cw2 <= 1024 and 0 < ch2 <= 1024 and abs(cx2) <= 1024 and abs(cy2) <= 1024 \
                and ft2 in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x07, 0x0f, 0x17, 0x1f) \
                and idx2 <= n:
            print("    sane header @%-6d canvas=%dx%d centre=(%d,%d) ft=0x%02x idx=%d"
                  % (o, cw2, ch2, cx2, cy2, ft2, idx2))
    print()
