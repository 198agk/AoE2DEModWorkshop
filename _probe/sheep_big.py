"""Render candidate angles large in one sheet, to pick the most photo-like pose."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sldlib as SL
from PIL import Image, ImageDraw, ImageFont

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GRAPHICS = os.path.join(GAME, "resources", "_common", "drs", "graphics")
FONTS = os.path.join(GAME, "resources", "_common", "wpfg", "fonts")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_cover")
PICK = (2, 3, 5, 11, 12, 13, 14, 1)


def to_image(canvas, w, h):
    return Image.frombytes("RGBA", (w, h), bytes(canvas))


def main():
    os.makedirs(OUT, exist_ok=True)
    s = SL.read_sld(os.path.join(GRAPHICS, "a_herd_sheep_idleA_x2.sld"))
    per = len(s.frames) // 16
    tiles = []
    for a in PICK:
        canvas, w, h, _ = SL.render_frame(s.frames[a * per + per // 2])
        img = to_image(canvas, w, h)
        bb = img.split()[-1].getbbox()
        img = img.crop(bb) if bb else img
        img = img.resize((img.size[0] * 4, img.size[1] * 4), Image.LANCZOS)
        tiles.append((a, img))
        print("angle %2d crop %s" % (a, img.size))

    cw = max(t.size[0] for _, t in tiles) + 24
    ch = max(t.size[1] for _, t in tiles) + 40
    sheet = Image.new("RGBA", (len(tiles) * cw, ch), (26, 28, 32, 255))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(os.path.join(FONTS, "SegoeUI.ttf"), 22)
    for i, (a, t) in enumerate(tiles):
        cx = i * cw
        sheet.alpha_composite(t, (cx + (cw - t.size[0]) // 2, 40 + (ch - 40 - t.size[1])))
        d.text((cx + 10, 8), "angle %d" % a, font=font, fill=(240, 236, 226))
    dst = os.path.join(OUT, "angles_big.png")
    sheet.convert("RGB").save(dst, "PNG")
    print("wrote %s %s" % (dst, sheet.size))


if __name__ == "__main__":
    main()
