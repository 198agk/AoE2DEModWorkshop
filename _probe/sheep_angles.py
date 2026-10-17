"""Survey the 16 angles of the sheep idle sprite: which one looks front-on?"""
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

def angle_count_of(rec_file):
    """The engine's own angle count comes from the graphics record, not the SLD.

    An SLD carries num_frames only; how those frames divide into angles lives in
    the .dat graphics record.  Hardcoding 16 would be a guess, and a wrong guess
    indexes the wrong picture rather than failing.
    """
    import aoe2mod.api as A
    tk = A.open_toolkit()
    tk._ensure()
    for g in tk._stats["graphics"]:
        if g.get("file") == rec_file:
            return g.get("angle_count"), g.get("frame_count")
    raise SystemExit("no graphics record names %r" % rec_file)


def main():
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(GRAPHICS, "a_herd_sheep_idleA_x2.sld")
    s = SL.read_sld(p)
    n = len(s.frames)
    angles, frames = angle_count_of("a_herd_sheep_idleA_x1")
    print("sld frames %d; record angle_count %s frame_count %s" % (n, angles, frames))
    per = n // angles
    print("frames per angle %d" % per)
    tiles = []
    for a in range(angles):
        idx = a * per + per // 2
        canvas, w, h, _ = SL.render_frame(s.frames[idx])
        img = to_image(canvas, w, h)
        bb = img.split()[-1].getbbox()
        img = img.crop(bb) if bb else img
        tiles.append((a, img))

    cw = max(t.size[0] for _, t in tiles) + 16
    ch = max(t.size[1] for _, t in tiles) + 30
    cols = 8
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (28, 30, 34, 255))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(os.path.join(FONTS, "SegoeUI.ttf"), 16)
    for i, (a, t) in enumerate(tiles):
        cx = (i % cols) * cw
        cy = (i // cols) * ch
        sheet.alpha_composite(t, (cx + (cw - t.size[0]) // 2, cy + 24))
        d.text((cx + 6, cy + 4), "angle %d" % a, font=font, fill=(240, 236, 226))
    dst = os.path.join(OUT, "angles.png")
    sheet.convert("RGB").save(dst, "PNG")
    print("wrote %s %s" % (dst, sheet.size))

if __name__ == "__main__":
    main()
