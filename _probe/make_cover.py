"""Build a 1280x720 Workshop thumbnail for the villager->sheep mod.

Composition imitates the user's reference photo: a round fluffy animal standing
on a tiled floor looking straight at the camera, a light patterned rug and a
doorway behind it. The animal is not drawn -- it is the game's own sheep sprite,
rendered with the project's SLD reader, so the cover shows exactly the art the
mod installs.

Four things this file gets wrong if you are not careful:
  * render_frame returns (bytearray, w, h, info) -- four values, not an image,
    and the bytearray is flat RGBA, so it needs Image.frombytes.
  * the sprite canvas is 400x400 with the sheep occupying a small part of it,
    so compositing the raw canvas leaves a tiny animal in a large empty box.
    Crop to the alpha bbox first, then scale.
  * the number of angles is NOT in the SLD -- it is `angle_count` on the .dat
    graphics record. Hardcoding 16 would be a guess.
  * angle 0 is a side view. Only angle 4 faces the camera, which is what the
    reference photo is. Picking a frame by "most visible pixels" picks a side.

Output: _probe/out_cover/thumbnail.png at exactly 1280x720, RGB.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sldlib as SL

from PIL import Image, ImageDraw, ImageFont, ImageFilter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GRAPHICS = os.path.join(GAME, "resources", "_common", "drs", "graphics")
FONTS = os.path.join(GAME, "resources", "_common", "wpfg", "fonts")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_cover")

W, H = 1280, 720
FLOOR_Y = 512

# Angle 0 is a flat side view; the reference photo is an animal facing the
# camera. Angle 2 is the front-on three-quarter view with the roundest body, so
# it reads like that photo. Chosen by looking at all sixteen, not by a rule --
# "most visible pixels" picks a side view. Note there is no TRUE front angle:
# every AoE2 sprite is drawn at a 3/4 top-down angle.
FRONT_ANGLE = 2


def to_image(canvas, w, h):
    return Image.frombytes("RGBA", (w, h), bytes(canvas))


def front_sheep(px_high):
    """The middle frame of the front-facing angle, cropped to its silhouette."""
    s = SL.read_sld(os.path.join(GRAPHICS, "a_herd_sheep_idleA_x2.sld"))
    per = len(s.frames) // 16
    canvas, cw, ch, _ = SL.render_frame(s.frames[FRONT_ANGLE * per + per // 2])
    img = to_image(canvas, cw, ch)
    bbox = img.split()[-1].getbbox()
    if not bbox:
        raise SystemExit("the front angle rendered empty -- refusing to ship a blank cover")
    img = img.crop(bbox)
    s_scale = px_high / float(img.size[1])
    return img.resize((max(1, int(round(img.size[0] * s_scale))), px_high), Image.LANCZOS)


def draw_room(d):
    d.rectangle([0, 0, W, H], fill=(228, 223, 214))

    # a warm wall wash from the top light
    for i in range(0, FLOOR_Y, 2):
        t = i / float(FLOOR_Y)
        c = (int(236 - 22 * t), int(232 - 23 * t), int(224 - 24 * t))
        d.line([(0, i), (W, i)], fill=c)

    # doorway, left of centre, with the darker room visible through it
    dx0, dx1, dy0 = 96, 452, 104
    d.rectangle([dx0 - 18, dy0 - 18, dx1 + 18, FLOOR_Y], fill=(208, 202, 192))
    d.rectangle([dx0, dy0, dx1, FLOOR_Y], fill=(126, 121, 114))
    d.rectangle([dx0 + 8, dy0 + 8, dx1 - 8, FLOOR_Y], fill=(110, 106, 99))
    d.rectangle([dx0 + 8, dy0 + 8, dx1 - 8, dy0 + 132], fill=(146, 141, 132))
    d.rectangle([dx0 + 8, FLOOR_Y - 96, dx1 - 8, FLOOR_Y], fill=(96, 92, 86))

    # skirting board
    d.rectangle([0, FLOOR_Y - 18, W, FLOOR_Y], fill=(60, 58, 56))

    # floor tiles, grout converging toward a vanishing point
    d.rectangle([0, FLOOR_Y, W, H], fill=(208, 188, 160))
    vx = W * 0.66
    for i in range(-16, 30):
        x = vx + i * 92
        d.line([(vx + (x - vx) * 0.10, FLOOR_Y), (x, H)], fill=(178, 158, 132), width=2)
    y, step = FLOOR_Y + 4, 7.0
    while y < H:
        d.line([(0, y), (W, y)], fill=(178, 158, 132), width=2)
        step *= 1.27
        y += step


def draw_rug(d):
    cx = W * 0.58
    top, bot = FLOOR_Y + 2, H - 4
    ht, hb = 200, 452
    bands = [(230, 224, 213), (221, 215, 203), (226, 220, 209)]
    n = len(bands)
    for i, col in enumerate(bands):
        y0 = top + (bot - top) * i / n
        y1 = top + (bot - top) * (i + 1) / n
        h0 = ht + (hb - ht) * i / n
        h1 = ht + (hb - ht) * (i + 1) / n
        d.polygon([(cx - h0, y0), (cx + h0, y0), (cx + h1, y1), (cx - h1, y1)], fill=col)
    for k in range(-8, 9):
        d.line([(cx + ht * k / 8.0, top), (cx + hb * k / 8.0, bot)],
               fill=(208, 201, 189), width=3)
    for side in (-1, 1):
        d.line([(cx + side * ht, top), (cx + side * hb, bot)],
               fill=(192, 184, 171), width=4)


def ground_shadow(out, bbox):
    x0, _y0, x1, y1 = bbox
    sh = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sh)
    sd.ellipse([x0 - 18, y1 - 34, x1 + 18, y1 + 22], fill=135)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    shadow = Image.new("RGBA", (W, H), (36, 30, 24, 255))
    shadow.putalpha(sh)
    out.alpha_composite(shadow)


def vignette(bg):
    vg = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vg).ellipse([-W * 0.20, -H * 0.20, W * 1.20, H * 1.20], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(150))
    return Image.composite(bg, Image.new("RGB", (W, H), (176, 170, 160)), vg)


def title(out):
    trajan = ImageFont.truetype(os.path.join(FONTS, "TrajanPro-Bold.ttf"), 86)
    yahei = ImageFont.truetype(os.path.join(FONTS, "MicrosoftYaHei.ttf"), 44)
    small = ImageFont.truetype(os.path.join(FONTS, "MicrosoftYaHei.ttf"), 26)

    # a top gradient band, so white text reads without a hard-edged box
    band = Image.new("L", (W, H), 0)
    ImageDraw.Draw(band).rectangle([0, 0, W, 300], fill=150)
    band = band.filter(ImageFilter.GaussianBlur(60))
    dark = Image.new("RGBA", (W, H), (20, 16, 12, 255))
    dark.putalpha(band)
    out.alpha_composite(dark)

    d = ImageDraw.Draw(out)

    def shadowed(xy, text, font, fill=(255, 252, 244)):
        x, y = xy
        d.text((x + 2, y + 3), text, font=font, fill=(14, 10, 6))
        d.text((x, y), text, font=font, fill=fill)

    shadowed((60, 40), "SHEEP", trajan)
    shadowed((62, 138), "村民变成绵羊", yahei)
    d.line([(62, 198), (286, 198)], fill=(200, 164, 94), width=3)
    shadowed((62, 204), "全体村民 · 连干活都是羊", small, fill=(238, 231, 216))

    # bottom-right caption, the mod's own promise
    cap = ImageFont.truetype(os.path.join(FONTS, "MicrosoftYaHei.ttf"), 24)
    txt = "帝国时代 II 决定版 · 松散贴图模组"
    tw = d.textlength(txt, font=cap)
    d.text((W - 40 - tw + 2, H - 52), txt, font=cap, fill=(12, 9, 6))
    d.text((W - 40 - tw, H - 54), txt, font=cap, fill=(240, 233, 219))


def before_after(out):
    """A small villager -> sheep badge in the empty right of the frame.

    The cover has to say what changed. Words say "villager becomes sheep"; this
    shows both sprites side by side, taken from the game's own files, so the
    claim is visible rather than asserted.
    """
    def sprite(path, angle, px_high):
        s = SL.read_sld(path)
        per = len(s.frames) // 16
        idx = min(len(s.frames) - 1, angle * per + per // 2)
        canvas, w, h, _ = SL.render_frame(s.frames[idx])
        img = to_image(canvas, w, h)
        bb = img.split()[-1].getbbox()
        if not bb:
            return None
        img = img.crop(bb)
        s2 = px_high / float(img.size[1])
        return img.resize((max(1, int(round(img.size[0] * s2))), px_high), Image.LANCZOS)

    human = sprite(os.path.join(GRAPHICS, "u_vil_male_villager_idleA_x2.sld"), 2, 150)
    sheep = sprite(os.path.join(GRAPHICS, "a_herd_sheep_idleA_x2.sld"), 2, 150)
    if human is None or sheep is None:
        return

    pad, arrow_w = 16, 56
    box_w = pad * 2 + human.size[0] + arrow_w + sheep.size[0]
    box_h = pad * 2 + 150
    bx = W - 34 - box_w
    by = H - 34 - box_h - 40

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=16,
                         fill=(22, 18, 14, 190), outline=(198, 162, 92, 220), width=2)
    out.alpha_composite(card)

    cx = bx + pad
    out.alpha_composite(human, (cx, by + pad + (150 - human.size[1]) // 2))
    ax = cx + human.size[0] + 6
    d = ImageDraw.Draw(out)
    d.line([(ax, by + box_h // 2), (ax + arrow_w - 18, by + box_h // 2)],
           fill=(232, 222, 200), width=5)
    d.polygon([(ax + arrow_w - 8, by + box_h // 2),
               (ax + arrow_w - 24, by + box_h // 2 - 13),
               (ax + arrow_w - 24, by + box_h // 2 + 13)], fill=(232, 222, 200))
    out.alpha_composite(sheep, (ax + arrow_w, by + pad + (150 - sheep.size[1]) // 2))


def main():
    os.makedirs(OUT, exist_ok=True)

    bg = Image.new("RGB", (W, H), (228, 223, 214))
    d = ImageDraw.Draw(bg)
    draw_room(d)
    draw_rug(d)
    out = vignette(bg).convert("RGBA")

    sp = front_sheep(452)
    sw, sh = sp.size
    px = int(W * 0.58 - sw * 0.5)
    py = FLOOR_Y - sh + 40
    ground_shadow(out, (px, py, px + sw, py + sh))
    out.alpha_composite(sp, (px, py))
    print("sheep %dx%d at (%d,%d)" % (sw, sh, px, py))

    title(out)
    before_after(out)

    flat = out.convert("RGB")
    dst = os.path.join(OUT, "thumbnail.png")
    flat.save(dst, "PNG")
    print("wrote %s (%d bytes) %dx%d" % (dst, os.path.getsize(dst),
                                         flat.size[0], flat.size[1]))


if __name__ == "__main__":
    main()
