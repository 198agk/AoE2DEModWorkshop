# -*- coding: utf-8 -*-
"""Read a picture file without Pillow.

Why this module exists
----------------------
Every other part of this package is stdlib-only, and the packaged build has
Pillow **excluded on purpose** (`_build/aoe2mod.spec` lists `"PIL"` in
`excludes`, because a one-file build that drags in image libraries is 40 MB
bigger for one feature).  The icon and repaint paths still called
`from PIL import Image`, so on a player's machine the sentence

    给不列颠新建一个单位叫图标学徒，图片用 D:\\图\\我的图.png

reached the build and answered `这个版本装不了图片读取组件（Pillow），没法读你给的图片`
-- measured 2026-10-30 against a packaged build, whose bundled
`app/aoe2mod/` ships only `schema/` and `ui/`.  The repo had
Pillow, so every test was green and the shipped program could not draw an icon.

What is supported here
----------------------
* PNG  -- non-interlaced, bit depth 1/2/4/8/16, colour types 0/2/3/4/6 (grey,
  truecolour, palette, grey+alpha, truecolour+alpha).  Adam7 interlacing is
  refused by name rather than silently mis-decoded.
* BMP  -- 24-bit and 32-bit BI_RGB (the shapes the mspaint and GIMP exports use).
* DDS  -- delegated to `aoe2mod.game.ddstex.decode`, which already reads both the
  uncompressed BGRA and DXT1/DXT5 families the game ships.

JPEG is refused with a sentence that says what to do instead: writing a baseline
decoder is a project of its own, and PIL is used when the host happens to have
it, so a machine that can actually open JPEGs still can.

The letterboxing that the icon layer needs lives here too, because "fit this
picture into a 256x256 square on a transparent margin" is arithmetic on pixels,
not a library feature.
"""
import os
import struct
import zlib

from . import ddstex

#: What the error messages promise the player they can drop on the tool.
SUPPORTED = "PNG、BMP、DDS"


class PictureError(Exception):
    """A picture that cannot be read, with a reason written for a player."""


