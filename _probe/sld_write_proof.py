# -*- coding: utf-8 -*-
"""Prove the SLD writer produces a *valid, editable* file:
  1. read u_arc_archer_idlea_x1.sld
  2. edit the BC1 endpoints of the main layer (recolour the tunic)
  3. serialize to a NEW file
  4. re-parse it with the UNMODIFIED reader (must walk to exact EOF,
     correct frame count, all layer size invariants hold)
  5. render both side by side so the change is visible

This is the sprite-mod capability end to end (minus launching the game).
"""
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


def recolour_main(s, target=(60, 90, 210), thresh=70):
    """Rewrite BC1 endpoint 0 of any block whose decoded colour is close to a
    saturated red (the player-coloured tunic) -- a crude but honest edit."""
    for fr in s.frames:
        m = fr.layers.get("main")
        if m is None:
            continue
        ncmd = struct.unpack_from("<H", m.data, 10)[0]
        base = 12 + 2 * ncmd
        blob = bytearray(m.data)
        n = (m.size - base) // 8
        hits = 0
        for i in range(n):
            o = base + 8 * i
            c0 = blob[o] | blob[o + 1] << 8
            c1 = blob[o + 2] | blob[o + 3] << 8
            r, g, b = _rgb565(c0)
            # red-ish and bright enough to be the tunic
            if r > 90 and r - g > 40 and r - b > 30:
                blob[o] = rgb565(*target) & 0xFF
                blob[o + 1] = (rgb565(*target) >> 8) & 0xFF
                hits += 1
        m.data = bytes(blob)
    return hits


def do(name, fi):
    src = os.path.join(GP, name)
    s = read_sld(src)
    hits = recolour_main(s)
    dst = os.path.join(WORK, "mod_" + name)
    with open(dst, "wb") as f:
        f.write(serialize_sld(s))
    print("%s: %d BC1 endpoints recoloured -> %d bytes (orig %d), hits=%d" %
          (name, hits, os.path.getsize(dst), os.path.getsize(src), hits))

    # re-parse with the unmodified reader
    s2 = read_sld(dst)
    assert len(s2.frames) == s.num_frames, "frame count changed"
    checks = 0
    for fr in s2.frames:
        m = fr.layers.get("main")
        if m is None:
            continue
        rect, fmt, n, cmds = parse_rect_layer(m)
        span = sum(b for _, b in cmds)
        assert m.size == 16 + 2 * n + 8 * span, "main size invariant broken"
        checks += 1
        if "playercolor" in fr.layers:
            pc = fr.layers["playercolor"]
            pfmt, pn, pcmds = parse_mask_layer(pc)
            assert pc.size == 8 + 2 * pn + 8 * sum(b for _, b in pcmds)
    print("   re-parsed OK: %d frames, %d main layers intact, walk exact EOF" %
          (len(s2.frames), checks))

    # render side by side
    def render(sld, idx):
        fr = sld.frames[idx]
        w, h = fr.canvas_w, fr.canvas_h
        cv = bytearray(w * h * 4)
        m = fr.layers["main"]
        rect, fmt, n, cmds = parse_rect_layer(m)
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        plane, PW, PH = decode_bc1_plane(rect_blocks(m, n), bw, bh, cmds)
        pc_plane = None
        if "playercolor" in fr.layers:
            pcl = fr.layers["playercolor"]
            pfmt, pn, pcmds = parse_mask_layer(pcl)
            pc_plane = decode_bc4_plane(mask_blocks(pcl, pn), bw, bh, pcmds)
        for gy in range(PH):
            for gx in range(PW):
                sx, sy = x1 + gx, y1 + gy
                if not (0 <= sx < w and 0 <= sy < h):
                    continue
                o = (sy * w + sx) * 4
                r, g, b, a = plane[(gy * PW + gx) * 4:(gy * PW + gx) * 4 + 4]
                if a == 0:
                    continue
                cv[o:o + 4] = bytes((r, g, b, a))
        im = Image.frombytes("RGBA", (w, h), bytes(cv))
        box = im.getbbox()
        if box:
            im = im.crop(box)
        return im

    a = render(s, fi)
    b = render(s2, fi)
    sc = 3
    a = a.resize((a.width * sc, a.height * sc), Image.NEAREST)
    b = b.resize((b.width * sc, b.height * sc), Image.NEAREST)
    sheet = Image.new("RGBA", (a.width + b.width + 24,
                               max(a.height, b.height) + 34), (18, 18, 22, 255))
    d = ImageDraw.Draw(sheet)
    d.text((6, 4), "ORIGINAL  %s f%d" % (name, fi), fill=(235, 235, 235))
    d.text((a.width + 18, 4), "AFTER sldwrite.py edit (tunic recoloured)",
           fill=(160, 220, 160))
    sheet.alpha_composite(a, (6, 24))
    sheet.alpha_composite(b, (a.width + 18, 24))
    p = os.path.join(OUT, "sld_write_proof.png")
    sheet.convert("RGB").save(p)
    print("   ->", p, sheet.size)


for nm in ("u_arc_archer_idlea_x1.sld", "u_inf_militia_idlea_x1.sld"):
    if os.path.exists(os.path.join(GP, nm)):
        do(nm, 0)
        break
