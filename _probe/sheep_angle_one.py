"""Render one angle of the sheep idle sprite at 5x, for a close look."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sldlib as SL
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GRAPHICS = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_cover")

ANGLE = int(sys.argv[1]) if len(sys.argv) > 1 else 12


def to_image(canvas, w, h):
    return Image.frombytes("RGBA", (w, h), bytes(canvas))


def main():
    os.makedirs(OUT, exist_ok=True)
    s = SL.read_sld(os.path.join(GRAPHICS, "a_herd_sheep_idleA_x2.sld"))
    per = len(s.frames) // 16
    canvas, w, h, _ = SL.render_frame(s.frames[ANGLE * per + per // 2])
    img = to_image(canvas, w, h)
    bb = img.split()[-1].getbbox()
    img = img.crop(bb)
    img = img.resize((img.size[0] * 5, img.size[1] * 5), Image.LANCZOS)
    # flat background so the silhouette is legible
    flat = Image.new("RGB", img.size, (238, 234, 224))
    flat.paste(img, (0, 0), img)
    dst = os.path.join(OUT, "one_%02d.png" % ANGLE)
    flat.save(dst, "PNG")
    print("angle %d -> %s %s" % (ANGLE, dst, flat.size))


if __name__ == "__main__":
    main()