def _png_chunks(body):
    pos = 8                                     # skip the signature
    n = len(body)
    while pos + 8 <= n:
        (length,) = struct.unpack_from(">I", body, pos)
        tag = body[pos + 4:pos + 8]
        data = body[pos + 8:pos + 8 + length]
        yield tag, data
        pos += 12 + length                      # length + tag + crc


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw, width, height, bpp, stride):
    """Undo the per-scanline filters PNG applies before compression."""
    out = bytearray(height * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if len(line) < stride:
            raise PictureError("这张图片的数据不完整，可能下载或复制时被截断了")
        if ftype == 0:
            pass
        elif ftype == 1:                        # Sub
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:                        # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:                        # Average
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:                        # Paeth
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                upleft = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
        else:
            raise PictureError("这张图片用了不认识的扫描行压缩方式（%d）" % ftype)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def _expand_to_rgba(pix, width, height, depth, ctype, palette, trns):
    """PNG samples -> RGBA bytes, whatever bit depth and colour type they are.

    `sample(row, x, c)` reads ONE scanline, not the whole image: the first
    version indexed `pix` without the row offset, so every scanline came back
    identical to the first.  A 4x4 round-trip showed it (`row 1 green = 0`), and
    the 64x64 case did not, because the picture happened to be symmetric enough
    to look plausible -- measure with an asymmetric fixture.
    """
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = (width * channels * depth + 7) // 8
    out = bytearray(width * height * 4)
    top = (1 << depth) - 1

    def sample(row, x, c):
        """The c-th sample of pixel x on THIS scanline, scaled to 0..255."""
        if depth == 8:
            return row[x * channels + c]
        if depth == 16:
            return row[(x * channels + c) * 2]          # high byte is enough
        bit = x * channels * depth + c * depth
        shift = 8 - depth - (bit % 8)
        raw = (row[bit // 8] >> shift) & top
        return raw * 255 // top

    def index(row, x):
        """The palette entry number of pixel x, at whatever bit depth."""
        if depth == 8:
            return row[x]
        bit = x * depth
        shift = 8 - depth - (bit % 8)
        return (row[bit // 8] >> shift) & top

    for y in range(height):
        row = pix[y * stride:(y + 1) * stride]
        for x in range(width):
            o = (y * width + x) * 4
            if ctype == 3:
                idx = index(row, x)
                if palette and idx * 3 + 2 < len(palette):
                    out[o] = palette[idx * 3]
                    out[o + 1] = palette[idx * 3 + 1]
                    out[o + 2] = palette[idx * 3 + 2]
                out[o + 3] = trns[idx] if (trns and idx < len(trns)) else 255
                continue
            if ctype in (0, 4):
                g = sample(row, x, 0)
                out[o] = out[o + 1] = out[o + 2] = g
                out[o + 3] = sample(row, x, 1) if ctype == 4 else 255
                continue
            out[o] = sample(row, x, 0)
            out[o + 1] = sample(row, x, 1)
            out[o + 2] = sample(row, x, 2)
            if ctype == 6:
                out[o + 3] = sample(row, x, 3)
            elif trns and len(trns) >= 6:
                r, g, b = struct.unpack(">HHH", trns[:6])
                same = (out[o] == (r >> 8) and out[o + 1] == (g >> 8)
                        and out[o + 2] == (b >> 8))
                out[o + 3] = 0 if same else 255
            else:
                out[o + 3] = 255
    return bytes(out)


def _read_png(body):
    if body[:8] != b"\x89PNG\r\n\x1a\n":
        raise PictureError("这不是 PNG")
    width = height = depth = ctype = interlace = None
    palette = None
    trns = None
    idat = bytearray()
    for tag, data in _png_chunks(body):
        if tag == b"IHDR":
            (width, height, depth, ctype,
             _comp, _filt, interlace) = struct.unpack(">IIBBBBB", data[:13])
        elif tag == b"PLTE":
            palette = data
        elif tag == b"tRNS":
            trns = data
        elif tag == b"IDAT":
            idat += data
        elif tag == b"IEND":
            break
    if width is None:
        raise PictureError("这张 PNG 没有文件头，可能不是图片")
    if interlace:
        raise PictureError("这张 PNG 用的是逐行交错（Adam7）存储，暂时读不了；"
                           "用画图或 GIMP 另存一次就能读")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None:
        raise PictureError("这张 PNG 用了不认识的色彩类型（%d）" % ctype)
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        raise PictureError("这张 PNG 的像素数据坏了，读不出来")
    stride = (width * channels * depth + 7) // 8
    bpp = max(1, (channels * depth) // 8)
    pix = _unfilter(raw, width, height, bpp, stride)
    return width, height, _expand_to_rgba(pix, width, height, depth, ctype,
                                          palette, trns)


def _read_bmp(body):
    if body[:2] != b"BM":
        raise PictureError("这不是 BMP")
    (offset,) = struct.unpack_from("<I", body, 10)
    (hsize,) = struct.unpack_from("<I", body, 14)
    if hsize < 40:
        raise PictureError("这张 BMP 是旧版格式（%d 字节头），读不了" % hsize)
    width, height, _planes, bpp, comp = struct.unpack_from("<iiHHI", body, 18)
    flip = height > 0
    height = abs(height)
    if comp not in (0, 3):
        raise PictureError("这张 BMP 用了压缩像素（类型 %d），读不了" % comp)
    if bpp not in (24, 32):
        raise PictureError("这张 BMP 是 %d 位的，只认 24 位和 32 位" % bpp)
    step = bpp // 8
    stride = ((width * bpp + 31) // 32) * 4
    out = bytearray(width * height * 4)
    for y in range(height):
        src_y = (height - 1 - y) if flip else y
        base = offset + src_y * stride
        row = body[base:base + stride]
        if len(row) < width * step:
            raise PictureError("这张图片的数据不完整，可能复制时被截断了")
        for x in range(width):
            s = x * step
            o = (y * width + x) * 4
            out[o] = row[s + 2]
            out[o + 1] = row[s + 1]
            out[o + 2] = row[s]
            out[o + 3] = row[s + 3] if step == 4 else 255
            if step == 4 and comp == 0 and out[o + 3] == 0:
                out[o + 3] = 255               # BI_RGB keeps a zero alpha byte
    return width, height, bytes(out)


def read(path):
    """-> (width, height, RGBA bytes).  Raises PictureError with a Chinese reason.

    DDS goes through `ddstex.decode`, so a picture the tool itself emitted
    (`aoe2mod.game.ddstex.encode_bgra`) can be read back pixel for pixel -- the
    two are each other's proof, the same way `decode` and `encode_bgra` already
    were.
    """
    if not os.path.isfile(path):
        raise PictureError("找不到这张图片：%s" % path)
    with open(path, "rb") as fh:
        head = fh.read(16)
    try:
        if head[:4] == b"DDS ":
            return ddstex.decode(path)
        with open(path, "rb") as fh:
            body = fh.read()
        if body[:8] == b"\x89PNG\r\n\x1a\n":
            return _read_png(body)
        if body[:2] == b"BM":
            return _read_bmp(body)
    except PictureError:
        raise
    except ValueError as exc:
        raise PictureError("这张图片读不出来：%s" % exc)
    except (struct.error, IndexError):
        raise PictureError("这张图片的数据不完整，可能下载或复制时被截断了")
    if head[:2] == b"\xff\xd8":
        try:
            from PIL import Image                    # noqa: F401
        except ImportError:
            raise PictureError("这张图片是 JPEG，这个版本读不了 JPEG；"
                               "另存成 PNG 就行（画图里「另存为」选 PNG）")
        return _read_with_pillow(path)
    raise PictureError("不是一张能识别的图片（支持 %s）" % SUPPORTED)


def _read_with_pillow(path):
    """JPEG and anything else, when the host happens to have Pillow."""
    from PIL import Image
    with Image.open(path) as im:
        im.load()
        rgba = im.convert("RGBA")
        w, h = rgba.size
        return w, h, rgba.tobytes()


def size(path):
    """-> (width, height) without decoding the pixels where the format allows.

    A preview has to answer "does this fit?" and only needs two integers;
    decoding a 4000 px photo to learn them would make planning cost as much as
    building.
    """
    if not os.path.isfile(path):
        raise PictureError("找不到这张图片：%s" % path)
    with open(path, "rb") as fh:
        head = fh.read(33)
    try:
        if head[:4] == b"DDS ":
            hd = ddstex.header(path)
            return hd["width"], hd["height"]
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            (w, h) = struct.unpack_from(">II", head, 16)
            return w, h
        if head[:2] == b"BM":
            w, h = struct.unpack_from("<ii", head, 18)
            return abs(w), abs(h)
    except (struct.error, ValueError):
        pass
    w, h, _px = read(path)
    return w, h


def fit(width, height, rgba, side):
    """Any picture -> (side, side, RGBA), letterboxed on transparent margins.

    The letterbox is deliberate and was already the rule before this module: a
    200x100 logo squashed to a square looks wrong on a square button, and
    cropping it would hide most of the picture.  Nearest-neighbour scaling is
    enough because this only ever runs on the way to a 256 px button: the
    blocking that bilinear would hide is invisible at that size, and shipping a
    resampler here would be a second thing to get wrong.
    """
    if width <= 0 or height <= 0:
        raise PictureError("这张图片是空的（%dx%d）" % (width, height))
    canvas = bytearray(side * side * 4)
    scale = min(float(side) / width, float(side) / height)
    nw = max(1, min(side, int(round(width * scale))))
    nh = max(1, min(side, int(round(height * scale))))
    off_x = (side - nw) // 2
    off_y = (side - nh) // 2
    for y in range(nh):
        sy = min(height - 1, y * height // nh)
        for x in range(nw):
            sx = min(width - 1, x * width // nw)
            s = (sy * width + sx) * 4
            o = ((off_y + y) * side + (off_x + x)) * 4
            canvas[o] = rgba[s]
            canvas[o + 1] = rgba[s + 1]
            canvas[o + 2] = rgba[s + 2]
            canvas[o + 3] = rgba[s + 3]
    return side, side, bytes(canvas)
