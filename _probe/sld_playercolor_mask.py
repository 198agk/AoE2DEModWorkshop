# -*- coding: utf-8 -*-
"""Decisive structural test of the SLD playercolor layer: MASK or INDEX?

Corrected facts (validated: comp==size 300/300 for main, shadow, playercolor):
  frame header 12 B; per layer present in frame_type (ascending bit):
      u32 size | payload | PAD to 4
  main / shadow payload: 4xu16 rect | u16 fmt | u16 ncmd | ncmd*(u8,u8) | blocks
  playercolor payload  : u16 fmt | u16 ncmd | ncmd*(u8,u8) | blocks
      -> NO rect: the layer spans the FRAME CANVAS, so its block grid is
         ceil(canvas_w/4) x ceil(canvas_h/4) and it must be cropped at the same
         canvas coordinates as main, NOT at (0,0).

Two independent discriminators:
  D1 SUBSET: every nonzero playercolor pixel must fall on a main-opaque pixel.
     A palette-index layer has no reason to satisfy this; a silhouette mask must.
  D2 SHAPE: the playercolor mass should correlate with the main layer's opaque
     silhouette (IoU / correlation), and be grey-valued rather than index-valued.
Read-only.
"""
import os
import struct
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\playerclr"
os.makedirs(OUT, exist_ok=True)

u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]
BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
PAD = lambda x: x + ((4 - x % 4) % 4)


def layers_of_frame(b, off):
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, off)
    p = off + 12
    out = []
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
        out.append(dict(name=nm, size=size, rect=rect, fmt=fmt, ncmd=ncmd,
                        cmds=cmds, draws=sum(c[1] for c in cmds), blocks=q, canvas=(cw, ch)))
        p = PAD(p + size)
    return (cw, ch, ft, fi), out, p


def decode(b, L, bc4, canvas):
    cw, ch = canvas
    bw, bh = (cw + 3) // 4, (ch + 3) // 4
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
                vals = [lut[v >> (3 * k) & 7] for k in range(16)]
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
                        px[xx, yy] = (vals[j * 4 + i],) * 3 + (255,) if bc4 else vals[j * 4 + i]
            bx += 1
            if bx >= bw:
                bx, by = 0, by + 1
    return im.crop((0, 0, cw, ch))


print("=" * 76)
print("D1/D2  subset + shape test, mask decoded on the CANVAS grid and cropped at main's rect")
print("=" * 76)
for fn in (u"u_arc_archer_idlea_x1.sld", u"u_inf_militia_idlea_x1.sld",
           u"u_cav_knight_idlea_x1.sld", u"u_monk_west_idlea_x1.sld",
           u"u_arc_skirmisher_idlea_x1.sld"):
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("   (skip, missing)", fn)
        continue
    b = open(p, "rb").read()
    (cw, ch, ft, fi), Ls, endp = layers_of_frame(b, 16)
    by = {L["name"]: L for L in Ls}
    m, q = by.get("main"), by.get("playercolor")
    if not (m and q):
        print("   %-32s no main/pc (layers=%s)" % (fn, list(by)))
        continue
    imM_full = decode(b, m, False, (cw, ch))
    imQ_full = decode(b, q, True, (cw, ch))
    x1, y1, x2, y2 = m["rect"]
    imM = imM_full.crop((x1, y1, x2, y2))
    imQ = imQ_full.crop((x1, y1, x2, y2))
    op = set((xx, yy) for yy in range(imM.size[1]) for xx in range(imM.size[0])
             if imM.getpixel((xx, yy))[3] > 0)
    nz = [(xx, yy) for yy in range(imQ.size[1]) for xx in range(imQ.size[0])
          if imQ.getpixel((xx, yy))[0] > 0]
    ins = sum(1 for t in nz if t in op)
    vals = [imQ.getpixel(t)[0] for t in nz]
    g = lambda im: set((xx, yy) for yy in range(im.size[1]) for xx in range(im.size[0])
                       if im.getpixel((xx, yy))[3] > 0)
    inter = len(op & set(nz))
    union = len(op | set(nz))
    print("   %-32s canvas=%dx%d main_rect=%s" % (fn, cw, ch, m["rect"]))
    print("        main_opaque=%-5d pc_nonzero=%-5d subset_inside=%-5d (%.1f%%)  IoU=%.2f"
          % (len(op), len(nz), ins, 100.0 * ins / max(1, len(nz)), inter / max(1, union)))
    if vals:
        print("        pc gray: min=%d max=%d mean=%.1f distinct=%d  (index layer would show"
              % (min(vals), max(vals), sum(vals) / len(vals), len(set(vals))))
        print("                 evenly spread integer codes 0..255 with weak spatial coherence)")
    # render
    sh = Image.new("RGBA", (imM.size[0] * 3 + 24, imM.size[1]), (40, 40, 40, 255))
    sh.alpha_composite(imM, (0, 0))
    sh.alpha_composite(imQ.convert("RGBA"), (imM.size[0] + 12, 0))
    tint = Image.new("RGBA", imM.size, (0, 0, 0, 0))
    tp = tint.load()
    mp = imM.load()
    qp = imQ.load()
    for yy in range(imM.size[1]):
        for xx in range(imM.size[0]):
            r, gg, bl, a = mp[xx, yy]
            if a == 0:
                continue
            f = qp[xx, yy][0] / 255.0
            tp[xx, yy] = (int(r * (1 - f) + 255 * f), int(gg * (1 - f)), int(bl * (1 - f)), a)
    sh.alpha_composite(tint, (imM.size[0] * 2 + 24, 0))
    sh = sh.resize((sh.size[0] * 5, sh.size[1] * 5), Image.NEAREST)
    out = os.path.join(OUT, "fixed_" + fn.split(".")[0] + ".png")
    sh.save(out)
    print("        wrote", os.path.basename(out), sh.size)
