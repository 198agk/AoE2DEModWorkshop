# -*- coding: utf-8 -*-
"""DECISIVE: is the SLD playercolor layer a MASK or a PALETTE INDEX plane?

Corrected layer geometry (all confirmed by comp==size==declared over 300 frames):
  main / shadow : u32 size | 4xu16 rect | u16 fmt | u16 ncmd | cmds | blocks
                  block grid = ceil(rect_w/4) x ceil(rect_h/4), and
                  sum(skip+draw) == bw*bh  (verified: archer 121=11*11,
                  militia 72=6*12) -> the command array is a LINEAR run list
                  over the block grid, rows wrapping at width bw.
  playercolor  : u32 size | u16 fmt | u16 ncmd | cmds | blocks
                  NO rect.  Its sum(skip+draw) EQUALS main's (121 and 72) ->
                  it shares main's block grid 1:1.

So the playercolor plane must be decoded on MAIN's grid, then compared pixel-wise
to main.  Discriminators:
  D1 SUBSET   : nonzero pc pixels must lie on main-opaque pixels.
  D2 VALUES   : mask => many grey levels / smooth; index => few small ints.
  D3 RENDER   : main tinted by pc*teamcolour must reproduce the in-game look.
Read-only.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import struct
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = _HERE_PATH("_shots", "playerclr")
os.makedirs(OUT, exist_ok=True)

u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
PAD = lambda x: x + ((4 - x % 4) % 4)

def parse_frame(b, off):
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, off)
    p = off + 12
    Ls = {}
    for bit, nm in BITS:
        if not (ft & (1 << bit)):
            continue
        size = u32(b, p)
        q = p + 4
        rect = None
        if nm in ("main", "shadow"):
            rect = struct.unpack_from("<4H", b, q)
            q += 8
        fmt, ncmd = struct.unpack_from("<2H", b, q)
        q += 4
        cmds = [(b[q + 2 * i], b[q + 2 * i + 1]) for i in range(ncmd)]
        q += 2 * ncmd
        Ls[nm] = dict(size=size, rect=rect, fmt=fmt, ncmd=ncmd, cmds=cmds,
                      draws=sum(c[1] for c in cmds), blocks=q,
                      span=sum(c[0] + c[1] for c in cmds))
        p = PAD(p + size)
    return (cw, ch, ft, fi), Ls, p

def decode_on_grid(b, L, bw, bh, bc4):
    im = Image.new("RGBA", (bw * 4, bh * 4), (0, 0, 0, 0))
    px = im.load()
    o = L["blocks"]
    bx = by = 0
    for skip, draw in L["cmds"]:
        for _ in range(skip):
            bx += 1
            if bx >= bw:
                bx, by = 0, by + 1
        for _ in range(draw):
            blk = b[o:o + 8]
            o += 8
            if len(blk) < 8:
                break
            if bc4:
                c0, c1 = blk[0], blk[1]
                if c0 > c1:
                    lut = [c0, c1] + [((7 - i) * c0 + i * c1) // 7 for i in range(1, 7)]
                else:
                    lut = [c0, c1] + [((5 - i) * c0 + i * c1) // 5 for i in range(1, 5)] + [0, 255]
                v = int.from_bytes(blk[2:8], "little")
                vals = [lut[(v >> (3 * k)) & 7] for k in range(16)]
            else:
                c0, c1 = struct.unpack_from("<HH", blk, 0)
                idx = struct.unpack_from("<I", blk, 4)[0]
                ch_ = lambda c: (((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63,
                                 (c & 31) * 255 // 31, 255)
                a, b2 = ch_(c0), ch_(c1)
                if c0 > c1:
                    c2 = tuple((2 * a[i] + b2[i]) // 3 for i in range(3)) + (255,)
                    c3 = tuple((a[i] + 2 * b2[i]) // 3 for i in range(3)) + (255,)
                else:
                    c2 = tuple((a[i] + b2[i]) // 2 for i in range(3)) + (255,)
                    c3 = (0, 0, 0, 0)
                lut = [a, b2, c2, c3]
                vals = [lut[(idx >> (2 * k)) & 3] for k in range(16)]
            for j in range(4):
                yy = by * 4 + j
                for i in range(4):
                    xx = bx * 4 + i
                    if 0 <= xx < im.size[0] and 0 <= yy < im.size[1]:
                        px[xx, yy] = ((vals[j * 4 + i],) * 3 + (255,)) if bc4 else vals[j * 4 + i]
            bx += 1
            if bx >= bw:
                bx, by = 0, by + 1
    return im

print("=" * 78)
print("BLOCK-GRID IDENTITY: does playercolor.span == main.span?  (decisive for sharing)")
print("=" * 78)
names = ["u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld",
         "u_cav_knight_idlea_x1.sld", "u_monk_west_idlea_x1.sld",
         "u_arc_skirmisher_idlea_x1.sld"]
data = {}
for fn in names:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        continue
    b = open(p, "rb").read()
    (cw, ch, ft, fi), Ls, endp = parse_frame(b, 16)
    m, q = Ls.get("main"), Ls.get("playercolor")
    if not (m and q):
        continue
    x1, y1, x2, y2 = m["rect"]
    bw, bh = (x2 - x1 + 3) // 4, (y2 - y1 + 3) // 4
    print("  %-32s main_rect=%s grid=%dx%d main.span=%-4d pc.span=%-4d match=%s"
          % (fn, m["rect"], bw, bh, m["span"], q["span"], m["span"] == q["span"]))
    data[fn] = (b, cw, ch, m, q, bw, bh)

print()
print("=" * 78)
print("D1 SUBSET / D2 VALUES  (pc decoded on MAIN's block grid)")
print("=" * 78)
for fn, (b, cw, ch, m, q, bw, bh) in data.items():
    imM = decode_on_grid(b, m, bw, bh, False)
    imQ = decode_on_grid(b, q, bw, bh, True)
    # crop each to its own rect extents (main uses its rect; pc shares it)
    x1, y1, x2, y2 = m["rect"]
    rw, rh = x2 - x1, y2 - y1
    imM = imM.crop((0, 0, rw, rh))
    imQ = imQ.crop((0, 0, rw, rh))
    op = set((x, y) for y in range(rh) for x in range(rw) if imM.getpixel((x, y))[3] > 0)
    nz = [(x, y) for y in range(rh) for x in range(rw) if imQ.getpixel((x, y))[0] > 0]
    ins = sum(1 for t in nz if t in op)
    vals = [imQ.getpixel(t)[0] for t in nz]
    allv = sorted(set(imQ.getpixel((x, y))[0] for y in range(rh) for x in range(rw)))
    print("  %-32s rect=%dx%d main_opaque=%-4d pc_nz=%-4d inside=%-4d (%.0f%%)"
          % (fn, rw, rh, len(op), len(nz), ins, 100.0 * ins / max(1, len(nz))))
    print("       pc levels present: %d distinct, %s%s"
          % (len(allv), allv[:14], "..." if len(allv) > 14 else ""))
    if vals:
        print("       pc nonzero: min=%d max=%d mean=%.1f" % (min(vals), max(vals), sum(vals) / len(vals)))
    # render
    tint = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    tp, mp, qp = tint.load(), imM.load(), imQ.load()
    for y in range(rh):
        for x in range(rw):
            r, g, bl, a = mp[x, y]
            if a == 0:
                continue
            f = qp[x, y][0] / 255.0
            tp[x, y] = (int(r * (1 - f) + 255 * f), int(g * (1 - f) + 10 * f), int(bl * (1 - f)), a)
    sh = Image.new("RGBA", (rw * 3 + 24, rh), (40, 40, 40, 255))
    sh.alpha_composite(imM, (0, 0))
    sh.alpha_composite(imQ, (rw + 12, 0))
    sh.alpha_composite(tint, (rw * 2 + 24, 0))
    sh = sh.resize((sh.size[0] * 6, sh.size[1] * 6), Image.NEAREST)
    out = os.path.join(OUT, "mask_" + fn.split(".")[0] + ".png")
    sh.save(out)
    print("       -> %s (main | pc plane | main tinted by pc*red)" % os.path.basename(out))
