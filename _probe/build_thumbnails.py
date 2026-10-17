"""Build the 1280x720 workshop thumbnails for v12 (copy) and v13 (rename).

Every published mod on this install ships a 1280x720 RGB thumbnail, and the
publish screen refuses with `IDS_MODMGR_ERROR_THUMBNAIL "Missing Thumbnail"`
without one.  The picture here is the actual before/after art, rendered from the
shipped .sld files by the same reader the reskin uses -- not a mockup, so nobody
can publish a thumbnail that promises something the mod does not do.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.game.sld as SL               # noqa: E402
import aoe2mod.game.sprites as SP           # noqa: E402

W, H = 1280, 720
SHOTS = os.path.join(os.path.dirname(HERE), "_shots", "workshop")
FONT_DIR = os.path.join("C:", os.sep, "Windows", "Fonts")


def _font(size, bold=False):
    for name in (("msyhbd.ttc" if bold else "msyh.ttc"), "simhei.ttf",
                 "segoeui.ttf", "arial.ttf"):
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def best_frame(path):
    """The first frame that actually has pixels (frame 0 is often empty).

    ``render_frame`` returns a flat RGBA ``bytearray``, not a PIL image, so the
    opacity count indexes it directly.
    """
    sld = SL.read_sld(path)
    best, best_n = None, -1
    for fr in sld.frames[:80]:
        canvas, w, h, _info = SL.render_frame(fr)
        n = sum(1 for i in range(3, len(canvas), 4) if canvas[i] > 8)
        if n > best_n:
            best, best_n = (canvas, w, h), n
            if n > 4000:
                break
    return best


def scaled(img, w, h):
    iw, ih = img.size
    k = min(w / iw, h / ih)
    return img.resize((max(1, int(iw * k)), max(1, int(ih * k))), Image.LANCZOS)


def crop_to_art(img, pad=6):
    """Trim the empty canvas around the sprite before blowing it up.

    A unit's frame is a 60x80-ish canvas with the body occupying a fraction of
    it, so pasting the canvas whole leaves the subject too small to see -- the
    first version of this thumbnail had a villager about 40 pixels tall.
    """
    bbox = img.getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    return img.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(img.size[0], x1 + pad), min(img.size[1], y1 + pad)))


def fit_into(img, w, h):
    """Scale so the subject FILLS the cell, keeping pixels chunky-nearest."""
    iw, ih = img.size
    k = min(w / iw, h / ih)
    return img.resize((max(1, int(iw * k)), max(1, int(ih * k))),
                      Image.NEAREST)


def build(tk, title, subtitle, before_rel, after_rel, out_path):
    bg = Image.new("RGB", (W, H), (26, 24, 22))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(30 + 16 * k), int(28 + 14 * k),
                                       int(26 + 12 * k)))
    gdir = SP.graphics_dir(tk.game_root)
    cell_w, cell_h = 520, 430
    panels = []
    for rel, label in ((before_rel, "替换前"), (after_rel, "替换后")):
        canvas, w, h = best_frame(os.path.join(gdir, rel + ".sld"))
        img = Image.frombytes("RGBA", (w, h), bytes(canvas))
        img = fit_into(crop_to_art(img), cell_w, cell_h)
        panels.append((img, label))

    f_title = _font(46, bold=True)
    f_label = _font(30, bold=True)
    f_sub = _font(24)
    x0 = 80
    for i, (img, label) in enumerate(panels):
        cx = x0 + i * (cell_w + 80) + (cell_w - img.size[0]) // 2
        cy = 190 + (cell_h - img.size[1]) // 2
        # a soft plate so the sprite separates from the background
        d.rounded_rectangle([x0 + i * (cell_w + 80) - 16, 170,
                             x0 + i * (cell_w + 80) + cell_w + 16,
                             170 + cell_h + 20], radius=14,
                            fill=(44, 41, 37))
        bg.paste(img, (cx, cy), img)
        d.text((x0 + i * (cell_w + 80) + cell_w // 2, 130), label,
               font=f_label, fill=(228, 214, 190), anchor="mm")

    d.text((W // 2, 58), title, font=f_title, fill=(245, 233, 210), anchor="mm")
    d.text((W // 2, H - 74), subtitle, font=f_sub, fill=(186, 176, 160),
           anchor="mm")
    bg.save(out_path, "PNG")
    print("wrote %s (%dx%d, %d B)"
          % (out_path, W, H, os.path.getsize(out_path)))
    return out_path


def main():
    os.makedirs(SHOTS, exist_ok=True)
    tk = A.open_toolkit()
    tk._ensure()
    v12 = os.path.join(HERE, "out_dshtest_v12", "thumbnail.png")
    v13 = os.path.join(HERE, "out_dshtest_v13", "thumbnail.png")
    build(tk, "村民变成绵羊",
          "替换 466 个动画文件（复制贴图）· 不含 .dat · 可与任何数据模组共存",
          "u_vil_male_villager_idleA_x1", "a_herd_sheep_idleA_x1", v12)
    build(tk, "村民变成绵羊（轻量版）",
          "改写 244 条图形记录（不复制贴图）· 11 MB · 是数据模组，一局只能启用一个",
          "u_vil_male_villager_idleA_x1", "a_herd_sheep_idleA_x1", v13)
    return 0


if __name__ == "__main__":
    sys.exit(main())
