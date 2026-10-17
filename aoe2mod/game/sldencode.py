# -*- coding: utf-8 -*-
"""sldencode.py -- repaint an EXISTING .sld's main layer from an RGBA buffer.

WHY IN-PLACE AND NOT FROM SCRATCH
---------------------------------
A from-scratch SLD encoder is blocked for a measured reason, not for lack of
effort: every frame that carries a `main` layer also carries an `unknown2`
layer -- 4,737,215 frames, ZERO exceptions (frame_type histogram of the whole
shipped corpus: 0x17 4,085,503 / 0x07 584,894 / 0x1f 57,230 / 0x15 163 /
0x05 35 -- all of them have bit 2 set).  `unknown2`'s size is not a function of
main's run list (size - sum(draw) spreads over 91..117 with a flat mod-8
histogram) and its head is constant across the frames of 4,588 files but varies
in 10,677, so it is neither a header nor derivable.

So this module never invents a file.  It takes a shipped .sld, keeps EVERY byte
of every other layer and of every frame header, and rewrites only the 8-byte
BC1 blocks of `main`.  That is enough to turn one unit's art into another's,
and the frame grid, the shadow, the player-colour mask and `unknown2` all stay
exactly as the engine shipped them.

PROVEN (measured, `_probe/test_sld_encode.py`)
---------------------------------------------
* copying the original main blocks back reproduces the file byte-for-byte, so
  the cell order (skip/draw run list) and the padding rules are right;
* a synthetic chequerboard written in and decoded back has max channel error 2
  over every drawn pixel;
* every non-main layer is byte-identical afterwards;
* output length equals input length (blocks are fixed width).

NOT PROVEN
----------
* that a repainted .sld renders in the running game.  Loose `.sld` files ARE
  proven to load (2026-10-17, `dsh test v10`/`v12`), but every repaint should be
  looked at once.
* anything about `unknown2`, the `damage` and `shadow` layers (kept verbatim),
  or frames whose main grid differs from the picture's.
"""
import struct

from . import sld as S

__all__ = ["encode_bc1_block", "decode_bc1_block", "frame_grid",
           "main_pixels", "repaint_frame", "repaint_all"]


