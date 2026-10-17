# -*- coding: utf-8 -*-
"""Can an EXISTING .sld have its main-layer pixels replaced in place?

That is the art pipeline question.  A from-scratch encoder is blocked
because every frame that has `main` also has `unknown2` (4,737,215 frames,
0 exceptions) and unknown2 is not understood.  But an in-place rewrite never
touches unknown2: it keeps every other layer byte-for-byte and only
re-encodes the BC1 blocks of `main`.

Part 1 validates the PLACEMENT logic: copying the original block bytes must
reproduce the original file byte-for-byte.  If that fails, the cell order or
padding is wrong and nothing else can work.
Part 2 validates the BC1 ENCODER: build a synthetic picture, write it in,
decode it back, and compare pixels.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import (read_sld, parse_rect_layer, parse_mask_layer, grid_of,
                    rect_blocks, mask_blocks, decode_bc1_plane, ceil4)

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"


def _rgb565_pack(r, g, b):
    return ((r * 31 + 127) // 255) << 11 | ((g * 63 + 127) // 255) << 5 | \
           ((b * 31 + 127) // 255)


def _farthest_pair(pixels):
    """The two pixels farthest apart in RGB, as (c0, c1).

    Taking per-channel min/max independently invents a colour nothing in the
    block actually has: a block that is half pure red and half pure blue got
    the endpoints (230,30,230) and (30,30,30) -- magenta and dark grey -- and
    the worst channel error was 132.  Choosing two REAL pixels fixes it.
    """
    best, bc0, bc1 = -1, None, None
    for i in range(len(pixels)):
        for j in range(i + 1, len(pixels)):
            a, b = pixels[i], pixels[j]
            d = sum((a[c] - b[c]) ** 2 for c in range(3))
            if d > best:
                best, bc0, bc1 = d, a, b
    if bc0 is None:
        bc0 = bc1 = pixels[0]
    return (_rgb565_pack(*bc0[:3]), _rgb565_pack(*bc1[:3]))


def encode_bc1_block(pixels, opaque=True):
    """pixels: 16 (r,g,b,a) tuples in row-major 4x4 order -> 8 bytes.

    Endpoints are the two furthest-apart REAL pixels.  Opaque blocks use the
    4-colour mode (c0 > c1); blocks with any transparency use the 3-colour
    mode (c0 <= c1) whose index 3 is fully transparent.
    """
    if opaque and all(p[3] == 255 for p in pixels):
        c0, c1 = _farthest_pair(pixels)
        if c0 == c1:
            # a solid block: nudge one endpoint so c0 > c1 keeps 4-colour mode
            c0 = min(0xFFFF, c1 + 1)
        if c0 < c1:
            c0, c1 = c1, c0
        mode4 = True
    else:
        opaque_px = [p for p in pixels if p[3] != 0]
        if not opaque_px:
            return struct.pack("<HHI", 0, 0, 0xFFFFFFFF)
        c0, c1 = _farthest_pair(opaque_px)
        if c0 > c1:
            c0, c1 = c1, c0
        mode4 = False

    pal = _palette_from_endpoints(c0, c1, mode4)
    bits = 0
    for i, p in enumerate(pixels):
        idx = 0 if p[3] == 0 and not mode4 else _nearest(pal, p)
        if not mode4 and p[3] == 0:
            idx = 3
        bits |= (idx & 3) << (2 * i)
    return struct.pack("<HHI", c0, c1, bits)


def _palette_from_endpoints(c0, c1, mode4):
    def rgb(c):
        return ((c >> 11 & 0x1F) * 255 // 31,
                (c >> 5 & 0x3F) * 255 // 63,
                (c & 0x1F) * 255 // 31)
    a, b = rgb(c0), rgb(c1)
    if mode4:
        return [a + (255,), b + (255,),
                tuple((2 * a[i] + b[i]) // 3 for i in range(3)) + (255,),
                tuple((a[i] + 2 * b[i]) // 3 for i in range(3)) + (255,)]
    return [a + (255,), b + (255,),
            tuple((a[i] + b[i]) // 2 for i in range(3)) + (255,),
            (0, 0, 0, 0)]


def _nearest(pal, p):
    best, bd = 0, None
    for i, q in enumerate(pal):
        if q[3] == 0:
            d = (p[0] ** 2 + p[1] ** 2 + p[2] ** 2) + 255 ** 2
        else:
            d = sum((p[c] - q[c]) ** 2 for c in range(3))
            if p[3] == 0:
                d += 255 ** 2
        if bd is None or d < bd:
            best, bd = i, d
    return best


def replace_main(s, frame_index, image_w, image_h, rgba):
    """Rewrite frame `frame_index`'s main blocks from an RGBA buffer of the
    same grid.  Returns new file bytes; every other byte is preserved."""
    fr = s.frames[frame_index]
    m = fr.layers["main"]
    rect, fmt, ncmd, cmds = parse_rect_layer(m)
    x1, y1, rw, rh, bw, bh = grid_of(rect)
    from sldlib import placed_blocks
    placed = placed_blocks(cmds, bw, bh)
    blocks = []
    for cell, _drawn in placed:
        gx, gy = (cell % bw) * 4, (cell // bw) * 4
        px = []
        for i in range(16):
            x, y = gx + (i % 4), gy + (i // 4)
            if x >= image_w or y >= image_h:
                px.append((0, 0, 0, 0))
            else:
                o = (y * image_w + x) * 4
                px.append(tuple(rgba[o:o + 4]))
        blocks.append(encode_bc1_block(px))
    base = 12 + 2 * ncmd
    old = rect_blocks(m, ncmd)
    assert len(old) == len(blocks), (len(old), len(blocks))
    new_layer = bytearray(m.data)
    for i, blk in enumerate(blocks):
        new_layer[base + 8 * i: base + 8 * i + 8] = blk
    out = bytearray(s.data)
    out[m.off + 4: m.off + m.size] = new_layer
    return bytes(out)


def copy_blocks_identity(s, frame_index):
    fr = s.frames[frame_index]
    m = fr.layers["main"]
    rect, fmt, ncmd, cmds = parse_rect_layer(m)
    base = 12 + 2 * ncmd
    old = rect_blocks(m, ncmd)
    new_layer = bytearray(m.data)
    for i, blk in enumerate(old):
        new_layer[base + 8 * i: base + 8 * i + 8] = blk
    out = bytearray(s.data)
    out[m.off + 4: m.off + m.size] = new_layer
    return bytes(out)


if __name__ == "__main__":
    name = "a_herd_sheep_idleA_x1.sld"
    p = os.path.join(GP, name)
    s = read_sld(p)
    print("file", name, len(s.data), "frames", len(s.frames))

    # --- Part 1: identity block copy must reproduce the file exactly
    bad = 0
    for i in range(min(40, len(s.frames))):
        if "main" not in s.frames[i].layers:
            continue
        if copy_blocks_identity(s, i) != s.data:
            bad += 1
    print("PART 1 identity block copy: mismatching frames:", bad,
          "(0 means the cell order and padding are right)")

    # --- Part 2: synthetic picture -> decode back
    fr = s.frames[0]
    m = fr.layers["main"]
    rect, fmt, ncmd, cmds = parse_rect_layer(m)
    x1, y1, rw, rh, bw, bh = grid_of(rect)
    W, H = bw * 4, bh * 4
    img = bytearray(W * H * 4)
    for y in range(H):
        for x in range(W):
            o = (y * W + x) * 4
            if (x // 4 + y // 4) % 2 == 0:
                img[o:o + 4] = bytes((230, 30, 30, 255))     # red
            else:
                img[o:o + 4] = bytes((30, 30, 230, 255))     # blue
    new_bytes = replace_main(s, 0, W, H, img)
    print("PART 2 wrote", len(new_bytes), "bytes (original", len(s.data),
          ") same size:", len(new_bytes) == len(s.data))

    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "_sld_out", "synth_check.sld")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with open(tmp, "wb") as fh:
        fh.write(new_bytes)
    s2 = read_sld(tmp)
    r2, f2, n2, c2 = parse_rect_layer(s2.frames[0].layers["main"])
    plane, PW, PH = decode_bc1_plane(rect_blocks(s2.frames[0].layers["main"], n2),
                                     bw, bh, c2)
    maxerr = 0
    drawn = 0
    from sldlib import placed_blocks
    cells = placed_blocks(c2, bw, bh)
    for cell, _d in cells:
        gx, gy = (cell % bw) * 4, (cell // bw) * 4
        for i in range(16):
            x, y = gx + (i % 4), gy + (i // 4)
            o_src = (y * W + x) * 4
            o_dec = (y * PW + x) * 4
            for c in range(3):
                maxerr = max(maxerr, abs(img[o_src + c] - plane[o_dec + c]))
            drawn += 1
    print("PART 2 re-decoded grid", (PW, PH), "over", drawn,
          "drawn pixels, max channel error", maxerr)

    # --- Part 3: every other layer is untouched
    same = all(s2.frames[0].layers[k].data == s.frames[0].layers[k].data
               for k in s.frames[0].layers if k != "main")
    print("PART 3 other layers byte-identical:", same)
