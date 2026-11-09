# -*- coding: utf-8 -*-
"""The picture reader works on a machine with NO Pillow.

WHY THIS EXISTS
---------------
`aoe2mod/game/picture.py` is a purely standard-library PNG/BMP/DDS reader,
written because the SHIPPED bundle has no Pillow: `_build/aoe2mod.spec:88`
excludes `PIL` from the frozen build.  A picture swap that worked in the
repository and failed in the exe would be the exact class of defect this project
keeps paying for (see `test_bundle_package_sync`), so the reader must be proved
without Pillow present.

HOW THE PROOF IS DONE
---------------------
A `meta_path` hook that raises ImportError for anything named PIL or Pillow is
installed BEFORE the module is imported, so a stray `import PIL` anywhere in the
picture path fails the suite instead of silently succeeding on the developer's
machine, which has Pillow 13.

The fixtures are hand-built and ASYMMETRIC on purpose.  The first version of this
reader had `sample(x, c)` ignore the row offset, so every row read row 0; on a
symmetric test image that bug is invisible.  A 4x4 image whose rows are four
different colours caught it immediately, and the fixtures here are the same shape.
"""
import os
import shutil
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

TMP = os.path.join(os.environ.get("TEMP") or "/tmp", "aoe2mod-picture-test")
FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def eq(label, got, want):
    return check("%s :: %r" % (label, want) if got != want else label,
                 got == want, "" if got == want else "got %r" % (got,))


class _NoPillow(object):
    """Make `import PIL` fail, so the standard-library path is the only path."""

    def find_module(self, name, path=None):
        return self if name.split(".")[0].upper() in ("PIL", "PILLOW") else None

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0].upper() in ("PIL", "PILLOW"):
            raise ImportError("PIL is blocked for this test")
        return None

    def load_module(self, name):                       # pragma: no cover
        raise ImportError("PIL is blocked for this test")


def png_bytes(width, height, rows):
    """A PNG whose row y is `rows[y]` (an (r,g,b,a) tuple).  No PIL involved."""
    raw = b""
    for y in range(height):
        raw += b"\x00"                       # filter type 0 for every scanline
        raw += bytes(rows[y]) * width
    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def bmp_bytes(width, height, rows):
    """A 24-bit BMP whose row y is `rows[y]`.  Stored bottom-up, like the format."""
    stride = (width * 3 + 3) // 4 * 4
    pix = b""
    for y in range(height - 1, -1, -1):      # BMP rows run bottom-up
        r, g, b, _a = rows[y]
        line = (bytes((b, g, r)) * width)
        pix += line + b"\x00" * (stride - len(line))
    hdr = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0,
                      len(pix), 2835, 2835, 0, 0)
    return b"BM" + struct.pack("<IHHI", 14 + 40 + len(pix), 0, 0, 54) + hdr + pix


