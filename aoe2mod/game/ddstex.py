# -*- coding: utf-8 -*-
"""Decode the game's DDS icon files to RGBA, and re-encode them as PNG.

Every icon the game ships is a DDS texture: `widgetui/materials.json` points at
`widgetui/textures/ingame/**/*.dds`, and a browser cannot draw a DDS.  So the UI
has to convert.  This module is the converter, and it only handles the layouts
the shipped icon textures actually use (measured over all 4,550 texture entries
in materials.json):

    uncompressed BGRA 8:8:8:8   pitch == width*4, fourcc empty   (539/794 unit icons)
    DXT5 / BC3                                                   (most of the rest)
    DXT1 / BC1

Two facts keep this simple and are worth stating because they are easy to
"optimise" wrongly:

* The loose FileName under an icon atlas IS the whole icon -- its pixel size
  equals `uv * atlas_size` for 1,211 of 1,211 icon entries -- so the UV rect must
  NOT be used to crop it.  See `probe_icon_render_route.py`.
* The atlas `MaxWidth`/`MaxHeight` are not the file's size; the file's own header
  is authoritative.

Nothing here writes into the game folder.  `to_png` returns bytes.
"""
import struct
import zlib

# DXGI_FORMAT values that show up in DX10 headers for the formats above.
_DX10_BC1 = 71
_DX10_BC3 = 77
_DX10_BGRA = 87


def header(path):
    """-> dict(width, height, pitch, fourcc, dx10_format, masks, data_offset).

    `masks` is the (R, G, B, A) bit-mask tuple from the pixel format block.  For
    a block-compressed file all four are 0 and channel order comes from the DXT
    tables; for an uncompressed one the masks are the whole story about channel
    order, which is why they are read here instead of assumed in `decode`.
    """
    with open(path, "rb") as fh:
        b = fh.read(148)
    if len(b) < 128 or b[:4] != b"DDS ":
        raise ValueError("not a DDS file: %r" % (path,))
    fourcc = struct.unpack_from("<4s", b, 84)[0].decode("latin-1").strip("\x00")
    dx10 = None
    if fourcc == "DX10" and len(b) >= 148:
        dx10 = struct.unpack_from("<I", b, 128)[0]
    return {"width": struct.unpack_from("<I", b, 16)[0],
            "height": struct.unpack_from("<I", b, 12)[0],
            "pitch": struct.unpack_from("<I", b, 20)[0],
            "fourcc": fourcc,
            "dx10_format": dx10,
            "masks": struct.unpack_from("<IIII", b, 92),
            "data_offset": 148 if fourcc == "DX10" else 128}


def _mask_shift(mask):
    """-> (shift, bits) for one channel mask, or (0, 0) when the mask is empty."""
    if not mask:
        return 0, 0
    shift = 0
    while not (mask >> shift) & 1:
        shift += 1
    bits = 0
    while (mask >> (shift + bits)) & 1:
        bits += 1
    return shift, bits


