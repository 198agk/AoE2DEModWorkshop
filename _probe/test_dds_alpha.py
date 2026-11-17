# -*- coding: utf-8 -*-
"""Pin the BC3/DXT5 alpha channel against a spec-faithful reference decoder.

Why this suite exists
---------------------
On 2026-11-05 the owner reported "some icons are still ghosts".  Measured over
the editor's 400 list rows, 17 of them had not one opaque pixel: every pixel sat
between 1 and 254 alpha, so a fully painted longbowman faded into the list
background.  Forcing alpha to 255 restored each one to full colour, which put the
blame on the alpha channel rather than on the artwork.

The cause was in `aoe2mod/game/ddstex.py`: DXT3 (BC2) and DXT5 (BC3) share a
16-byte block size, and the decoder treated "block == 16" as one thing, so every
BC3 icon had its alpha read as sixteen 4-bit explicit values (the DXT3 rule)
instead of two endpoint bytes plus sixteen 3-bit indices.  The Rust mirror in
`desktop/aoe2mod-serve/src/ddstex.rs` said "the Python implementation is the
reference" and carried the identical bug, so the two agreed with each other and
both were wrong -- `test_dds_parity.py` was green the whole time.

What is checked
---------------
1. The palette arithmetic, on blocks whose answer is known by hand.
2. Every BC3 texture the game ships, against a second decoder written here from
   the format description (endpoints, 7-step or 5-step interpolation, 3-bit
   indices).  Pixel for pixel, not "the PNG opens".
3. The 17 icons the owner saw, plus the whole editor list, must have opaque
   pixels.  This is the shape of the complaint, so it is the shape of the check.

Runtime: about 10 s (353 textures, 256x256 each).
"""
import os
import _gamepaths as GP
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import ddstex as D          # noqa: E402
from aoe2mod.game import icons as I          # noqa: E402

GAME = GP.GAME
TEX = os.path.join(GAME, "widgetui", "textures", "ingame")

OK = [0]
FAILED = []


def check(name, cond, detail=""):
    if cond:
        OK[0] += 1
        print("  ok   %s" % name)
    else:
        FAILED.append(name)
        print("  FAIL %s%s" % (name, (" :: " + str(detail)) if detail else ""))


