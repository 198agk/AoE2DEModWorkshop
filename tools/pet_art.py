"""Turn the flat-green pose renders into the alpha PNGs the pet shows.

Why this exists: the ten poses under `_probe/_tmp/pose_src/` are drawn on a
chroma-key backdrop, not on transparency.  Doing the key by hand once would
leave the next person with a folder of green pictures and no record of how the
edges were trimmed, so the step is a script.

Run:  python -X utf8 tools/pet_art.py
Out:  aoe2mod/ui/static/art/pet/*.png  (one per pose, 220 px tall)
Src:  _probe/_tmp/pose_src/pose_<name>.png, straight from the renderer
"""
import colorsys
import os
import shutil

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "_probe", "_tmp", "pose_src")
DST = os.path.join(HERE, "aoe2mod", "ui", "static", "art", "pet")

TALL = 220          # display box tops out near 200 px; 220 keeps the scale honest
# Every picture is pasted onto a canvas this wide, instead of being cropped to
# its own outline.  The page shows them all in one box with `object-fit:
# contain`, so a drawing that happens to be narrower would render smaller and
# the character would visibly change build when she switches pose.
CANVAS_W = 128      # 128/220 matches the 84x144 and 56x96 boxes exactly

# source stem -> file the page asks for
POSES = {
    "pose_idle": "idle",
    "pose_think": "think",
    "pose_happy": "happy",
    "pose_sad": "sad",
    "pose_sleep": "sleep",
    "pose_approval": "approval",
    "pose_edit": "edit",
    "pose_sing": "sing",
    # Kept for the left/right facing swap even though nothing switches to them
    # yet: redrawing a profile later is the expensive half of that work.
    # Facing swaps and idle variety.  side/back were drawn before anything used
    # them; wave/eat/pat/look/walk now give the idle loop something to pick from
    # so the same picture is not on screen for an hour.
    "pose_side": "side",
    "pose_back": "back",
    "pose_wave": "wave",
    "pose_eat": "eat",
    "pose_pat": "pat",
    "pose_look": "look",
    "pose_walk1": "walk1",
    "pose_walk2": "walk2",
}


def is_green(r, g, b):
    """A pixel belongs to the backdrop when it is green-dominant and saturated.

    Hue alone is not enough: the white apron and the pale skin both pick up a
    green cast where they meet the backdrop, and those must stay.
    """
    hue, _light, sat = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return 0.20 <= hue <= 0.46 and sat >= 0.22 and g > r + 10 and g > b + 10


def key(im):
    im = im.convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if is_green(r, g, b):
                px[x, y] = (0, 0, 0, 0)
                continue
            hue, _light, sat = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
            # Fringe: still greenish but no longer pure backdrop.  Cap the green
            # channel at the larger of red and blue, which is what the eye reads
            # as "not green" without turning the edge grey.
            if 0.18 <= hue <= 0.48 and sat >= 0.14 and g > max(r, b):
                px[x, y] = (r, min(g, max(r, b) + 4), b, a)
    # One pixel of erosion kills the half-transparent green rim the key leaves.
    im.putalpha(im.split()[3].filter(ImageFilter.MinFilter(3)))
    return im


def fit(im, tall=TALL):
    box = im.split()[3].getbbox()
    if box:
        im = im.crop(box)
    wide = max(1, round(im.width * tall / im.height))
    im = im.resize((wide, tall), Image.LANCZOS)
    if wide > CANVAS_W:
        # Wider than the shared canvas: keep her feet centred and let the
        # sides fall off, rather than shrink the whole cast to fit one pose.
        left = (wide - CANVAS_W) // 2
        return im.crop((left, 0, left + CANVAS_W, tall))
    canvas = Image.new("RGBA", (CANVAS_W, tall), (0, 0, 0, 0))
    canvas.paste(im, ((CANVAS_W - wide) // 2, 0))
    return canvas


def main():
    if not os.path.isdir(SRC):
        raise SystemExit("pose sources missing: " + SRC)
    os.makedirs(DST, exist_ok=True)
    total = 0
    for stem, name in sorted(POSES.items()):
        src = os.path.join(SRC, stem + ".png")
        if not os.path.exists(src):
            print("skip (no source):", stem)
            continue
        out = os.path.join(DST, name + ".png")
        im = fit(key(Image.open(src)))
        im.save(out, optimize=True)
        size = os.path.getsize(out)
        total += size
        print("%-16s -> %-12s %-9s %6d B" % (stem, name + ".png", "%dx%d" % im.size, size))
    print("total %d bytes, %d poses" % (total, len(POSES)))


if __name__ == "__main__":
    main()
