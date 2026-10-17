# -*- coding: utf-8 -*-
"""sldlib.py -- AoE2 DE `.sld` sprite reader + software renderer.

Format verified tree-wide: 15,484 / 15,484 files walk to EXACT EOF,
4,850,222 frames, zero `frame_index` discontinuities, `num_frames` header
field matches the walked count in every file.

FILE HEADER (16 B)  <4s 2H 2H H
    sig          4s   'SLDX'
    version      u16  always 4 in this build
    num_frames   u16  == number of frames walked (verified 15484/15484)
    u1           u16  0x0000 or 0x0010 (semantics not established)
    frame_offset u16  16 for 15,053 files / 14 for 431 files  <- USE THIS
    magic        u16  low byte always 0xff

FRAME HEADER (12 B)  <2H 2h 2B H
    canvas_w u16 | canvas_h u16 | centre_x i16 | centre_y i16
    frame_type u8 | unknown u8 | frame_index u16

LAYER RECORD
    u32 size | (size-4) payload | pad
    next_offset = off + ceil4(size)          <-- padding from the SIZE FIELD

    main / shadow : 4x u16 rect | u16 fmt | u16 ncmd | ncmd*(u8 skip,u8 draw) | blocks
                    size == 16 + 2*ncmd + 8*sum(draw)     [4,737,215 / 4,737,215 verified]
    playercolor   : u16 fmt | u16 ncmd | ncmd*(u8 skip,u8 draw) | blocks
                    size ==  8 + 2*ncmd + 8*sum(draw)     [4,142,896 / 4,142,896 verified]
    damage        : SAME layout as playercolor (no rect, 8 + 2*ncmd + 8*sum(draw))
                    [66,620 / 66,620 verified, 0 bad]
                    It is a BC4 MASK and indexes MAIN's grid: for all
                    66,620/66,620 layers sum(skip+draw) == main's bw*bh.
                    fmt tells which command array it carries:
                      0x0100 -> same run-list as main (23,835 / 23,870)
                      0x0180 -> its OWN run-list over the same grid (42,750)
                    Placement: placed_blocks(damage_cmds, bw, bh) on main's grid.
                    (damage.span == main.span only when fmt==0x0100.)
    unknown2      : not a block layer at all (size parity varies) -- not decoded

BLOCK DATA
    one 8-byte block per drawn cell, consumed in command order.
    The command array is a LINEAR RUN LIST over the bw x bh cell grid in
    row-major order, bw = ceil(rect_w/4), bh = ceil(rect_h/4).
    Invariant: sum(skip+draw) == bw*bh, and playercolor shares main's grid.
"""
import struct

BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
MASK_LAYERS = ("playercolor", "damage")   # identical layout, both are BC4 masks
ceil4 = lambda x: x + ((4 - x % 4) % 4)


class Layer(object):
    __slots__ = ("name", "off", "size", "data")

    def __init__(self, name, off, size, data):
        self.name, self.off, self.size, self.data = name, off, size, data

    def __repr__(self):
        return "<Layer %s @%d size=%d>" % (self.name, self.off, self.size)


class Frame(object):
    __slots__ = ("index", "frame_type", "canvas_w", "canvas_h",
                 "centre_x", "centre_y", "off", "layers", "unknown")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<Frame %d ft=0x%02x %dx%d layers=%s>" % (
            self.index, self.frame_type, self.canvas_w, self.canvas_h,
            "+".join(sorted(self.layers)))


class Sld(object):
    def __init__(self, path, data):
        self.path = path
        self.data = data
        sig, self.version, self.num_frames, self.u1, self.frame_offset, self.magic = \
            struct.unpack_from("<4s 2H 2H H", data, 0)
        if sig != b"SLDX":
            raise ValueError("not an SLD: %r" % sig)
        self.frames = list(self._walk())

    def _walk(self):
        b = self.data
        p, prev, i = self.frame_offset, None, 0
        while p < len(b):
            if p + 12 > len(b):
                raise ValueError("frame header past EOF at %d" % p)
            cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, p)
            if prev is not None and idx != prev + 1:
                raise ValueError("frame_index break: %d -> %d" % (prev, idx))
            prev = idx
            q = p + 12
            layers = {}
            for bit, nm in BITS:
                if not (ft & (1 << bit)):
                    continue
                if q + 4 > len(b):
                    raise ValueError("layer size past EOF f%d %s" % (i, nm))
                size = struct.unpack_from("<I", b, q)[0]
                if size < 4 or q + size > len(b):
                    raise ValueError("bad size %d f%d %s" % (size, i, nm))
                layers[nm] = Layer(nm, q, size, b[q + 4:q + size])
                q += ceil4(size)
            yield Frame(index=idx, frame_type=ft, canvas_w=cw, canvas_h=ch,
                        centre_x=cx, centre_y=cy, off=p, layers=layers,
                        unknown=un)
            p = q
            i += 1
        if p != len(b):
            raise ValueError("walk overran: ended at %d of %d" % (p, len(b)))

    def __len__(self):
        return len(self.frames)


