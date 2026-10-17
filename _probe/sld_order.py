"""Decide whether an SLD stores frames ANGLE-major or FRAME-major.

Both layouts fit the same frame count, so the count cannot tell you. The
decisive test: render frames 0..15. Under an angle-major layout those are
sixteen successive moments of ONE angle (near-identical). Under a frame-major
layout they are sixteen DIFFERENT angles of one moment (wildly different).

Getting this wrong does not raise -- it silently renders a scrambled animal,
which is exactly what a first attempt at a front-facing cover produced.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sldlib as SL
from PIL import Image, ImageDraw, ImageFont

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GRAPHICS = os.path.join(GAME, "resources", "_common", "drs", "graphics")
FONTS = os.path.join(GAME, "resources", "_common", "wpfg", "fonts")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_cover")


def to_image(canvas, w, h):
    return Image.frombytes("RGBA", (w, h), bytes(canvas))


def main():
    os.makedirs(OUT, exist_ok=True)
    s = SL.read_sld(os.path.join(GRAPHICS, "a_herd_sheep_idleA_x2.sld"))
    print("frames %d" % len(s.frames))

    tiles = []
    for i in range(16):
        canvas, w, h, _ = SL.render_frame(s.frames[i])
        img = to_image(canvas, w, h)
        bb = img.split()[-1].getbbox()
        img = img.crop(bb) if bb else img
        img = img.resize((img.size[0] * 3, img.size[1] * 3), Image.LANCZOS)
        tiles.append((i, img))
        print("frame %2d crop %s" % (i, img.size))

    cw = max(t.size[0] for _, t in tiles) + 20
    ch = max(t.size[1] for _, t in tiles) + 34
    sheet = Image.new("RGBA", (8 * cw, 2 * ch), (26, 28, 32, 255))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(os.path.join(FONTS, "SegoeUI.ttf"), 18)
    for i, (n, t) in enumerate(tiles):
        cx, cy = (i % 8) * cw, (i // 8) * ch
        sheet.alpha_composite(t, (cx + (cw - t.size[0]) // 2, cy + 34 + (ch - 34 - t.size[1])))
        d.text((cx + 8, cy + 6), "f%d" % n, font=font, fill=(240, 236, 226))
    dst = os.path.join(OUT, "frame_order.png")
    sheet.convert("RGB").save(dst, "PNG")
    print("wrote %s %s" % (dst, sheet.size))


if __name__ == "__main__":
    main()
