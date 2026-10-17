# -*- coding: utf-8 -*-
"""CORRECTED SLD layer decoder + structural test of the player-colour layer.

What was wrong before: I assumed every layer used the rect+cmd header and
advanced without 4-byte padding, so the "playercolor" tile was pure garbage.
The walk that actually validates (300 consecutive frames, idx 0..299, no breaks)
is:

  frame header 12 B:  canvas_w canvas_h (u16) centre_x centre_y (i16)
                      frame_type (u8) unknown (u8) frame_index (u16)
  for each bit set in frame_type (bit0 main, bit1 shadow, bit2 unknown2,
  bit3 damage, bit4 playercolor), in ascending bit order:
      u32 layer_size   (includes the 4 bytes itself)
      payload ...
      PAD to 4-byte alignment

Payload layout differs by layer kind:
  main / shadow : 4xu16 rect | u16 fmt | u16 ncmd | ncmd*(u8 skip,u8 draw) | blocks
                  comp = 16 + 2*ncmd + 8*sum(draw)
  playercolor   : u16 fmt | u16 ncmd | cmds | blocks     (no rect: spans canvas)
                  comp = 8 + 2*ncmd + 8*sum(draw)

This script:
  S1  re-derives the per-kind layout empirically over 300 frames (comp==size rate)
  S2  decodes main as BC1(RGBA) and playercolor as BC4(gray) correctly
  S3  STRUCTURAL TEST: are the playercolor's non-zero pixels a SUBSET of the
      main layer's opaque pixels?  A palette-INDEX layer cannot satisfy this;
      a mask can.  Report the overlap fraction.
  S4  render: main | playercolor mask | main tinted by mask*red
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

def read_layer(b, p, kind):
    """Return dict with layout info; comp = computed size."""
    size = u32(b, p)
    q = p + 4
    rect = None
    if kind in ("main", "shadow"):
        x1, y1, x2, y2 = struct.unpack_from("<4H", b, q)
        q += 8
        rect = (x1, y1, x2, y2)
    fmt, ncmd = struct.unpack_from("<2H", b, q)
    q += 4
    cmds = [(b[q + 2 * i], b[q + 2 * i + 1]) for i in range(ncmd)]
    q += 2 * ncmd
    draws = sum(c[1] for c in cmds)
    comp = (q - p) + 8 * draws
    return dict(start=p, size=size, rect=rect, fmt=fmt, ncmd=ncmd, cmds=cmds,
                draws=draws, blocks_off=q, comp=comp)

def decode(b, L, bc4):
    """Decode blocks into an image using the command array (skip/draw)."""
    if L["rect"]:
        x1, y1, x2, y2 = L["rect"]
        w, h = x2 - x1, y2 - y1
    else:
        w = h = None
    o = L["blocks_off"]
    # grid dims from the block count actually addressed
    nblk = sum(c[0] + c[1] for c in L["cmds"])
    if w is None:
        # no rect: infer a square grid from total addressed blocks
        import math
        g = max(1, int(math.ceil(math.sqrt(nblk))))
        w = h = g * 4
    bw = (w + 3) // 4
    im = Image.new("RGBA", (bw * 4, bw * 4), (0, 0, 0, 0))
    px = im.load()
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
                ch = lambda c: ((c >> 11 & 31) * 255 // 31, (c >> 5 & 63) * 255 // 63,
                                (c & 31) * 255 // 31, 255)
                a, b2 = ch(c0), ch(c1)
                if c0 > c1:
                    c2 = tuple((2 * a[i] + b2[i]) // 3 for i in range(3)) + (255,)
                    c3 = tuple((a[i] + 2 * b2[i]) // 3 for i in range(3)) + (255,)
                else:
                    c2 = tuple((a[i] + b2[i]) // 2 for i in range(3)) + (255,)
                    c3 = (0, 0, 0, 0)
                lut = [a, b2, c2, c3]
                vals = [lut[idx >> (2 * k) & 3] for k in range(16)]
            for j in range(4):
                yy = by * 4 + j
                for i in range(4):
                    xx = bx * 4 + i
                    if 0 <= xx < im.size[0] and 0 <= yy < im.size[1]:
                        px[xx, yy] = (vals[j * 4 + i],) * 3 + (255,) if bc4 else vals[j * 4 + i]
            bx += 1
            if bx >= bw:
                bx, by = 0, by + 1
    return im

print("=" * 74)
print("S1  layout verification over 300 frames of u_arc_archer_idlea_x1.sld")
b = open(os.path.join(GP, u"u_arc_archer_idlea_x1.sld"), "rb").read()
off = 16
stat = {nm: [0, 0] for _, nm in BITS}
frames = 0
LAY = {}
while off + 12 <= len(b) and frames < 300:
    cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, off)
    p = off + 12
    for bit, nm in BITS:
        if not (ft & (1 << bit)):
            continue
        L = read_layer(b, p, nm)
        LAY.setdefault(nm, L)
        stat[nm][0] += (L["comp"] == L["size"])
        stat[nm][1] += 1
        p = PAD(p + L["size"])
    off = p
    frames += 1
print("   frames walked:", frames)
for nm, (ok, n) in stat.items():
    if n:
        print("   %-11s comp==size %d/%d  %s" % (nm, ok, n, "LAYOUT CONFIRMED" if ok == n else "MISMATCH"))

print()
print("=" * 74)
print("S2/S3  decode frame 0 correctly and run the subset test")
name = u"u_arc_archer_idlea_x1.sld"
main = LAY.get("main")
pc = LAY.get("playercolor")
print("   main   rect=%s ncmd=%d draws=%d size=%d" % (main["rect"], main["ncmd"], main["draws"], main["size"]))
if pc:
    print("   playercolor ncmd=%d draws=%d size=%d fmt=0x%04x" % (pc["ncmd"], pc["draws"], pc["size"], pc["fmt"]))

im_main = decode(b, main, False)
im_pc = decode(b, pc, True)
print("   main image %s ; pc image %s" % (im_main.size, im_pc.size))

# map pc pixels onto the main rect grid
x1, y1, x2, y2 = main["rect"]
w, h = x2 - x1, y2 - y1
opaque = set()
for yy in range(im_main.size[1]):
    for xx in range(im_main.size[0]):
        if im_main.getpixel((xx, yy))[3] > 0:
            opaque.add((xx, yy))
# pc was decoded on its own g*g grid; align by cropping/scaling to the main rect
pc_small = im_pc.crop((0, 0, w, h)) if im_pc.size[0] >= w else im_pc
nz = [(xx, yy) for yy in range(pc_small.size[1]) for xx in range(pc_small.size[0])
      if pc_small.getpixel((xx, yy))[0] > 0]
inside = sum(1 for p in nz if p in opaque)
print("   pc nonzero px=%d ; of those inside main-opaque=%d (%.1f%%)"
      % (len(nz), inside, 100.0 * inside / max(1, len(nz))))
print("   main opaque px=%d" % len(opaque))
vals = [pc_small.getpixel(p)[0] for p in nz]
if vals:
    print("   pc gray range min=%d max=%d distinct=%d" % (min(vals), max(vals), len(set(vals))))

# tint main by mask
tint = Image.new("RGBA", im_main.size, (0, 0, 0, 0))
tp = tint.load()
for yy in range(im_main.size[1]):
    for xx in range(im_main.size[0]):
        r, g, bl, a = im_main.getpixel((xx, yy))
        if a == 0:
            continue
        m = pc_small.getpixel((xx, yy))[0] if (xx < pc_small.size[0] and yy < pc_small.size[1]) else 0
        f = m / 255.0
        tp[xx, yy] = (int(r * (1 - f) + 255 * f), int(g * (1 - f)), int(bl * (1 - f)), a)
sheet = Image.new("RGBA", (im_main.size[0] * 3 + 20, im_main.size[1]), (40, 40, 40, 255))
sheet.alpha_composite(im_main, (0, 0))
sheet.alpha_composite(im_pc.crop((0, 0, im_main.size[0], im_main.size[1])), (im_main.size[0] + 10, 0))
sheet.alpha_composite(tint, (im_main.size[0] * 2 + 20, 0))
sheet = sheet.resize((sheet.size[0] * 4, sheet.size[1] * 4), Image.NEAREST)
sheet.save(os.path.join(OUT, "archer_layers_corrected.png"))
print("   wrote archer_layers_corrected.png (main | pc mask | main tinted red)")

print()
print("=" * 74)
print("S4  repeat subset test for several units/frames")
for fn in (u"u_inf_militia_idlea_x1.sld", u"u_cav_knight_idlea_x1.sld", u"u_monk_west_idlea_x1.sld"):
    bb = open(os.path.join(GP, fn), "rb").read()
    o = 16
    got = {}
    for _ in range(2):
        cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", bb, o)
        p = o + 12
        for bit, nm in BITS:
            if not (ft & (1 << bit)):
                continue
            L = read_layer(bb, p, nm)
            got.setdefault(nm, L)
            p = PAD(p + L["size"])
        o = p
    m, q = got.get("main"), got.get("playercolor")
    if not (m and q):
        print("   %-30s main/pc missing (%s)" % (fn, list(got)))
        continue
    imM = decode(bb, m, False)
    imQ = decode(bb, q, True)
    x1, y1, x2, y2 = m["rect"]
    w, h = x2 - x1, y2 - y1
    op = set((xx, yy) for yy in range(imM.size[1]) for xx in range(imM.size[0])
             if imM.getpixel((xx, yy))[3] > 0)
    qs = imQ.crop((0, 0, w, h))
    nz = [(xx, yy) for yy in range(qs.size[1]) for xx in range(qs.size[0])
          if qs.getpixel((xx, yy))[0] > 0]
    ins = sum(1 for p2 in nz if p2 in op)
    print("   %-30s main_rect=%s main_opaque=%-5d pc_nz=%-5d inside=%-5d (%.1f%%) comp==size main=%s pc=%s"
          % (fn, m["rect"], len(op), len(nz), ins, 100.0 * ins / max(1, len(nz)),
             m["comp"] == m["size"], q["comp"] == q["size"]))
    sh = Image.new("RGBA", (imM.size[0] * 3 + 20, imM.size[1]), (40, 40, 40, 255))
    sh.alpha_composite(imM, (0, 0))
    sh.alpha_composite(imQ.crop((0, 0, imM.size[0], imM.size[1])), (imM.size[0] + 10, 0))
    sh.alpha_composite(imM, (imM.size[0] * 2 + 20, 0))
    sh = sh.resize((sh.size[0] * 4, sh.size[1] * 4), Image.NEAREST)
    sh.save(os.path.join(OUT, "layers_" + fn.split(".")[0] + ".png"))