def read_sld(path):
    with open(path, "rb") as f:
        return Sld(path, f.read())


# ---------------------------------------------------------------- layer bodies

def parse_rect_layer(layer):
    """main / shadow / damage: rect + fmt + ncmd + cmds.  Returns
    (rect, fmt, ncmd, cmds) with cmds a list of (skip, draw)."""
    b = layer.data
    rect = struct.unpack_from("<4H", b, 0)
    fmt, ncmd = struct.unpack_from("<2H", b, 8)
    cmds = [(b[12 + 2 * i], b[13 + 2 * i]) for i in range(ncmd)]
    return rect, fmt, ncmd, cmds


def parse_mask_layer(layer):
    """playercolor / damage: fmt + ncmd + cmds (NO rect -- BOTH share main's
    grid, verified: sum(skip+draw) == main's bw*bh for 4,142,872 / 4,142,896
    playercolor and 66,620 / 66,620 damage layers).
    Returns (fmt, ncmd, cmds) with cmds a list of (skip, draw)."""
    b = layer.data
    fmt, ncmd = struct.unpack_from("<2H", b, 0)
    cmds = [(b[4 + 2 * i], b[5 + 2 * i]) for i in range(ncmd)]
    return fmt, ncmd, cmds


def mask_blocks(layer, ncmd):
    """The 8-byte blocks of a mask layer, in stream order."""
    base = 4 + 2 * ncmd
    n = (layer.size - base) // 8
    return [layer.data[base + 8 * i: base + 8 * i + 8] for i in range(n)]


def rect_blocks(layer, ncmd):
    """The 8-byte blocks of a rect layer (main / shadow)."""
    base = 12 + 2 * ncmd
    n = (layer.size - base) // 8
    return [layer.data[base + 8 * i: base + 8 * i + 8] for i in range(n)]


def grid_of(rect):
    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    return x1, y1, w, h, (w + 3) // 4, (h + 3) // 4


def placed_blocks(cmds, bw, bh):
    """Run list -> [(cell_index, order_index)].  order_index counts drawn cells
    so the caller can pull the matching 8-byte block from the stream."""
    out, pos, drawn = [], 0, 0
    for skip, draw in cmds:
        pos += skip
        for _ in range(draw):
            if 0 <= pos < bw * bh:
                out.append((pos, drawn))
            drawn += 1
            pos += 1
    return out


# ------------------------------------------------------------------- decoders