def _bc3_alpha_table(a0, a1):
    """-> the 8-entry alpha palette a BC3/DXT5 block's 3-bit indices point into.

    Why this exists, and why the old code was wrong
    -----------------------------------------------
    BC3 stores alpha as its own 8-byte block: two endpoint bytes `a0`/`a1`, then
    48 bits holding sixteen 3-bit indices.  When `a0 > a1` the six middle entries
    are 7ths of the way from a1 to a0; otherwise they are 5ths and the last two
    entries become the hard 0 and 255.  That is the whole format.

    Until 2026-11-05 this file decoded DXT5 alpha with the DXT3 rule --
    `((blk[i // 2] >> (4 * (i % 2))) & 0xF) * 17`, i.e. sixteen 4-bit explicit
    values -- because `block == 16` was treated as one thing.  DXT3 (BC2) and
    DXT5 (BC3) share a block size and share nothing else, so every BC3 icon came
    out with alpha values like 34/68/153 and the thin end of the sprite faded
    into the list background.  The owner reported that as "some icons are still
    ghosts"; measured over the editor's 400 rows, 17 of them had not one opaque
    pixel (longbowman, the elite variants, Harald Hardrada, the big pavilion),
    and forcing alpha to 255 restored each one to full colour -- the pixels were
    always fine, only the alpha channel was misread.

    Checked against Pillow on all 17 DXT5 files the editor shows: this table
    agrees on 65,536 of 65,536 pixels per file, where the old path agreed on
    12,303-16,384.
    """
    if a0 > a1:
        return (a0, a1) + tuple(((7 - k) * a0 + k * a1) // 7 for k in range(1, 7))
    return (a0, a1) + tuple(((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)) + (0, 255)


def _rgb565(c0, c1):
    def expand(c):
        r = (c >> 11) & 0x1F
        g = (c >> 5) & 0x3F
        b = c & 0x1F
        return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))
    a, b = expand(c0), expand(c1)
    if c0 > c1:
        return [a, b,
                tuple((2 * a[k] + b[k]) // 3 for k in range(3)),
                tuple((a[k] + 2 * b[k]) // 3 for k in range(3))], True
    return [a, b, tuple((a[k] + b[k]) // 2 for k in range(3)), (0, 0, 0)], False


def decode(path):
    """-> (width, height, RGBA bytes).  Raises ValueError with a reason."""
    hd = header(path)
    w, h = hd["width"], hd["height"]
    with open(path, "rb") as fh:
        fh.seek(hd["data_offset"])
        body = fh.read()

    fourcc = hd["fourcc"]
    if fourcc == "DX10":
        fmt = hd["dx10_format"]
        if fmt == _DX10_BC3:
            fourcc = "DXT5"
        elif fmt == _DX10_BC1:
            fourcc = "DXT1"
        elif fmt == _DX10_BGRA:
            fourcc = ""
        else:
            raise ValueError("unsupported DXGI format %s in %r" % (fmt, path))

    if not fourcc:                                  # uncompressed 32-bit
        need = w * h * 4
        if len(body) < need:
            raise ValueError("raw BGRA data short: %d < %d bytes" % (len(body), need))
        return w, h, _uncompressed(body, need, hd["masks"], path)

    if fourcc in ("DXT5", "DXT4", "BC3"):
        block = 16
    elif fourcc in ("DXT1", "BC1"):
        block = 8
    else:
        raise ValueError("unsupported fourcc %r in %r (DXGI %s)"
                         % (fourcc, path, hd["dx10_format"]))
    bw, bh = (w + 3) // 4, (h + 3) // 4
    if len(body) < bw * bh * block:
        raise ValueError("block data short: %d < %d bytes"
                         % (len(body), bw * bh * block))
    out = bytearray(w * h * 4)
    pos = 0
    for by in range(bh):
        for bx in range(bw):
            blk = body[pos:pos + block]
            pos += block
            apal = None
            if block == 8:
                c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
                cols, opaque = _rgb565(c0, c1)
            else:
                # BC3/DXT5: alpha is a block of its own in the first 8 bytes, the
                # colour block is the same BC1 shape the DXT1 path uses.  See
                # _bc3_alpha_table for what went wrong when this was DXT3.
                apal = _bc3_alpha_table(blk[0], blk[1])
                abits = int.from_bytes(blk[2:8], "little")
                c0, c1 = struct.unpack_from("<HH", blk, 8)
                cols, _opaque = _rgb565(c0, c1)
                bits = struct.unpack_from("<I", blk, 12)[0]
            for py in range(4):
                y = by * 4 + py
                if y >= h:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x >= w:
                        continue
                    i = py * 4 + px
                    r, g, b = cols[(bits >> (2 * i)) & 3]
                    if apal is not None:
                        a = apal[(abits >> (3 * i)) & 7]
                    elif cols is not None and c0 <= c1 and ((bits >> (2 * i)) & 3) == 3:
                        a = 0
                    else:
                        a = 255
                    o = (y * w + x) * 4
                    out[o] = r
                    out[o + 1] = g
                    out[o + 2] = b
                    out[o + 3] = a
    return w, h, bytes(out)


def _uncompressed(body, need, masks, path):
    """Raw 32-bit pixels -> RGBA, using the header's masks to find each channel.

    Why this is not a hardcoded BGR->RGB swap
    -----------------------------------------
    The first version of this decoder assumed every uncompressed icon was BGRA
    and swapped channels 0 and 2.  That is true for 14 of the 1,052 uncompressed
    DDS files the game ships, and false for the other 1,038: measured across
    `widgetui/textures` on 2026-11-01,

        rmask=0x000000FF gmask=0x0000FF00 bmask=0x00FF0000 amask=0xFF000000  1038 files
        rmask=0x00FF0000 gmask=0x0000FF00 bmask=0x000000FF amask=0xFF000000    14 files

    so the swap painted 1,038 icons with red and blue exchanged.  On a villager
    the skin turned blue and it read as "the icon is inverted", which is what the
    owner reported.  The header had been saying which byte was which all along;
    nothing was reading it.

    A mask states where a channel lives and how many bits it holds, so this reads
    the answer instead of remembering it.  Both shapes above go through the same
    path, and the 8-bit-in-place case keeps the fast slice assignment rather than
    a per-pixel loop -- 539 unit icons are 256x256.
    """
    if not any(masks):
        # No mask means the header is not describing a channel layout we can
        # honour.  Use the order 98% of the shipped files carry rather than
        # drawing something plausible-but-wrong.
        masks = (0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000)
    plan = []
    for mask in masks:
        shift, bits = _mask_shift(mask)
        plan.append((shift, bits) if bits else None)

    out = bytearray(need)
    n = need // 4

    # Fast path: all four channels are whole bytes, each sitting in its own byte.
    if all(p is not None and p[1] == 8 and p[0] % 8 == 0 for p in plan[:3]):
        for idx in (0, 1, 2):
            out[idx::4] = body[plan[idx][0] // 8:need:4]
        if plan[3] is None:
            out[3::4] = bytes([255]) * n
        else:
            out[3::4] = body[plan[3][0] // 8:need:4]
        return bytes(out)

    # General path: read each pixel word and pick the bits the mask names.
    for i in range(n):
        word = int.from_bytes(body[i * 4:i * 4 + 4], "little")
        for idx in (0, 1, 2, 3):
            p = plan[idx]
            if p is None:
                out[i * 4 + idx] = 255 if idx == 3 else 0
                continue
            shift, bits = p
            top = (1 << bits) - 1
            v = (word >> shift) & top
            out[i * 4 + idx] = v if bits == 8 else (v * 255 + top // 2) // top
    return bytes(out)


def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(width, height, rgba):
    """RGBA bytes -> PNG bytes (no PIL; the project ships none)."""
    need = width * height * 4
    if len(rgba) != need:
        raise ValueError("pixel buffer is %d bytes, expected %d for %dx%d"
                         % (len(rgba), need, width, height))
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)                       # filter type 0 for every scanline
        raw += rgba[y * stride:(y + 1) * stride]
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def to_png(path, max_side=0):
    """Decode a DDS and return PNG bytes, optionally box-filtered down.

    `max_side` exists because the UI draws icons at 32-64px and the files are
    256x256; shipping the full texture per icon would be ~100x the bytes for no
    visible gain.  A value of 0 keeps the original size.
    """
    w, h, rgba = decode(path)
    if max_side and max(w, h) > max_side:
        w, h, rgba = shrink(w, h, rgba, max_side)
    return encode_png(w, h, rgba)


def encode_bgra(width, height, rgba):
    """RGBA bytes -> an uncompressed 32-bit DDS the game reads.

    The shipped icons split 1,052 uncompressed / 362 block-compressed, so a raw
    pixel DDS is not a hack around the format -- it is the majority shape.  That matters because
    this project can compose pixels (it already decodes every icon to RGBA to
    draw the screen) but has no DXT encoder, and a mod that only needs to draw a
    square picture does not need one.

    The header is 128 bytes and follows the four masks DDPF_RGB|DDPF_ALPHAPIXELS
    layout the game's own uncompressed icons use; `decode` reads it back, so the
    two functions are each other's proof.

    **The flag word has to agree with the mip count.**  The first version of this
    function wrote ``0x00081007`` -- which includes ``DDSD_MIPMAPCOUNT`` -- and
    then left the mip field at zero.  Every icon built that way drew as an empty
    box in game, while the same pixels with ``0x0000100F`` (the word both shipped
    families use) drew correctly.  Measured 2026-10-24 in four runs:

        flags 0x00081007, mips 0  -> empty box   (v63..v72, and v62's icons)
        flags 0x00081007, mips 1  -> drawn
        flags 0x0000100F, mips 0  -> drawn
        flags 0x0000100F, mips 1  -> drawn

    So it is not "mips are required" and not "that flag is wrong": declaring a
    count and shipping zero levels is the contradiction the engine refuses.  This
    now writes the shape the shipped icons write.  `decode` cannot catch a mistake
    of this class -- it reads whatever the header claims -- which is why it took a
    match to find.
    """
    if len(rgba) != width * height * 4:
        raise ValueError("pixel buffer is %d bytes, expected %d for %dx%d"
                         % (len(rgba), width * height * 4, width, height))
    head = bytearray(128)
    head[0:4] = b"DDS "
    struct.pack_into("<I", head, 4, 124)              # dwSize
    struct.pack_into("<I", head, 8, 0x0000100F)       # caps|height|width|pitch|pf
    struct.pack_into("<I", head, 12, height)
    struct.pack_into("<I", head, 16, width)
    struct.pack_into("<I", head, 20, width * 4)       # linear size
    struct.pack_into("<I", head, 28, 1)               # one mip level
    struct.pack_into("<I", head, 76, 32)              # pixel format size
    struct.pack_into("<I", head, 80, 0x41)            # RGB | ALPHAPIXELS
    struct.pack_into("<I", head, 88, 32)              # bits per pixel
    struct.pack_into("<I", head, 92, 0x00FF0000)      # R mask
    struct.pack_into("<I", head, 96, 0x0000FF00)      # G mask
    struct.pack_into("<I", head, 100, 0x000000FF)     # B mask
    struct.pack_into("<I", head, 104, 0xFF000000)     # A mask
    struct.pack_into("<I", head, 108, 0x1000)         # DDSCAPS_TEXTURE
    # RGBA -> BGRA because the masks written above say BGRA.  The swap is not a
    # property of DDS, it is this header's own claim, and `decode` reads that
    # claim back -- so writing the masks and the bytes from the same constant is
    # what makes them each other's proof.
    body = bytearray(len(rgba))
    body[0::4] = rgba[2::4]
    body[1::4] = rgba[1::4]
    body[2::4] = rgba[0::4]
    body[3::4] = rgba[3::4]
    return bytes(head) + bytes(body)


def shrink(width, height, rgba, max_side):
    """Integer box filter to at most `max_side` on the long edge."""
    factor = 1
    while max(width // (factor * 2), height // (factor * 2)) >= 1 and \
            max(width, height) // factor > max_side:
        factor += 1
    if factor == 1:
        return width, height, rgba
    nw, nh = max(1, width // factor), max(1, height // factor)
    out = bytearray(nw * nh * 4)
    area = factor * factor
    for y in range(nh):
        for x in range(nw):
            r = g = b = a = 0
            for dy in range(factor):
                row = (y * factor + dy) * width
                for dx in range(factor):
                    o = (row + x * factor + dx) * 4
                    r += rgba[o]
                    g += rgba[o + 1]
                    b += rgba[o + 2]
                    a += rgba[o + 3]
            p = (y * nw + x) * 4
            out[p] = r // area
            out[p + 1] = g // area
            out[p + 2] = b // area
            out[p + 3] = a // area
    return nw, nh, bytes(out)