def main():
    install = _NoPillow()
    sys.meta_path.insert(0, install)
    try:
        from aoe2mod.game import picture as P
    finally:
        pass
    check("the module imports with Pillow blocked", P is not None)

    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)

    # Four DIFFERENT rows.  A reader that ignores the row offset returns row 0
    # four times, which is the bug this shape exists to catch.
    ROWS = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 128)]

    print("\n=== 1. PNG: 8-bit RGBA, four asymmetric rows ===")
    p = os.path.join(TMP, "four.png")
    open(p, "wb").write(png_bytes(4, 4, ROWS))
    w, h, rgba = P.read(p)
    eq("the width is read", w, 4)
    eq("the height is read", h, 4)
    eq("the buffer is RGBA", len(rgba), 4 * 4 * 4)
    for y in range(4):
        got = [tuple(rgba[((y * 4 + x) * 4):((y * 4 + x) * 4) + 4]) for x in range(4)]
        check("row %d is its own colour, not row 0" % y,
              all(g == ROWS[y] for g in got), str(got[:2]))

    print("\n=== 2. size() reads the header without decoding ===")
    eq("size answers two integers", P.size(p), (4, 4))

    print("\n=== 3. BMP: 24-bit, stored bottom-up ===")
    b = os.path.join(TMP, "four.bmp")
    open(b, "wb").write(bmp_bytes(4, 4, ROWS))
    w, h, rgba = P.read(b)
    eq("the width is read", w, 4)
    eq("the height is read", h, 4)
    top = tuple(rgba[0:4])
    eq("the TOP row is the first row of the file's visual order", top, ROWS[0])
    # A 24-bit BMP has no alpha channel at all, so the fourth row comes back
    # fully opaque.  Asserting the fixture's 128 here would be asserting a
    # channel the format does not carry; the RGB is what must survive.
    bottom = tuple(rgba[(3 * 4) * 4:(3 * 4) * 4 + 4])
    eq("and the bottom row is the fourth, with alpha filled in",
       bottom, ROWS[3][:3] + (255,))
    eq("BMP size() agrees", P.size(b), (4, 4))

    print("\n=== 4. DDS goes through the same decoder the game uses ===")
    from aoe2mod.game import ddstex
    d = os.path.join(TMP, "four.dds")
    body = bytearray()
    for y in range(4):
        for x in range(4):
            r, g, bl, a = ROWS[y]
            body += bytes((r, g, bl, a))
    # `encode_bgra` hands back the bytes of a whole DDS rather than writing a
    # file; the two functions are each other's proof.
    open(d, "wb").write(ddstex.encode_bgra(4, 4, bytes(body)))
    w, h, rgba = P.read(d)
    eq("the DDS width is read", w, 4)
    eq("the DDS height is read", h, 4)
    eq("and its first pixel survives the round trip", tuple(rgba[0:4]), ROWS[0])
    eq("DDS size() agrees", P.size(d), (4, 4))

    print("\n=== 5. fit() letterboxes instead of squashing or cropping ===")
    wide = os.path.join(TMP, "wide.png")
    open(wide, "wb").write(png_bytes(8, 2, [(10, 20, 30, 255), (40, 50, 60, 255)]))
    w, h, rgba = P.read(wide)
    side = 16
    sw, sh, sq = P.fit(w, h, rgba, side)
    eq("the square canvas is square", (sw, sh), (side, side))
    eq("the canvas has one RGBA per pixel", len(sq), side * side * 4)
    # An 8x2 picture scaled into 16x16 is 16x4 with 6 transparent rows above and
    # below: cropping it would hide most of the logo, and squashing it to 16x16
    # would look wrong on a square button.
    top = tuple(sq[0:4])
    eq("the top margin is transparent", top, (0, 0, 0, 0))
    mid_row = side // 2
    mid = tuple(sq[(mid_row * side) * 4:(mid_row * side) * 4 + 4])
    check("and the picture's own colour is in the middle", mid[3] > 0, str(mid))

    print("\n=== 6. failures are Chinese sentences, not tracebacks ===")
    miss = os.path.join(TMP, "not-here.png")
    try:
        P.read(miss)
        check("a missing file raises", False)
    except P.PictureError as exc:
        check("a missing file says so in Chinese",
              u"\u627e\u4e0d\u5230" in str(exc), str(exc))
    junk = os.path.join(TMP, "junk.png")
    open(junk, "wb").write(b"not a picture at all")
    try:
        P.read(junk)
        check("junk raises", False)
    except P.PictureError as exc:
        check("junk says what IS supported",
              "PNG" in str(exc) or "BMP" in str(exc), str(exc))

    print("\n=== 7. a JPEG is refused by name when Pillow is absent ===")
    jp = os.path.join(TMP, "a.jpg")
    open(jp, "wb").write(b"\xff\xd8\xff\xe0" + b"\x00" * 40)
    try:
        P.read(jp)
        check("a JPEG raises without Pillow", False)
    except P.PictureError as exc:
        check("and it names the format and the way out",
              "JPEG" in str(exc) and "PNG" in str(exc), str(exc))

    sys.meta_path.remove(install)
    shutil.rmtree(TMP, ignore_errors=True)
    print()
    if FAILS:
        print("PICTURE FORMATS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("PICTURE FORMATS: PNG/BMP/DDS READ WITHOUT PILLOW, FOUR ASYMMETRIC "
          "ROWS PROVE THE ROW OFFSET IS REAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
