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


def dense_runs(cells):
    """A skip/draw list that draws EVERY cell of a grid, in reading order.

    WHY A DENSE LIST AT ALL.  A shipped frame's run list is a mask: the villager
    idle frame 0 has 55 cells and draws 35 of them, because the cells its art
    never reaches are not stored.  Repainting IN PLACE could therefore only ever
    touch those 35 -- a picture drawn across the whole window came out with a
    chunk missing wherever the original art was empty, which is what the player
    saw as 「图像是缺损的」 on 2026-11-25.  A repaint has to be allowed to say "this
    cell is part of the picture now", and the only way to say it is a run list
    that mentions the cell.

    skip and draw are single bytes, so a grid of more than 255 cells needs more
    than one run; the runs are emitted back to back with no skip.
    """
    out, left = [], int(cells)
    while left > 0:
        n = 255 if left > 255 else left
        out.append((0, n))
        left -= n
    return out


def zero_mask(layer, bw, bh):
    """A dense, all-zero stand-in for a mask layer on main's own grid.

    WHY A MASK HAS TO GO WHEN THE PICTURE DOES.  playercolor and damage are
    BC4 planes whose run list is shaped like the OLD art: on the militia idle
    frame the playercolor mask lights up 156 pixels of a 24x48 grid, all of
    them where the shipped villager's cloak is.  Paint a player's own picture
    into the dense main layer and those 156 pixels still say "this bit is the
    cloak", so the picture comes back with blue splotches in the shape of the
    art it replaced -- measured on 2026-11-25, see _probe/_tmp/dense_tint.png.

    A mask that describes a silhouette cannot describe a different silhouette,
    so the honest value is zero everywhere: no team tint, no damage darkening.
    The layer itself stays (the frame type still claims it) and it still covers
    every cell, so the game reads the same grid it always did.

    An all-zero BC4 block is eight zero bytes: a0 == a1 == 0 puts index 0 on
    value 0 for all sixteen pixels.
    """
    # The patch bit goes for the same reason main's does: what follows is a
    # whole layer covering every cell, not a delta over the previous frame.
    fmt = struct.unpack_from("<H", layer.data, 0)[0] & 0x7F
    runs = dense_runs(bw * bh)
    payload = struct.pack("<2H", fmt, len(runs))
    for run in runs:
        payload += bytes(run)
    payload += bytes(8 * (bw * bh))
    return payload

