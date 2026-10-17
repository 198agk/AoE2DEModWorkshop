# -*- coding: utf-8 -*-
"""Verify the SLD writer edit is a REAL change, and render it legibly.

Checks:
  1. original vs written file: how many bytes differ, and are they all inside
     main-layer BC1 block data (i.e. no structural drift)?
  2. re-parse the written file with the UNMODIFIED reader and assert every
     layer size invariant + exact EOF + frame count.
  3. big side-by-side render of the recoloured frame.
"""
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import (read_sld, parse_rect_layer, parse_mask_layer, grid_of,
                    rect_blocks, mask_blocks, decode_bc1_plane,
                    decode_bc4_plane, _rgb565)
from sldwrite import serialize_sld
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_shots\sld_render"
WORK = r"D:\Software\DeepSeek Harness\工作区2\_probe\sld_out"
os.makedirs(OUT, exist_ok=True)
os.makedirs(WORK, exist_ok=True)


def rgb565(r, g, b):
    return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)


def parse_main_geometry(d, size):
    """Given raw main-layer payload `d` (size-4 bytes), return geometry."""
    rect = struct.unpack_from("<4H", d, 0)
    fmt, ncmd = struct.unpack_from("<2H", d, 8)
    cmds = [struct.unpack_from("<2B", d, 12 + 2 * i) for i in range(ncmd)]
    span = sum(b for a, b in cmds)
    assert size == 16 + 2 * ncmd + 8 * span, (size, ncmd, span)
    return rect, fmt, ncmd, cmds


def main():
    name = "u_arc_archer_idlea_x1.sld"
    src = os.path.join(GP, name)
    s = read_sld(src)
    orig = s.data

    # ---- edit: recolour the blue tunic to green ----
    fr0 = s.frames[0]
    m = fr0.layers["main"]
    rect, fmt, ncmd, cmds = parse_main_geometry(m.data, m.size)
    base = 12 + 2 * ncmd
    blob = bytearray(m.data)
    nblocks = (m.size - base) // 8
    edited_block_offsets = []
    for i in range(nblocks):
        o = base + 8 * i
        c0 = blob[o] | blob[o + 1] << 8
        c1 = blob[o + 2] | blob[o + 3] << 8
        # the archer's tunic is rgb(65,76,90) -- a dim blue.  Measure it,
        # don't guess it (v1 of this script used b>90 and matched 0 blocks).
        for cc in (c0, c1):
            r, g, b = _rgb565(cc)
            if b > 60 and b - r >= 18 and b - g >= 8:
                nb = rgb565(30, 200, 70)               # -> green
                blob[o] = nb & 0xFF
                blob[o + 1] = (nb >> 8) & 0xFF
                edited_block_offsets.append(m.off + 4 + o)
                break
    m.data = bytes(blob)
    dst = os.path.join(WORK, "edit_" + name)
    out = serialize_sld(s)
    with open(dst, "wb") as fh:
        fh.write(out)

    print("=== file identity ===")
    print("  original : %d B sha256 %s" % (len(orig),
          hashlib.sha256(orig).hexdigest()[:32]))
    print("  written  : %d B sha256 %s" % (len(out),
          hashlib.sha256(out).hexdigest()[:32]))
    print("  size delta: %d" % (len(out) - len(orig)))

    # ---- where do the bytes differ? ----
    diffs = [i for i in range(min(len(orig), len(out))) if orig[i] != out[i]]
    print("  differing byte positions: %d" % len(diffs))
    print("  first/last diff offset  : %s / %s"
          % (hex(diffs[0]) if diffs else "-", hex(diffs[-1]) if diffs else "-"))
    expected = set()
    for o in edited_block_offsets:
        expected.update(range(o, o + 2))
    print("  edited BC1 endpoint offsets: %s" % [hex(o) for o in
                                                edited_block_offsets])
    print("  all diffs inside edited endpoints: %s"
          % (set(diffs) == expected))
    if set(diffs) != expected:
        extra = sorted(set(diffs) - expected)[:12]
        print("  unexpected diff offsets: %s" % [hex(x) for x in extra])

    # ---- re-parse with the UNMODIFIED reader ----
    s2 = read_sld(dst)
    assert len(s2.frames) == s.num_frames
    assert s2.frame_offset == s.frame_offset
    nmain = npc = ndmg = 0
    for fr in s2.frames:
        L = fr.layers
        if "main" in L:
            r, f2, n2, c2 = parse_rect_layer(L["main"])
            assert L["main"].size == 16 + 2 * n2 + 8 * sum(b for a, b in c2)
            nmain += 1
        if "playercolor" in L:
            f2, n2, c2 = parse_mask_layer(L["playercolor"])
            assert L["playercolor"].size == 8 + 2 * n2 + 8 * sum(b for a, b in c2)
            npc += 1
    print()
    print("=== re-parse with UNMODIFIED reader ===")
    print("  frames: %d (== %d)  frame_offset %d"
          % (len(s2.frames), s.num_frames, s2.frame_offset))
    print("  main layers verified      : %d" % nmain)
    print("  playercolor layers verified: %d" % npc)
    print("  walked to exact EOF, all size invariants hold")

    # ---- render big ----
    def render(sld, idx):
        fr = sld.frames[idx]
        w, h = fr.canvas_w, fr.canvas_h
        m = fr.layers["main"]
        rect, f, n, c = parse_rect_layer(m)
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        plane, PW, PH = decode_bc1_plane(rect_blocks(m, n), bw, bh, c)
        cv = bytearray(w * h * 4)
        for gy in range(PH):
            for gx in range(PW):
                sx, sy = x1 + gx, y1 + gy
                if 0 <= sx < w and 0 <= sy < h:
                    o = (sy * w + sx) * 4
                    px = plane[(gy * PW + gx) * 4:(gy * PW + gx) * 4 + 4]
                    if px[3]:
                        cv[o:o + 4] = bytes(px)
        im = Image.frombytes("RGBA", (w, h), bytes(cv))
        bx = im.getbbox()
        return im.crop(bx) if bx else im

    a, b = render(s, 0), render(s2, 0)
    sc = 5
    a = a.resize((a.width * sc, a.height * sc), Image.NEAREST)
    b = b.resize((b.width * sc, b.height * sc), Image.NEAREST)
    sheet = Image.new("RGBA", (a.width + b.width + 30,
                               max(a.height, b.height) + 40), (18, 18, 22, 255))
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), "ORIGINAL  %s f0" % name, fill=(235, 235, 235))
    d.text((a.width + 24, 6), "RE-SERIALIZED after BC1 edit (tunic blue->green)",
           fill=(140, 235, 140))
    sheet.alpha_composite(a, (8, 28))
    sheet.alpha_composite(b, (a.width + 24, 28))
    p = os.path.join(OUT, "sld_write_proof_BIG.png")
    sheet.convert("RGB").save(p)
    print()
    print("  -> %s %s" % (p, sheet.size))


if __name__ == "__main__":
    main()