def _rgb565(c):
    return ((c >> 11 & 0x1F) * 255 // 31,
            (c >> 5 & 0x3F) * 255 // 63,
            (c & 0x1F) * 255 // 31)


def bc1_palette(blk):
    c0 = blk[0] | blk[1] << 8
    c1 = blk[2] | blk[3] << 8
    a, b = _rgb565(c0), _rgb565(c1)
    if c0 > c1:
        return [a + (255,), b + (255,),
                tuple((2 * a[i] + b[i]) // 3 for i in range(3)) + (255,),
                tuple((a[i] + 2 * b[i]) // 3 for i in range(3)) + (255,)]
    return [a + (255,), b + (255,),
            tuple((a[i] + b[i]) // 2 for i in range(3)) + (255,),
            (0, 0, 0, 0)]


def bc4_palette(blk):
    """1-channel block.  a0 > a1 -> 8 values; else 6 values + {0,255}."""
    a0, a1 = blk[0], blk[1]
    if a0 > a1:
        return [a0, a1] + [((6 - i) * a0 + (i + 1) * a1) // 7 for i in range(6)]
    return [a0, a1] + [((4 - i) * a0 + (i + 1) * a1) // 5 for i in range(4)] + [0, 255]


def _idx_bits(blk):
    v = blk[4] | blk[5] << 8 | blk[6] << 16 | blk[7] << 24
    return [(v >> (2 * i)) & 3 for i in range(16)]


def _idx_bits3(blk):
    v = int.from_bytes(blk[2:8], "little")
    return [(v >> (3 * i)) & 7 for i in range(16)]


def decode_bc1_plane(blocks, bw, bh, cmds=None):
    """-> bytearray RGBA of size (bw*4) x (bh*4)

    `blocks` are consumed in DRAW order; `cmds` (skip/draw run list over the
    row-major cell grid) says which cell each drawn block lands in.  Without
    `cmds` the blocks are assumed to fill the grid in order.
    """
    W, H = bw * 4, bh * 4
    img = bytearray(W * H * 4)
    if cmds is None:
        placed = [(n, n) for n in range(bw * bh)]
    else:
        placed = placed_blocks(cmds, bw, bh)
    for cell, drawn in placed:
        if drawn >= len(blocks):
            break
        blk = blocks[drawn]
        pal = bc1_palette(blk)
        bits = _idx_bits(blk)
        gx, gy = (cell % bw) * 4, (cell // bw) * 4
        for i in range(16):
            x, y = gx + (i % 4), gy + (i // 4)
            if x >= W or y >= H:
                continue
            o = (y * W + x) * 4
            img[o:o + 4] = bytes(pal[bits[i]])
    return img, W, H


def decode_bc4_plane(blocks, bw, bh, cmds=None):
    """-> bytearray L8 of size (bw*4) x (bh*4)"""
    W, H = bw * 4, bh * 4
    img = bytearray(W * H)
    if cmds is None:
        placed = [(n, n) for n in range(bw * bh)]
    else:
        placed = placed_blocks(cmds, bw, bh)
    for cell, drawn in placed:
        if drawn >= len(blocks):
            break
        blk = blocks[drawn]
        pal = bc4_palette(blk)
        bits = _idx_bits3(blk)
        gx, gy = (cell % bw) * 4, (cell // bw) * 4
        for i in range(16):
            x, y = gx + (i % 4), gy + (i // 4)
            if x >= W or y >= H:
                continue
            img[y * W + x] = pal[bits[i]]
    return img, W, H


# ------------------------------------------------------------------ renderer

def render_frame(frame, team=(220, 60, 60), with_shadow=True, with_pc=True):
    """Composite one frame onto its canvas.  Returns (bytearray RGBA, w, h)
    plus a dict of intermediate planes for inspection."""
    w, h = frame.canvas_w, frame.canvas_h
    canvas = bytearray(w * h * 4)
    info = {}

    m = frame.layers.get("main")
    if m is not None:
        rect, fmt, ncmd, cmds = parse_rect_layer(m)
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        plane, PW, PH = decode_bc1_plane(rect_blocks(m, ncmd), bw, bh, cmds)
        info["main_rect"] = rect
        info["grid"] = (bw, bh)
        info["main_plane"] = (plane, PW, PH)

        # player colour mask first, so we can tint before compositing
        pc_plane = None
        if with_pc and "playercolor" in frame.layers:
            pcl = frame.layers["playercolor"]
            pfmt, pncmd, pcmds = parse_mask_layer(pcl)
            pc_plane = decode_bc4_plane(mask_blocks(pcl, pncmd), bw, bh, pcmds)
            info["pc_plane"] = pc_plane
            info["pc_fmt"] = pfmt

        for gy in range(PH):
            for gx in range(PW):
                sx, sy = x1 + gx, y1 + gy
                if not (0 <= sx < w and 0 <= sy < h):
                    continue
                o = (sy * w + sx) * 4
                r, g, b, a = plane[(gy * PW + gx) * 4:(gy * PW + gx) * 4 + 4]
                if a == 0:
                    continue
                if pc_plane is not None:
                    msk = pc_plane[0][gy * pc_plane[1] + gx]
                    if msk:
                        f = msk / 255.0
                        r = int(r * (1 - f) + team[0] * f)
                        g = int(g * (1 - f) + team[1] * f)
                        b = int(b * (1 - f) + team[2] * f)
                canvas[o:o + 4] = bytes((r, g, b, a))

    if with_shadow and "shadow" in frame.layers:
        sl = frame.layers["shadow"]
        rect, fmt, ncmd, cmds = parse_rect_layer(sl)
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        plane, PW, PH = decode_bc4_plane(rect_blocks(sl, ncmd), bw, bh, cmds)
        info["shadow_plane"] = (plane, PW, PH)
        info["shadow_rect"] = rect

    # damage mask: same grid as main, placed over the composited sprite
    if "damage" in frame.layers and "main" in frame.layers:
        d = frame.layers["damage"]
        dfmt, dncmd, dcmds = parse_mask_layer(d)
        rect = info["main_rect"]
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        dplane, DW, DH = decode_bc4_plane(mask_blocks(d, dncmd), bw, bh, dcmds)
        info["damage_plane"] = (dplane, DW, DH)
        info["damage_fmt"] = dfmt
        for gy in range(min(DH, frame.canvas_h)):
            for gx in range(min(DW, frame.canvas_w)):
                sx, sy = x1 + gx, y1 + gy
                if not (0 <= sx < w and 0 <= sy < h):
                    continue
                o = (sy * w + sx) * 4
                if not canvas[o + 3]:
                    continue
                k = dplane[gy * DW + gx]
                if k:
                    f = k / 255.0
                    for c in range(3):
                        canvas[o + c] = int(canvas[o + c] * (1 - f))

    return canvas, w, h, info


def desaturate_alpha(canvas, w, h, bg=(24, 24, 28)):
    """Flatten RGBA over a background for PNG output."""
    out = bytearray(w * h * 3)
    for i in range(w * h):
        a = canvas[i * 4 + 3]
        if a == 0:
            out[i * 3:i * 3 + 3] = bytes(bg)
        else:
            f = a / 255.0
            for c in range(3):
                out[i * 3 + c] = int(canvas[i * 4 + c] * f + bg[c] * (1 - f))
    return out, w, h
