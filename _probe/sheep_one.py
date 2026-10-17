"""Render a couple of candidate angles large, so the face can be judged."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sldlib as SL
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GRAPHICS = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_cover")


def to_image(canvas, w, h):
    return Image.frombytes("RGBA", (w, h), bytes(canvas))


def main():
    os.makedirs(OUT, exist_ok=True)
    s = SL.read_sld(os.path.join(GRAPHICS, "a_herd_sheep_idleA_x2.sld"))
    per = len(s.frames) // 16
    for a in (4, 12, 0):
        canvas, w, h, _ = SL.render_frame(s.frames[a * per + per // 2])
        img = to_image(canvas, w, h)
        bb = img.split()[-1].getbbox()
        img = img.crop(bb)
        img = img.resize((img.size[0] * 3, img.size[1] * 3), Image.LANCZOS)
        dst = os.path.join(OUT, "angle_%02d.png" % a)
        img.save(dst, "PNG")
        print("angle %d -> %s %s" % (a, dst, img.size))


if __name__ == "__main__":
    main()