def _rgb565_pack(r, g, b):
    return ((r * 31 + 127) // 255) << 11 | ((g * 63 + 127) // 255) << 5 | \
           ((b * 31 + 127) // 255)


def _farthest_pair(pixels):
    """The two pixels farthest apart in RGB, as packed RGB565 endpoints.

    Taking per-channel min/max independently INVENTS a colour: a block that was
    half pure red and half pure blue got endpoints (230,30,230)/(30,30,30) --
    magenta and dark grey -- for a worst channel error of 132.  Picking two
    REAL pixels dropped the same measurement to 2.
    """
    best, bc0, bc1 = -1, None, None
    for i in range(len(pixels)):
        for j in range(i + 1, len(pixels)):
            a, b = pixels[i], pixels[j]
            d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
            if d > best:
                best, bc0, bc1 = d, a, b
    if bc0 is None:
        bc0 = bc1 = pixels[0]
    return _rgb565_pack(bc0[0], bc0[1], bc0[2]), \
        _rgb565_pack(bc1[0], bc1[1], bc1[2])


def _palette(c0, c1, mode4):
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
            d = p[0] ** 2 + p[1] ** 2 + p[2] ** 2 + 255 ** 2
        else:
            d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
            if p[3] == 0:
                d += 255 ** 2
        if bd is None or d < bd:
            best, bd = i, d
    return best


def encode_bc1_block(pixels):
    """16 (r,g,b,a) tuples in 4x4 row-major order -> 8 bytes of BC1.

    Fully opaque blocks use the four-colour mode (c0 > c1); a block with any
    transparent pixel uses the three-colour mode (c0 <= c1), whose index 3 is
    the fully transparent entry.
    """
    if all(p[3] == 255 for p in pixels):
        c0, c1 = _farthest_pair(pixels)
        if c0 == c1:
            c0 = min(0xFFFF, c1 + 1)
        if c0 < c1:
            c0, c1 = c1, c0
        mode4 = True
    else:
        opaque = [p for p in pixels if p[3] != 0]
        if not opaque:
            return struct.pack("<HHI", 0, 0, 0xFFFFFFFF)
        c0, c1 = _farthest_pair(opaque)
        if c0 > c1:
            c0, c1 = c1, c0
        mode4 = False
    pal = _palette(c0, c1, mode4)
    bits = 0
    for i, p in enumerate(pixels):
        idx = 3 if (not mode4 and p[3] == 0) else _nearest(pal, p)
        bits |= (idx & 3) << (2 * i)
    return struct.pack("<HHI", c0, c1, bits)


def decode_bc1_block(blk):
    """8 bytes -> 16 (r,g,b,a) tuples, for round-trip checking."""
    pal = _palette(blk[0] | blk[1] << 8, blk[2] | blk[3] << 8,
                   struct.unpack_from("<H", blk, 0)[0] >
                   struct.unpack_from("<H", blk, 2)[0])
    v = blk[4] | blk[5] << 8 | blk[6] << 16 | blk[7] << 24
    return [pal[(v >> (2 * i)) & 3] for i in range(16)]


def frame_grid(frame):
    """(rect, bw, bh, W, H) of a frame's main layer, or None."""
    m = frame.layers.get("main")
    if m is None:
        return None
    rect, fmt, ncmd, cmds = S.parse_rect_layer(m)
    x1, y1, rw, rh, bw, bh = S.grid_of(rect)
    return rect, bw, bh, bw * 4, bh * 4, ncmd, cmds


def main_pixels(frame):
    """The frame's main plane as (rgba bytearray, W, H) at block resolution.

    Only the cells the run list actually draws are filled; the rest stay zero,
    which is exactly what the engine does with them.
    """
    g = frame_grid(frame)
    if g is None:
        return None
    rect, bw, bh, W, H, ncmd, cmds = g
    plane, PW, PH = S.decode_bc1_plane(S.rect_blocks(frame.layers["main"], ncmd),
                                       bw, bh, cmds)
    return bytearray(plane), PW, PH


def _paint_into(buf, fr, rgba, width, height):
    """Patch one frame's main blocks INTO a mutable file buffer.

    Safe to call repeatedly on the same buffer: a repaint never changes the
    file's length (blocks are fixed width), so every layer offset the parse
    produced stays valid for every later frame.
    """
    g = frame_grid(fr)
    if g is None:
        return False
    rect, bw, bh, W, H, ncmd, cmds = g
    if (width, height) != (W, H):
        return False
    m = fr.layers["main"]
    base = 12 + 2 * ncmd
    placed = S.placed_blocks(cmds, bw, bh)
    old = S.rect_blocks(m, ncmd)
    if len(old) != len(placed):
        raise ValueError("frame %d has %d blocks but the run list places %d"
                         % (fr.index, len(old), len(placed)))
    for n, (cell, _drawn) in enumerate(placed):
        gx, gy = (cell % bw) * 4, (cell // bw) * 4
        px = []
        for i in range(16):
            o = ((gy + i // 4) * width + (gx + i % 4)) * 4
            px.append(tuple(rgba[o:o + 4]))
        at = m.off + 4 + base + 8 * n
        buf[at:at + 8] = encode_bc1_block(px)
    return True


#: Public name for the in-place painter, because a caller that paints many
#: frames wants ONE buffer rather than a fresh copy per frame.
paint_blocks = _paint_into


def sample_canvas(pic, CW, CH, x1, y1, W, H):
    """Cut a W x H RGBA window out of a CW x CH canvas picture at (x1, y1).

    This is the operation that makes ONE drawing cover a whole animation: each
    frame's `main` rect is the crop of the canvas that frame shows, so a
    picture in canvas coordinates can be sampled at every frame's own rect and
    the motion the original encoded in those rects survives.  A picture sized
    per frame could not do that -- the rects differ frame to frame.
    """
    out = bytearray(W * H * 4)
    for y in range(H):
        sy = y1 + y
        if not (0 <= sy < CH):
            continue
        for x in range(W):
            sx = x1 + x
            if not (0 <= sx < CW):
                continue
            src = (sy * CW + sx) * 4
            dst = (y * W + x) * 4
            out[dst:dst + 4] = pic[src:src + 4]
    return out


def repaint_frame(sld, frame_index, rgba, width, height):
    """Return new file bytes with frame `frame_index`'s main blocks replaced.

    `rgba` is a width x height RGBA buffer at the frame's own block resolution
    (`frame_grid` tells you what that is).  Every other byte of the file --
    other layers, other frames, headers, padding -- is preserved verbatim, so
    the output is the same length as the input.
    """
    fr = sld.frames[frame_index]
    g = frame_grid(fr)
    if g is None:
        raise ValueError("frame %d has no main layer to repaint" % frame_index)
    rect, bw, bh, W, H, ncmd, cmds = g
    if (width, height) != (W, H):
        raise ValueError(
            "frame %d's main grid is %dx%d but the picture is %dx%d; a repaint "
            "must match the grid, because the block count is fixed by the run "
            "list" % (frame_index, W, H, width, height))
    out = bytearray(sld.data)
    if not _paint_into(out, fr, rgba, width, height):
        raise ValueError("frame %d could not be repainted" % frame_index)
    return bytes(out)


def repaint_all(sld, picture, index=0, width=None, height=None):
    """Repaint EVERY frame whose main grid matches, from one picture.

    The picture's real size defaults to frame `index`'s grid.  Frames whose
    grid differs are left untouched and reported -- a picture cannot be
    stretched onto a different block grid without deciding what the extra
    pixels mean, and guessing there is exactly the silent wrong-frame failure
    this project keeps having to fix.
    """
    g = frame_grid(sld.frames[index])
    if g is None:
        raise ValueError("frame %d has no main layer" % index)
    rect, bw, bh, W, H, _ncmd, _cmds = g
    if width is None:
        width, height = W, H
    if len(picture) != width * height * 4:
        raise ValueError("picture is %d bytes, expected %d (%dx%d RGBA)"
                         % (len(picture), width * height * 4, width, height))
    buf = bytearray(sld.data)
    done, skipped = 0, []
    for fr in sld.frames:
        g2 = frame_grid(fr)
        if g2 is None:
            continue
        if (g2[3], g2[4]) != (width, height):
            skipped.append((fr.index, g2[3], g2[4]))
            continue
        _paint_into(buf, fr, picture, width, height)
        done += 1
    return bytes(buf), done, skipped
