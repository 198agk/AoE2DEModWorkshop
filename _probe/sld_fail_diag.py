# -*- coding: utf-8 -*-
"""Two open questions after sld_validate_all:
   Q1  what is the `unknown2` layer's payload layout?  (0/4,618,175 on both candidates)
   Q2  why do 431 files walk off the rails?  (2.8%; 'frame header past EOF' / 'layer size past EOF')
Read-only.
"""
import os
import struct
import collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
PAD = lambda x: x + ((4 - x % 4) % 4)
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]

print("#" * 78)
print("# Q2  FAILING FILES: what do their first bytes look like?")
print("#" * 78)
FAILD = [
    "a_bird_condor_hoverA_shadow_x1.sld",
    "a_hunt_chicken_A_idleA_x1.sld",
    "b_afri_stable_age2_x1.sld",
    "b_ande_mill_age2_x1.sld",
]
GOODD = ["u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld"]
for fn in FAILD + GOODD:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("  (missing)", fn)
        continue
    b = open(p, "rb").read()
    sig, ver, n, u1, u2, u3 = struct.unpack_from("<4s 2H 2H I", b, 0)
    print()
    print("  %-40s size=%d" % (fn, len(b)))
    print("    hdr: sig=%r ver=%d num_frames=%d u1=0x%04x u2=%d u3=0x%08x"
          % (sig, ver, n, u1, u2, u3))
    print("    first 96 B: %s" % b[:96].hex(" "))
    # first frame header as we parse it
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, 16)
    print("    @16 frame: canvas=%dx%d centre=(%d,%d) ft=0x%02x unk=%d idx=%d"
          % (cw, ch, cx, cy, ft, un, fi))
    # scan for byte patterns that look like a sane frame header (canvas<=512, centre half)
    hits = []
    for o in range(16, min(len(b) - 12, 4000)):
        cw2, ch2, cx2, cy2, ft2, un2, fi2 = struct.unpack_from("<2H 2h 2B H", b, o)
        if 0 < cw2 <= 512 and 0 < ch2 <= 512 and abs(cx2) <= 512 and abs(cy2) <= 512 \
                and ft2 in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x07, 0x0f, 0x17, 0x1f) \
                and fi2 <= n:
            hits.append((o, cw2, ch2, ft2, fi2))
    print("    plausible frame-header offsets in first 4000 B: %d -> %s"
          % (len(hits), hits[:8]))

print()
print("#" * 78)
print("# Q1  unknown2 payload anatomy")
print("#" * 78)
NAMES = ["u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld",
         "u_cav_knight_idlea_x1.sld", "u_monk_west_idlea_x1.sld",
         "u_arc_skirmisher_idlea_x1.sld", "u_inf_spearman_idlea_x1.sld"]


def first_layers(b):
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, 16)
    p = 28
    out = {}
    for bit, nm in BITS:
        if not (ft & (1 << bit)):
            continue
        size = struct.unpack_from("<I", b, p)[0]
        q = p + 4
        rect = None
        if nm in ("main", "shadow"):
            rect = struct.unpack_from("<4H", b, q)
            q += 8
        fmt, ncmd = struct.unpack_from("<2H", b, q)
        q += 4
        cmds = [(b[q + 2 * i], b[q + 2 * i + 1]) for i in range(ncmd)]
        q += 2 * ncmd
        out[nm] = dict(off=p, size=size, rect=rect, fmt=fmt, ncmd=ncmd, cmds=cmds,
                       draws=sum(c[1] for c in cmds), blockoff=q,
                       span=sum(c[0] + c[1] for c in cmds), payload=b[p + 4:p + size])
        p = PAD(p + size)
    return (cw, ch, ft), out


for fn in NAMES:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("  (missing)", fn)
        continue
    b = open(p, "rb").read()
    (cw, ch, ft), L = first_layers(b)
    m, u = L.get("main"), L.get("unknown2")
    if not (m and u):
        print("  %-34s missing main or unknown2" % fn)
        continue
    x1, y1, x2, y2 = m["rect"]
    bw, bh = (x2 - x1 + 3) // 4, (y2 - y1 + 3) // 4
    pay = u["payload"]
    print()
    print("  %-34s main: rect=%dx%d grid=%dx%d span=%d draws=%d ncmd=%d"
          % (fn, x2 - x1, y2 - y1, bw, bh, m["span"], m["draws"], m["ncmd"]))
    print("      unknown2: size=%d payload=%d blockcount=%d bw*bh=%d"
          % (u["size"], len(pay), u["draws"] if u["ncmd"] >= 0 else -1, bw * bh))
    print("      payload hex : %s" % pay[:64].hex(" "))
    # u16 scan: how many leading small u16 before the values go large?
    vals = []
    for i in range(0, min(len(pay), 80), 2):
        vals.append(struct.unpack_from("<H", pay, i)[0])
    print("      u16 head    : %s" % vals[:20])
    # monotone prefix detection
    k = 0
    for i in range(len(vals)):
        if i > 0 and vals[i] < vals[i - 1]:
            break
        if vals[i] > 4096:
            break
        k += 1
    print("      monotone u16 prefix count = %d" % k)
    rest = len(pay) - 2 * k
    print("      bytes after that prefix = %d   /8=%.3f  /7=%.3f  /4=%.3f  /6=%.3f"
          % (rest, rest / 8.0, rest / 7.0, rest / 4.0, rest / 6.0))
    for cand, nm in [(4 + 2 * k, "u32@0+u16[k]"), (2 * k, "u16[k] only"),
                     (4 + 2 * k + 4, "+u32")]:
        r = len(pay) - cand
        print("        if head=%d (%s): rest=%d /8=%.3f /7=%.3f /4=%.3f /6=%.3f"
              % (cand, nm, r, r / 8.0, r / 7.0, r / 4.0, r / 6.0))
