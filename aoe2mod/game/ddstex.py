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
    """-> dict(width, height, pitch, fourcc, dx10_format, data_offset)."""
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
            "data_offset": 148 if fourcc == "DX10" else 128}


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

    if not fourcc:                                  # uncompressed BGRA
        need = w * h * 4
        if len(body) < need:
            raise ValueError("raw BGRA data short: %d < %d bytes" % (len(body), need))
        out = bytearray(need)
        # BGRA -> RGBA, swapping only the two colour channels.
        out[0::4] = body[2:need:4]
        out[1::4] = body[1:need:4]
        out[2::4] = body[0:need:4]
        out[3::4] = body[3:need:4]
        return w, h, bytes(out)

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
            if block == 8:
                c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
                cols, opaque = _rgb565(c0, c1)
            else:
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
                    if block == 16:
                        a = ((blk[i // 2] >> (4 * (i % 2))) & 0xF) * 17
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

    The shipped unit icons split 539 uncompressed / 255 DXT5, so raw BGRA is not
    a hack around the format -- it is the majority shape.  That matters because
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
    # RGBA -> BGRA for the same reason `decode` swaps them.
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
