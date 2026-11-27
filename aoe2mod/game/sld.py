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


# ------------------------------------------------------- delta frame replay

def layer_is_patch(layer, mask=False):
    # True when this layer is a PATCH over the frame before it.  A main or
    # shadow layer keeps fmt at offset 8; a mask keeps it at offset 0.  Bit
    # 0x80 says 'this layer carries its own run list', and on a later frame a
    # run list is a patch, not a picture -- see Walk.
    off = 0 if mask else 8
    return bool(struct.unpack_from('<H', layer.data, off)[0] & 0x80)


def decode_absolute(cells, w, h, mask=False):
    # -> (plane, w, h) from a {(x, y): 8-byte block} dict.  The key is the
    # pixel on the CANVAS that the block's top-left corner sits on, not a grid
    # index -- see Walk for why that difference is the whole bug.
    #
    # A cell that is not in the dict was never drawn and stays empty.  That is
    # NOT the same as a cell holding a zeroed block, which decodes to real
    # pixels (an all-zero BC1 block is opaque black, an all-zero BC4 block is
    # 0), so the two cases must never be folded together.
    img = bytearray(w * h) if mask else bytearray(w * h * 4)
    for (px, py), blk in cells.items():
        if mask:
            pal, bits = bc4_palette(blk), _idx_bits3(blk)
        else:
            pal, bits = bc1_palette(blk), _idx_bits(blk)
        for i in range(16):
            x, y = px + (i % 4), py + (i // 4)
            if not (0 <= x < w and 0 <= y < h):
                continue
            if mask:
                img[y * w + x] = pal[bits[i]]
            else:
                o = (y * w + x) * 4
                img[o:o + 4] = bytes(pal[bits[i]])
    return img, w, h


class Walk:
    # Replays a file's frames in order so a patch frame comes out whole.
    #
    # WHY THIS EXISTS.  Most .sld frames are not pictures, they are patches:
    # bit 0x80 in the layer's fmt says the layer carries its own run list, and
    # on any frame after the first of a pose that run list names only the cells
    # whose colour changed.  Archer idle is 903 patch frames out of 961; the
    # villager's is 960 whole frames out of 960, which is why only some units
    # looked broken.  Drawn on its own, a patch frame shows the handful of
    # cells it happened to resend: the body vanishes and a row of black dashes
    # is left where the bow was -- the player reported exactly that twice
    # (2026-11-27) and was right both times.
    #
    # The engine keeps the previous cells and overwrites the named ones.  So
    # does this: take(frame) applies one frame in file order, plane(name) hands
    # back the picture as of that frame.  A layer whose fmt has no 0x80 starts a
    # new picture, which is exactly the reset the format implies.
    #
    # A CELL IS A PLACE ON THE CANVAS, NOT A GRID INDEX (measured 2026-11-27).
    # The first version of this class keyed cells by their index in the frame's
    # own grid, which is only the same thing while the rect never moves.  It
    # does move: the mangudai idle rect changes 110 times over 961 frames, 95
    # of those changes on a patch frame, and each move shifts the grid by 4 px.
    # Keyed by index, a cell that is not resent keeps its old block, which the
    # canvas then paints at the NEW rect origin: the previous pose is dragged
    # along behind the new one.  Over 300 frames that leftover is 403,922 opaque
    # pixels on the mangudai (3,614 in one frame) against 277 keyed by screen
    # position, and 80,972 against 0 on the archer.  The player saw it as a
    # smear of torn black dashes on the mangudai strip (2026-11-25).
    #
    # So the key is (x, y) on the canvas: `rect.x1 + (cell % bw) * 4` and
    # `rect.y1 + (cell // bw) * 4`.  A mask has no rect of its own and rides on
    # main's, exactly as parse_mask_layer's docstring says.

    NAMES = ('main', 'playercolor', 'shadow', 'damage')
    MASKS = ('playercolor', 'damage')

    def __init__(self, width=0, height=0):
        self.cells = dict((nm, {}) for nm in self.NAMES)
        self.w = int(width or 0)
        self.h = int(height or 0)
        self.wholes = 0     # main-layer whole frames (each starts a picture)
        self.patches = 0    # main-layer patches since the last whole frame

    def _room(self, frame):
        # The canvas can differ between frames of one file (a house's age
        # states are 300x300 and 400x400), so it is grown, never fixed.
        if frame.canvas_w > self.w:
            self.w = frame.canvas_w
        if frame.canvas_h > self.h:
            self.h = frame.canvas_h

    def take(self, frame):
        self._room(frame)
        m = frame.layers.get('main')
        mg = grid_of(parse_rect_layer(m)[0]) if m is not None else None
        for nm in self.NAMES:
            layer = frame.layers.get(nm)
            if layer is None:
                continue
            mask = nm in self.MASKS
            if mask:
                fmt, ncmd, cmds = parse_mask_layer(layer)
                blocks = mask_blocks(layer, ncmd)
                g = mg
            else:
                rect, fmt, ncmd, cmds = parse_rect_layer(layer)
                blocks = rect_blocks(layer, ncmd)
                g = grid_of(rect)
            if g is None:
                continue
            x1, y1, bw, bh = g[0], g[1], g[4], g[5]
            dest = self.cells[nm]
            if not (fmt & 0x80):
                dest.clear()
                if nm == 'main':
                    self.wholes += 1
            elif nm == 'main':
                self.patches += 1
            for cell, drawn in placed_blocks(cmds, bw, bh):
                if drawn >= len(blocks):
                    continue
                dest[(x1 + (cell % bw) * 4, y1 + (cell // bw) * 4)] = blocks[drawn]
        return self

    def plane(self, name, mask=False):
        # The accumulated picture of one layer, or None when it has none.
        if self.w <= 0 or self.h <= 0:
            return None
        if not self.cells[name]:
            return None
        return decode_absolute(self.cells[name], self.w, self.h, mask=mask)

# ------------------------------------------------------------------ renderer

def render_frame(frame, team=(220, 60, 60), with_shadow=True, with_pc=True,
                 walk=None):
    """Composite one frame onto its canvas.  Returns (bytearray RGBA, w, h)
    plus a dict of intermediate planes for inspection.

    With `walk`, the picture comes from the replay instead of the frame: a
    patch frame only resends the cells whose colour changed, and the walk owns
    every cell applied so far, keyed by canvas position.  Each plane is then
    already canvas-sized, so nothing here adds a rect origin to a coordinate.
    """
    w, h = frame.canvas_w, frame.canvas_h
    canvas = bytearray(w * h * 4)
    info = {}

    m = frame.layers.get("main")
    if m is not None:
        rect, fmt, ncmd, cmds = parse_rect_layer(m)
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        if walk is None:
            plane, PW, PH = decode_bc1_plane(rect_blocks(m, ncmd), bw, bh, cmds)
            ox, oy = x1, y1
        else:
            # A patch frame carries only the cells that changed; the walk holds
            # the picture as of this frame, which is what the engine draws.
            plane, PW, PH = walk.plane("main")
            ox, oy = 0, 0
        info["main_rect"] = rect
        info["grid"] = (bw, bh)
        info["main_plane"] = (plane, PW, PH)

        # player colour mask first, so we can tint before compositing
        pc_plane = None
        if with_pc and "playercolor" in frame.layers:
            pcl = frame.layers["playercolor"]
            pfmt, pncmd, pcmds = parse_mask_layer(pcl)
            if walk is None:
                pc_plane = decode_bc4_plane(mask_blocks(pcl, pncmd), bw, bh, pcmds)
            else:
                pc_plane = walk.plane("playercolor", mask=True)
            info["pc_plane"] = pc_plane
            info["pc_fmt"] = pfmt

        for gy in range(PH):
            for gx in range(PW):
                sx, sy = ox + gx, oy + gy
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
        if walk is None:
            plane, PW, PH = decode_bc4_plane(rect_blocks(sl, ncmd), bw, bh, cmds)
        else:
            plane, PW, PH = walk.plane("shadow", mask=True)
        info["shadow_plane"] = (plane, PW, PH)
        info["shadow_rect"] = rect
        info["shadow_absolute"] = walk is not None

    # damage mask: same grid as main, placed over the composited sprite
    if "damage" in frame.layers and "main" in frame.layers:
        d = frame.layers["damage"]
        dfmt, dncmd, dcmds = parse_mask_layer(d)
        rect = info["main_rect"]
        x1, y1, rw, rh, bw, bh = grid_of(rect)
        if walk is None:
            dplane, DW, DH = decode_bc4_plane(mask_blocks(d, dncmd), bw, bh, dcmds)
            dx, dy = x1, y1
        else:
            dplane, DW, DH = walk.plane("damage", mask=True)
            dx, dy = 0, 0
        info["damage_plane"] = (dplane, DW, DH)
        info["damage_fmt"] = dfmt
        for gy in range(min(DH, frame.canvas_h)):
            for gx in range(min(DW, frame.canvas_w)):
                sx, sy = dx + gx, dy + gy
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