def reference_table(a0, a1):
    """The BC3 palette, written from the format description rather than reused."""
    if a0 > a1:
        steps = [(a0, 0), (a1, 1)] + [(((7 - k) * a0 + k * a1) // 7, k + 1)
                                      for k in range(1, 7)]
    else:
        steps = ([(a0, 0), (a1, 1)]
                 + [(((5 - k) * a0 + k * a1) // 5, k + 1) for k in range(1, 5)])
        steps += [(0, 6), (255, 7)]
    table = [0] * 8
    for value, index in steps:
        table[index] = value
    return table


def reference_alpha(path):
    """Decode only the alpha plane, from the block layout, with no shared code."""
    hd = D.header(path)
    w, h = hd["width"], hd["height"]
    with open(path, "rb") as fh:
        fh.seek(hd["data_offset"])
        body = fh.read()
    bw, bh = (w + 3) // 4, (h + 3) // 4
    out = bytearray(w * h)
    pos = 0
    for by in range(bh):
        for bx in range(bw):
            blk = body[pos:pos + 16]
            pos += 16
            table = reference_table(blk[0], blk[1])
            bits = int.from_bytes(blk[2:8], "little")
            for py in range(4):
                y = by * 4 + py
                if y >= h:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x >= w:
                        continue
                    out[y * w + x] = table[(bits >> (3 * (py * 4 + px))) & 7]
    return w, h, bytes(out)


def bc3_files(limit=None):
    seen, out = set(), []
    for base, _dirs, files in os.walk(TEX):
        for f in sorted(files):
            if not f.lower().endswith(".dds"):
                continue
            p = os.path.join(base, f)
            try:
                hd = D.header(p)
            except Exception:
                continue
            fmt = hd["fourcc"]
            if fmt == "DX10" and hd["dx10_format"] == D._DX10_BC3:
                fmt = "DXT5"
            if fmt in ("DXT5", "DXT4", "BC3"):
                if p not in seen:
                    seen.add(p)
                    out.append(p)
                if limit and len(out) >= limit:
                    return out
    return out


def main():
    print("-- the palette, on blocks whose answer is known by hand")
    # a0 > a1: six steps of 7ths between a0 and a1, endpoints keep their bytes.
    t = reference_table(255, 0)
    check("a0 > a1 keeps both endpoints", (t[0], t[1]) == (255, 0), t[:2])
    check("a0 > a1 puts 218 at index 2", t[2] == 218, t[2])
    check("a0 > a1 walks down to 36 at index 7", t[7] == 36, t[7])
    # The endpoint bytes themselves are 255 and 0 here, so 0 in the palette is
    # not evidence of the hard pair; the hard pair is index 6 being 0 *and*
    # index 7 being 255 in the a0 <= a1 shape.  Assert the shapes, not the values.
    t = reference_table(200, 40)
    check("a0 > a1 is monotonically between the endpoints",
          all(40 <= v <= 200 for v in t), t)
    # a0 <= a1: five steps of 5ths from a0 toward a1, then the hard 0 and 255.
    t = reference_table(0, 200)
    check("a0 <= a1 ends with the hard 0 and 255", (t[6], t[7]) == (0, 255), t[6:])
    check("a0 <= a1 puts 40 at index 2 (a fifth of the way)", t[2] == 40, t[2])
    check("a0 <= a1 puts 160 at index 5 (four fifths of the way)", t[5] == 160, t[5])
    check("the shipped decoder agrees with the reference table",
          list(D._bc3_alpha_table(255, 0)) == list(reference_table(255, 0))
          and list(D._bc3_alpha_table(0, 200)) == list(reference_table(0, 200)),
          (D._bc3_alpha_table(255, 0), D._bc3_alpha_table(0, 200)))

    print()
    print("-- every BC3 texture the game ships")
    files = bc3_files()
    check("the shipped textures include BC3 files at all", len(files) > 300,
          "%d found" % len(files))
    worst = (None, 0, 0)
    mismatched = []
    for p in files:
        w, h, rgba = D.decode(p)
        rw, rh, ref = reference_alpha(p)
        if (w, h) != (rw, rh):
            mismatched.append((os.path.basename(p), "size", (w, h), (rw, rh)))
            continue
        same = sum(1 for a, b in zip(rgba[3::4], ref) if a == b)
        if same != len(ref):
            mismatched.append((os.path.basename(p), "%d/%d" % (same, len(ref)),
                               None, None))
        if len(ref) and (same / len(ref)) < worst[1] or worst[0] is None:
            worst = (os.path.basename(p), same / max(1, len(ref)), len(ref))
    check("the decoder's alpha matches the reference on every BC3 texture",
          not mismatched, mismatched[:4])
    check("the worst file still matches every pixel",
          worst[0] is not None and worst[1] == 1.0,
          "%s %.4f of %d" % worst)

    print()
    print("-- the shape of the complaint: no icon may be entirely translucent")
    editor_rows = []
    try:
        book = I.IconBook(GAME)
        for icon_id in range(1, 500):
            got = book.picture("Units", icon_id)
            if got.get("ok"):
                editor_rows.append((icon_id, got["path"]))
    except Exception as exc:                   # icons.json missing: skip, not fail
        print("  ..  icon book unavailable: %s" % exc)
    seen = set()
    translucent = []
    for icon_id, path in editor_rows:
        if path in seen:
            continue
        seen.add(path)
        try:
            _w, _h, rgba = D.decode(path)
        except Exception:
            continue
        alpha = rgba[3::4]
        opaque = sum(1 for v in alpha if v > 200)
        if opaque == 0:
            translucent.append((icon_id, os.path.basename(path)))
    check("no unit icon decodes to an entirely see-through picture",
          not translucent, translucent[:5])
    check("the unit icon table was actually walked", len(seen) > 100,
          "%d files" % len(seen))

    # The seventeen the owner saw.  Named, because a number that regresses is
    # only useful if the next reader can find the icons behind it.
    ghosts = {8: "长弓兵", 232: "靛蓝突袭者", 426: "哈拉尔·哈德拉达",
              530: "精锐长弓兵", 531: "精锐掷斧兵", 533: "精锐维京长船",
              534: "精锐靛蓝突袭者", 553: "精锐甲胄骑兵", 554: "精锐条顿骑士",
              555: "精锐近卫军", 556: "精锐马穆鲁克", 557: "精锐苏丹亲兵",
              558: "精锐战象", 559: "精锐诸葛弩", 560: "精锐日本武士",
              561: "精锐蒙古突骑", 624: "大帐篷 A"}
    still = []
    book = None
    try:
        book = I.IconBook(GAME)
    except Exception:
        pass
    for icon_id, name in sorted(ghosts.items()):
        path = dict(editor_rows).get(icon_id)
        if path is None and book is not None:
            for section in ("Units", "Buildings"):
                got = book.picture(section, icon_id)
                if got.get("ok"):
                    path = got["path"]
                    break
        if path is None:
            still.append((icon_id, name, "no picture"))
            continue
        _w, _h, rgba = D.decode(path)
        alpha = rgba[3::4]
        fraction = sum(1 for v in alpha if v > 200) / float(len(alpha))
        if fraction < 0.5:
            still.append((icon_id, name, "%.2f opaque" % fraction))
    check("every icon the owner called a ghost is now mostly opaque",
          not still, still[:5])

    print()
    if FAILED:
        print("DDS ALPHA: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("DDS ALPHA: %d CHECKS PASSED -- BC3 alpha is the endpoint-plus-index "
          "format, on every texture the game ships and on every icon that used "
          "to be a ghost" % OK[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