def rebuild_dense(sld, paint, skip=None, keep_masks=None):
    """Rebuild a whole .sld with a FULL-CELL main layer per frame.

    `paint(frame, W, H)` returns the RGBA window for that frame (W, H are the
    frame's own block-grid size).

    `skip` names frames to copy through byte for byte, mask layers included.
    Painting ONE DIRECTION of a file must not disturb the other fifteen: their
    art is still the game's, their masks still describe it, and rewriting them
    densely would strip a tint nobody asked to remove.  `keep_masks` names the
    frames whose mask layers stay as they are even though main is rewritten --
    an untouched frame of the painted direction keeps the game's own pixels, so
    it keeps the game's own silhouette mask with them.  Shadow and the opaque `unknown2` block are
    copied verbatim, pad bytes included.  `playercolor` and `damage` are the
    one exception and they are rewritten as zero masks -- they describe the
    OLD silhouette, and keeping them tints the new picture (see `zero_mask`).
    So the only claims this makes about the format are the ones it was written
    to make: main is a rect, a run list and BC1 blocks; a mask is a run list
    and BC4 blocks on main's grid.

    THE FILE LENGTH CHANGES, on purpose.  A dense main layer is bigger than a
    sparse one (villager idle x1: 55 cells vs 35 drawn, +160 bytes a frame).
    Frames are sequential records and each carries its own sizes, so a longer
    file re-parses identically; `verify_repaint` below is what checks that.
    """
    raw = sld.data
    out = bytearray(struct.pack("<4s 2H 2H H", b"SLDX", sld.version,
                                len(sld.frames), sld.u1, sld.frame_offset,
                                sld.magic))
    # The 0- or 2-byte gap between the 14-byte header and frame 0 is preserved
    # verbatim; `frame_offset` is authoritative (14 for 431 of 15,484 files).
    out += raw[len(out):sld.frame_offset]
    for fr in sld.frames:
        out += struct.pack("<2H 2h 2B H", fr.canvas_w, fr.canvas_h,
                           fr.centre_x, fr.centre_y,
                           fr.frame_type, fr.unknown, fr.index)
        g = frame_grid(fr)
        for bit, nm in S.BITS:
            if not (fr.frame_type & (1 << bit)):
                continue
            l = fr.layers[nm]
            if skip is not None and fr.index in skip:
                payload = l.data
                size = 4 + len(payload)
                if size != l.size:
                    raise ValueError("layer %s of frame %d says %d bytes, holds %d"
                                     % (nm, fr.index, l.size, size))
                out += struct.pack("<I", size) + payload
                pad = S.ceil4(size) - size
                if pad:
                    out += raw[l.off + size:l.off + size + pad]
                continue
            if g is not None and nm == "main":
                rect, bw, bh, W, H, ncmd, cmds = g
                # CLEAR THE PATCH BIT.  fmt 0x180 means "this layer carries a
                # run list", and on a frame that is not the first of a pose
                # that run list is a PATCH: only the cells whose colour changed.
                # What is written here is a whole picture -- a dense run list and
                # a block for every cell -- so the flag has to say so, or the
                # engine overlays a complete picture onto the previous one.
                fmt = S.parse_rect_layer(l)[1] & 0x7F
                rgba = paint(fr, W, H)
                blocks = bytearray()
                for cy in range(bh):
                    for cx in range(bw):
                        px = []
                        for i in range(16):
                            o = ((cy * 4 + i // 4) * W + cx * 4 + i % 4) * 4
                            px.append(tuple(rgba[o:o + 4]))
                        blocks += encode_bc1_block(px)
                runs = dense_runs(bw * bh)
                payload = struct.pack("<4H 2H", rect[0], rect[1], rect[2],
                                      rect[3], fmt, len(runs))
                for run in runs:
                    payload += bytes(run)
                payload += bytes(blocks)
                size = 4 + len(payload)
                out += struct.pack("<I", size) + payload
                out += bytes(S.ceil4(size) - size)
                continue
            if g is not None and nm in ("playercolor", "damage") and not (
                    keep_masks is not None and fr.index in keep_masks):
                # SHAPED LIKE THE OLD SILHOUETTE, SO IT HAS TO GO -- see
                # zero_mask: keeping it tints the new picture where the old
                # art used to be.
                payload = zero_mask(l, g[1], g[2])
                size = 4 + len(payload)
                out += struct.pack("<I", size) + payload
                pad = S.ceil4(size) - size
                if pad:
                    out += bytes(pad)
                continue
            payload = l.data
            size = 4 + len(payload)
            if size != l.size:
                raise ValueError("layer %s of frame %d says %d bytes, holds %d"
                                 % (nm, fr.index, l.size, size))
            out += struct.pack("<I", size) + payload
            pad = S.ceil4(size) - size
            if pad:
                out += raw[l.off + size:l.off + size + pad]
    return bytes(out)


def _mask_is_cleared(layer, bw, bh):
    """True when `layer` is a mask that draws every cell and says zero."""
    fmt, ncmd, cmds = S.parse_mask_layer(layer)
    cells = sum(draw for _skip, draw in cmds)
    if cells != bw * bh:
        return False
    blocks = S.mask_blocks(layer, ncmd)
    return len(blocks) == bw * bh and not any(any(blk) for blk in blocks)


def verify_repaint(old, new, touched=None):
    """Raise unless `new` is `old` with ONLY the main blocks redrawn.

    Returns the list of frames whose main layer grew.  This is the check that
    replaced "the length must not change": a dense main layer necessarily makes
    the file longer, so the honest invariant is about STRUCTURE -- same frames,
    same canvases, same rects, and every other layer byte-identical.
    """
    if len(new.frames) != len(old.frames):
        raise ValueError("frame count changed: %d -> %d"
                         % (len(old.frames), len(new.frames)))
    grew = []
    for a, b in zip(old.frames, new.frames):
        untouched = touched is not None and a.index not in touched
        if untouched:
            # A FRAME NOBODY PAINTED MUST COME BACK AS ITSELF.  One direction of
            # a file can be repainted while the other fifteen still carry the
            # game's own art, and that art includes patch frames whose fmt bit
            # and whose masks are only correct for the pixels they shipped with.
            for nm in a.layers:
                if a.layers[nm].data != b.layers[nm].data:
                    raise ValueError("frame %d layer %s was disturbed"
                                     % (a.index, nm))
            continue
        if (a.canvas_w, a.canvas_h, a.frame_type, a.index) != \
                (b.canvas_w, b.canvas_h, b.frame_type, b.index):
            raise ValueError("frame %d header changed" % a.index)
        if set(a.layers) != set(b.layers):
            raise ValueError("frame %d layer set changed" % a.index)
        ga, gb = frame_grid(a), frame_grid(b)
        if ga is not None:
            if gb is None or ga[0] != gb[0] or (ga[1], ga[2]) != (gb[1], gb[2]):
                raise ValueError("frame %d main rect or grid changed" % a.index)
            # EVERY REPAINTED FRAME MUST READ AS A WHOLE PICTURE.  A shipped
            # patch frame (fmt 0x180) carries only the cells that changed; if a
            # repaint left that bit set on a dense layer, the engine would
            # treat a complete picture as a delta.
            fmt = S.parse_rect_layer(b.layers["main"])[1]
            if fmt & 0x80:
                raise ValueError("frame %d still reads as a patch (fmt 0x%03X)"
                                 % (a.index, fmt))
            if b.layers["main"].size > a.layers["main"].size:
                grew.append(a.index)
        for nm in a.layers:
            if nm == "main":
                continue
            if a.layers[nm].data == b.layers[nm].data:
                continue
            # A MASK MAY BE CLEARED, AND ONLY CLEARED.  It is allowed to differ
            # from the original because a silhouette mask cannot describe a
            # picture it was not drawn for (see zero_mask); what must hold is
            # that the new one is all zero and covers the frame's whole grid.
            if nm in ("playercolor", "damage") and _mask_is_cleared(
                    b.layers[nm], ga[1], ga[2]):
                continue
            raise ValueError("frame %d layer %s was disturbed"
                             % (a.index, nm))
    return grew


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
