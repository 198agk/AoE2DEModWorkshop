# -*- coding: utf-8 -*-
"""Paint a user's picture onto a unit's existing animations.

WHY THIS IS THE SHAPE IT IS
---------------------------
An `.sld` cannot be built from scratch: every frame that carries a `main` layer
also carries an `unknown2` layer (4,737,215 frames, zero exceptions across the
shipped corpus), and `unknown2`'s size is not a function of main's run list, so
it cannot be regenerated.  What CAN be done -- and what this module does -- is
repaint the BC1 blocks of `main` in place, keeping every other byte.

A PICTURE IS TRIMMED, THEN SIZED ONCE FOR THE WHOLE FILE
-------------------------------------------------------
Two things happen before a single pixel is written.  The picture is trimmed to
its own opaque box, because a 1,024 px export with 300 px of padding is a 400 px
drawing and scaling the padding would shrink the drawing to keep the emptiness.
Then ONE scale is chosen for the whole file, and the picture is drawn into every
frame's own window at that scale, centred across and sitting on the window's
bottom edge.  One picture covers one animation from every angle, at one size,
with its feet on the ground -- which is what a player means by "put my drawing on
this unit".

A frame's `main` rect is the TIGHT CROP of the canvas that frame draws, and the
rect is the ONLY area that frame can show, so the picture has to be inside each
one of them; the rects are bottom-aligned on the canvas already (301 of 481
`idleA` rects end on y=108, the rest on y=104), so bottom-aligning to the window
is what puts the feet on the ground.

WHY ONE SCALE, AND WHY A LOW PERCENTILE WINDOW DECIDES IT
---------------------------------------------------------
Fitting each frame to its own window draws the SAME picture 24 px wide in one
frame and 32 px wide in the next, forty times a second, and moves its top edge
over a 20 px range: measured on `walkA`, the drawn y took 7 distinct values.
The size and the ground line pulse with the silhouette and motion stops reading
as motion.

The bare minimum is not the answer either, and measuring said so: 39 of the 481
frames of `idleA` are 16 px wide, and taking the minimum drew the whole
animation at 15x34 while its median window carried 20x44.  So the scale is the
fit factor at the tenth percentile (`KEEP`): nine frames in ten are at least
that big and draw at exactly that size, the tail draws the same picture
proportionally smaller instead of being cut, and no frame ever draws larger than
its own window, so nothing is clipped.  Measured over the villager's 22 files,
the tail is 0..4% of frames and never more; capping at p20 was rejected because
it pushes that tail to 12..15% of frames, and capping at the median or above
pulses again in 3..4 steps and cuts up to 127 frames per file.

THIS REPLACED A CANVAS MODEL, AND WHY
-------------------------------------
The first version sampled the picture in CANVAS coordinates: the union of every
frame's rect was where the original art lived (x 68..132, y 52..108 for a
200x200 canvas), the picture was scaled to fit that union once, and each frame
cropped its own rect out of it.  That is right for a picture that IS the
original art.  It is wrong for a picture a player drew, because the player's
drawing has no canvas coordinates: measured on `u_inf_militia_idleA_x1`, the
union was 40x52 while 481 frames were 16..32 wide and 44..48 tall, so each frame
showed a 24x48 SLICE of the drawing -- and all sixteen angles of pose 0 share
one rect, so all sixteen angles showed the SAME slice.  A player uploaded one
picture and saw a corner of it, from every direction (reported 2026-11-25).
Anchoring in canvas coordinates instead was the obvious repair and it is worse:
pinning the drawing to the union's bottom-centre put 180 of 481 `idleA`
frames, 394 of `walkA` and 334 of `attackA` partly outside their own rect, i.e.
silently cut.

x1 AND x2 ARE INDEPENDENT DRAWINGS
----------------------------------
The engine derives the `_x2` name from `_x1`, so shipping only x1 leaves UHD
users looking at the old art.  x2 is NOT the x1 art scaled by 2: over 6 shipped
pairs the frame rects were exactly 2x in only 0-37 frames of 481-961.  Each
file's canvas is (mostly) double, but the drawing differs, so each file is
repainted at its own canvas size from the same picture.

HONESTY BOUNDARY
----------------
PROVEN: the blocks land in the right cells (copying the original bytes back
reproduces each file byte-for-byte), the round trip decodes within 5, the file
length never changes, and no non-main layer is touched.
NOT PROVEN: that the game renders a RE-ENCODED file.  Loose `.sld` files are
proven to load and to win over the shipped picture (2026-10-17, `dsh test v12`:
466 copied files, the user saw sheep for every villager job) -- but v10/v12
COPIED donor pictures rather than re-encoding them, so "a loose file replaces
the picture" and "this encoder produces a file the game accepts" are two
different claims and only the first one has been looked at in game.
"""
import os

from ..game import sld as S
from ..game import sldencode as E
from ..game import sprites as SP

GRAPHICS_REL = ("resources", "_common", "drs", "graphics")

#: Animations that must survive a repaint for the unit to look right in every
#: situation a player meets.  Reported when a requested one is missing.
ESSENTIAL = ("idle", "walk", "attack", "death")


class PaintError(Exception):
    pass


def _rel(name):
    return "/".join(GRAPHICS_REL + (name + ".sld",))


def load_picture(path):
    """Read a PNG/BMP/DDS (JPEG when Pillow is around) as (rgba bytearray, w, h).

    Goes through `aoe2mod.game.picture`, which is stdlib-only, because the
    packaged build excludes Pillow on purpose: calling PIL here meant the
    SHIPPED program refused every picture the player named (measured 2026-10-30
    against `AoE2 DE Mod Workshop.exe`).  The repo has Pillow, so no suite saw it.
    """
    from ..game import picture as P
    try:
        w, h, rgba = P.read(path)
    except P.PictureError as exc:
        raise PaintError(str(exc))
    return bytearray(rgba), w, h


def union_bbox(sld):
    """(x1, y1, x2, y2) covering every frame's main rect, in canvas coords."""
    xs, ys, xe, ye = None, None, None, None
    for f in sld.frames:
        g = E.frame_grid(f)
        if g is None:
            continue
        x, y, W, H = g[0][0], g[0][1], g[3], g[4]
        xs = x if xs is None else min(xs, x)
        ys = y if ys is None else min(ys, y)
        xe = x + W if xe is None else max(xe, x + W)
        ye = y + H if ye is None else max(ye, y + H)
    if xs is None:
        return None
    return xs, ys, xe, ye


def _windows(sld):
    """[(frame, x, y, W, H)] for every frame that can be painted."""
    out = []
    for f in sld.frames:
        g = E.frame_grid(f)
        if g is None:
            continue
        out.append((f, g[0][0], g[0][1], g[3], g[4]))
    return out


#: Fraction of frames allowed to draw the picture a little smaller than the rest.
#: It is exactly the percentile of the fit factors that sets the scale, so this
#: number is the trade made in one place: 0.05 dragged `idleA` down to a 15x34
#: drawing because 39 of its 481 frames are 16 px wide, when 0.10 keeps 20x44 and
#: costs 43 frames (9%) that draw up to a quarter smaller for a frame or two.
#: Those two or three pixels do not read as a pulse; a 33% smaller drawing does.
KEEP = 0.10


def picture_box(pic, PW, PH):
    """(x, y, w, h) of the picture inside its fully transparent border.

    A picture that is entirely transparent keeps its full size, so "the drawing
    fits the window" stays a true statement about it too.
    """
    x1, y1, x2, y2 = PW, PH, -1, -1
    for y in range(PH):
        base = y * PW * 4
        for x in range(PW):
            if pic[base + x * 4 + 3]:
                if x < x1:
                    x1 = x
                if x > x2:
                    x2 = x
                if y < y1:
                    y1 = y
                if y > y2:
                    y2 = y
    if x2 < x1:
        return 0, 0, PW, PH
    return x1, y1, x2 - x1 + 1, y2 - y1 + 1


def _scale_for(windows, bw, bh, keep=KEEP):
    """One scale for the whole file, and the window that decided it.

    Both are read off the same percentile of the fit factors, so the returned
    window is the one whose size the report's `drawn_size` fits.  See WHY ONE
    SCALE at the top of this module for the measurements behind it.
    """
    if bw <= 0 or bh <= 0:
        raise PaintError("the picture is %dx%d, which has no area" % (bw, bh))
    fits = sorted((min(float(W) / bw, float(H) / bh), W, H)
                  for _f, _x, _y, W, H in windows)
    if not fits:
        raise PaintError("this file has no frame with a main layer")
    sc, W, H = fits[min(len(fits) - 1, int(round(keep * (len(fits) - 1))))]
    return sc, W, H


def _window_pixels(pic, PW, PH, box, W, H, dw, dh, cache):
    """The picture drawn into a W x H window: bottom edge, centred across.

    Nearest neighbour on purpose.  AoE2 sprites are 8-bit art at low
    resolution; interpolating would blur the pixel edges the game draws crisp,
    and the BC1 quantiser then spends its four colours on the blur.

    Cached by window size: a 481-frame file has a handful of sizes, and
    re-sampling the same size four hundred times is the difference between
    0.4 s and two seconds.
    """
    bx, by, bw, bh = box
    # THE PICTURE IS PART OF THE KEY.  A direction sheet hands this function a
    # DIFFERENT picture for each direction at the SAME window size, so a key of
    # sizes alone would paint all sixteen directions with the first one's
    # pixels -- the exact bug the sheet exists to fix.
    key = (id(pic), W, H, dw, dh)
    got = cache.get(key)
    if got is not None:
        return got
    ox = (W - dw) // 2
    oy = H - dh
    out = bytearray(W * H * 4)
    for y in range(dh):
        sy = by + y * bh // dh
        base = (y + oy) * W
        sbase = sy * PW + bx
        for x in range(dw):
            o = (base + x + ox) * 4
            s = (sbase + x * bw // dw) * 4
            out[o] = pic[s]
            out[o + 1] = pic[s + 1]
            out[o + 2] = pic[s + 2]
            out[o + 3] = pic[s + 3]
    cache[key] = out
    return out


#: Gutter between the cells of a direction sheet, in pixels.  The template
#: paints it a flat grey and prints the direction number in it, and
#: `sheet_cells` never samples it -- a stroke that crosses a gutter is ignored
#: rather than bleeding into two directions.  Wide enough for a two-digit number
#: because a number drawn INSIDE a cell would be painted into the sprite.
SHEET_GAP = 14


#: Percentile of the frame windows a sheet cell is cut to, PER AXIS.  Nine
#: frames in ten are no bigger than this in each direction.  Measured over six
#: units (2026-11-27): with KEEP's tenth percentile the archer's cell came out
#: 64x96 while 771 of its 961 frames are TALLER than that, so most frames would
#: have had the drawing fitted down; at the ninetieth percentile 83 frames are
#: over and 878 are placed pixel-exact.  A tenth percentile is right for
#: `_scale_for`, because there it decides how big to DRAW; here it would decide
#: how much of the drawing gets thrown away.
SHEET_KEEP = 0.90


def sheet_size(sld, keep=SHEET_KEEP):
    """(cw, ch) of one direction cell: a window nine frames in ten fit inside.

    THE CELL IS THE WINDOW, not the drawing.  A picture-mode repaint trims the
    picture to its own opaque box and then FITS it, which is why a 512 px
    square export lands as 32x32 inside a 32x84 window and reads as grain.
    A sheet cell is handed over at the frame's own pixel grid, so one pixel of
    the player's drawing becomes one pixel of the sprite -- nothing resampled,
    and nothing lost to the BC1 quantiser except what the format cannot hold.

    PER AXIS, NOT PER FRAME.  Taking the percentile of `min(W, H)` answers "a
    window whose NARROWER side is at least this", which for a tall figure means
    the height column is read off frames chosen for their width -- and the
    answer came back 16 px too short on the archer.  Width and height are two
    separate questions here, so they are asked separately.
    """
    wins = _windows(sld)
    if not wins:
        raise PaintError("this file has no frame with a main layer")
    def axis(vals):
        v = sorted(vals)
        return v[min(len(v) - 1, int(round(keep * (len(v) - 1))))]
    return axis([W for _f, _x, _y, W, _H in wins]), axis([H for _f, _x, _y, _W, H in wins])


def sheet_grid(angles):
    """(cols, rows) of a direction sheet: 16 -> 4x4, 8 -> 3x3 with a spare.

    Reading order is left to right, then top to bottom, which is how every
    sprite sheet a player has ever seen is laid out.
    """
    a = max(int(angles or 1), 1)
    cols = 1
    while cols * cols < a:
        cols += 1
    return cols, (a + cols - 1) // cols


def sheet_layout(sld, angles, gap=SHEET_GAP):
    """(cols, rows, cw, ch, gap) -- the template's geometry and the painter's.

    ONE function answers for both sides on purpose: a template drawn to one
    layout and sliced by another is a picture nobody can line up.
    """
    cw, ch = sheet_size(sld)
    cols, rows = sheet_grid(angles)
    return cols, rows, cw, ch, gap


def sheet_shape(PW, PH, angles, gap=SHEET_GAP):
    """(cols, rows, cw, ch, gap) read OFF a drawn sheet, not off a file.

    The inverse of `sheet_template`'s own arithmetic: the template is
    `gap + cols*(cw+gap)` wide, so a picture of that size divides back into the
    cells it was cut from.  Anything else -- a photo, a sheet drawn by hand at
    another size -- still divides into `cols x rows` cells, just at whatever
    size the picture happens to be, and the painter rescales each cell to the
    file's own grid afterwards.
    """
    cols, rows = sheet_grid(angles)
    cw = max(1, (int(PW) - gap * (cols + 1)) // cols)
    ch = max(1, (int(PH) - gap * (rows + 1)) // rows)
    return cols, rows, cw, ch, gap


def sheet_template_size(sld, angles, gap=SHEET_GAP):
    """(w, h) the template for this file would be, without drawing it.

    Needed for one decision only: `slide_set` has to tell a painted sheet from
    an ordinary picture, and the honest test is "is this the size of the
    template we handed out?".  Measuring beats asking the player, who has no
    reason to know which of the two buttons they pressed.
    """
    cols, rows, cw, ch, _gap = sheet_layout(sld, angles, gap)
    return gap + cols * (cw + gap), gap + rows * (ch + gap)


def sheet_origin(i, cols, cw, ch, gap=SHEET_GAP):
    """(x, y) of cell i's top-left corner inside the sheet.

    The first cell starts one GUTTER in, not at 0, because the gutter carries
    the direction number of every column and row.
    """
    cy, cx = divmod(i, cols)
    return gap + cx * (cw + gap), gap + cy * (ch + gap)


def sheet_cells(pic, PW, PH, cols, rows, cw, ch, gap=SHEET_GAP):
    """Cut a drawn sheet into per-direction cells, reading order.

    A cell the player left empty comes back empty; `paint_sld` decides what to
    do about that, because the answer is a sentence the player should read
    rather than a silent guess buried in a slicer.
    """
    out = []
    for i in range(cols * rows):
        x0, y0 = sheet_origin(i, cols, cw, ch, gap)
        cell = bytearray(cw * ch * 4)
        for row in range(ch):
            sy = y0 + row
            if sy >= PH:
                break
            s = (sy * PW + x0) * 4
            if s >= len(pic):
                break
            n = min(cw * 4, len(pic) - s)
            cell[row * cw * 4:row * cw * 4 + n] = pic[s:s + n]
        out.append(cell)
    return out


def cell_is_blank(cell):
    """True when a sheet cell holds nothing but paper (or nothing at all)."""
    for o in range(0, len(cell), 4):
        if cell[o + 3] == 0 or is_paper_pixel(cell, o):
            continue
        return False
    return True

def _place_cell(cell, cw, ch, W, H):
    """One drawn cell placed into one frame's own window.

    THE WINDOW IS NOT ALWAYS THE CELL.  A file's frames have many different
    rects -- the archer's idle x2 has 961 frames across dozens of sizes, from
    64x80 to 92x100 -- so a cell is never exactly right for all of them.  Two
    rules, in this order:

      1. if the window can hold the cell, paste it unscaled, centred across
         and sitting on the bottom edge (the sprite stands, it does not float);
      2. otherwise fit it, ONE scale for both axes.  Never a stretch, and never
         a crop: a crop loses the feet, which is the half of the figure a player
         notices first.

    Rule 1 is what keeps the common case pixel-exact; rule 2 only fires on the
    frames whose own window is tighter than the one the cell was cut from.
    """
    if W == cw and H == ch:
        return cell
    if W >= cw and H >= ch:
        out = bytearray(W * H * 4)
        ox = (W - cw) // 2
        oy = H - ch
        for y in range(ch):
            o = ((oy + y) * W + ox) * 4
            s = (y * cw) * 4
            out[o:o + cw * 4] = cell[s:s + cw * 4]
        return out
    return _fit_cell(cell, cw, ch, W, H)


def _fit_cell(cell, sw, sh, dw, dh):
    """One nearest-neighbour resample of a drawn cell into a smaller grid.

    WHY THIS EXISTS AT ALL.  The two twins of a file are independent drawings:
    `_x1` cells are half the size of `_x2` cells (villager 16x48 against
    32x88), and their aspect ratios are not identical either (archer 32x52
    against 64x96).  A player downloads the template for the twin the page
    shows, paints it, and uploads it -- and the other twin has to be painted
    from the same drawing.

    SO THE CELL IS FITTED, NOT STRETCHED: one scale for both axes, keeping the
    drawing's proportions, centred across and sitting on the bottom edge the
    way the sprite does.  A stretch to the cell's exact aspect would make a
    figure half an inch wider on the smaller twin and nobody could say why.

    Nearest neighbour on purpose: it is the only resampler that cannot invent
    a colour, so half a downscale of a drawn pixel is still that drawn pixel.
    """
    if (sw, sh) == (dw, dh):
        return cell
    if sw <= 0 or sh <= 0:
        return bytearray(dw * dh * 4)
    k = min(float(dw) / sw, float(dh) / sh)
    nw = max(1, min(dw, int(round(sw * k))))
    nh = max(1, min(dh, int(round(sh * k))))
    ox = (dw - nw) // 2
    oy = dh - nh
    out = bytearray(dw * dh * 4)
    for y in range(nh):
        sy = min(sh - 1, int(y * sh / nh)) if nh else 0
        srow = sy * sw * 4
        orow = (oy + y) * dw * 4
        for x in range(nw):
            sx = min(sw - 1, int(x * sw / nw)) if nw else 0
            s = srow + sx * 4
            o = orow + (ox + x) * 4
            out[o:o + 4] = cell[s:s + 4]
    return out

#: 3x5 digits, one row per line, so the template can number its cells without a
#: font library.  The packaged build ships no Pillow on purpose (see
#: `load_picture`), so a template that needed one would not open where it is
#: most needed.
_DIGITS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}

#: Flat grey the gutter is filled with, and the ink the numbers are drawn in.
SHEET_GUTTER = (58, 58, 66, 255)
SHEET_INK = (226, 226, 232, 255)
SHEET_EDGE = (150, 150, 160, 255)
#: The stencil is the frame's own silhouette flattened to a PALE GREY and drawn
#: OPAQUE.  It used to be the sprite's own colour at alpha 90, which is invisible
#: on a white background and thicker than fog on a dark one -- the colour was
#: dimmed and then the alpha dimmed it a second time.  The player opened the
#: file and asked 为什么都是全透明的 (2026-11-26).  A grey that never leaves this
#: range doubles as the "nothing painted here" marker, so no second copy of the
#: template is needed to tell a painted cell from an untouched one.
SHEET_HINT_LO = 150
SHEET_HINT_HI = 205
#: The paper a cell is printed on.  A sheet is a PICTURE, not a transparency:
#: the player opened one and said 不理解你给透明的有什么用 (2026-11-26).  A PNG
#: with half its pixels at alpha 0 opens as a hole in most viewers and reads as
#: a broken file, so every pixel of a sheet is opaque now.  White on purpose:
#: white is the one colour that can still mean "nothing painted here", so a
#: white flood fill from an editor reads as blank instead of becoming paint.
SHEET_PAPER = (255, 255, 255, 255)


def stencil_grey(r, g, b):
    """The grey a stencil pixel is drawn in for one art pixel (r, g, b)."""
    lum = (r * 299 + g * 587 + b * 114) // 1000
    return SHEET_HINT_LO + lum * (SHEET_HINT_HI - SHEET_HINT_LO) // 255


def is_stencil_pixel(cell, o):
    """True when the pixel at byte `o` is our stencil, not the player's paint."""
    if cell[o + 3] != 255:
        return False
    v = cell[o]
    return cell[o + 1] == v and cell[o + 2] == v and SHEET_HINT_LO <= v <= SHEET_HINT_HI


def is_paper_pixel(cell, o):
    """True when the pixel at byte `o` is the blank paper a cell is printed on."""
    return (cell[o + 3] == 255 and cell[o] == 255
            and cell[o + 1] == 255 and cell[o + 2] == 255)


def has_stencil(cell):
    """True when a cell still carries any of our stencil pixels at all.

    A cell the player filled edge to edge has none, and then the frame's own
    art never has to be replayed for it -- which is what keeps a fully painted
    sixteen-direction sheet as fast as it was before the floor existed.
    """
    for o in range(0, len(cell), 4):
        if cell[o + 3] and is_stencil_pixel(cell, o):
            return True
    return False


def _strip_stencil(placed, base):
    """Lay a drawn cell over the frame's own art.  Returns the frame's window.

    WHERE THE PLAYER DID NOT PAINT, THE GAME'S PIXEL STANDS.  The cell arrives
    printed on white paper with our pale stencil on top of it -- an opaque grey
    silhouette of the pose -- and pasting that in whole turns the figure grey on
    a white card.  So, per pixel: paper takes the art, because paper is exactly
    where nothing was drawn; a stencil grey takes the art too; an empty pixel
    takes the art; a soft edge is laid OVER the art rather than punching a hole
    in it; anything else is the player's and is written verbatim.
    """
    if base is None or len(base) != len(placed):
        return placed
    for o in range(0, len(placed), 4):
        al = placed[o + 3]
        if al == 0 or is_paper_pixel(placed, o) or is_stencil_pixel(placed, o):
            # Nothing drawn here, or nothing but our own stencil -- and a
            # stencil pixel is the template's, never the player's, so it goes
            # even where the frame has no art of its own (a cell fitted into a
            # tighter window drags its stencil off the silhouette).
            placed[o:o + 4] = base[o:o + 4]
        elif al != 255:
            a = al / 255.0
            r = 1.0 - a
            placed[o] = int(placed[o] * a + base[o] * r)
            placed[o + 1] = int(placed[o + 1] * a + base[o + 1] * r)
            placed[o + 2] = int(placed[o + 2] * a + base[o + 2] * r)
            placed[o + 3] = al + int(base[o + 3] * r)
    return placed


def _digit(rgba, w, x, y, ch, ink):
    rows = _DIGITS.get(ch)
    if rows is None:
        return
    for ry, line in enumerate(rows):
        for rx, bit in enumerate(line):
            if bit != "1":
                continue
            px = x + rx
            py = y + ry
            if 0 <= px < w and py >= 0:
                o = (py * w + px) * 4
                if o + 3 < len(rgba):
                    rgba[o:o + 4] = bytes(ink)


def _number(rgba, w, h, x, y, n, ink):
    """Draw `n` as 3x5 digits with one pixel between them."""
    for i, ch in enumerate(str(int(n))):
        _digit(rgba, w, x + i * 4, y, ch, ink)


def sheet_template(sld, angles, hint=True):
    """The empty direction sheet to hand to a player: (w, h, rgba).

    WHY A TEMPLATE AND NOT JUST A SIZE.  "Upload a 4x4 grid of 32x84 cells" is
    a sentence nobody can act on without measuring; a picture with the cells
    drawn, numbered and showing the original pose as a pale stencil is the same
    instruction in a form that can be painted over.  The stencil comes from the
    file's own pose 0 of each direction, so the sprite that comes back stands
    the same way the game's own art does.

    The gutter is OPAQUE and the cells are not touched at all: `sheet_cells`
    samples the cell rectangles only, so a border can never become a pixel of
    the sprite.
    """
    a = max(int(angles or 1), 1)
    cols, rows, cw, ch, gap = sheet_layout(sld, a)
    w = gap + cols * (cw + gap)
    h = gap + rows * (ch + gap)
    rgba = bytearray(w * h * 4)
    for i in range(w * h):
        rgba[i * 4:i * 4 + 4] = bytes(SHEET_GUTTER)
    # THE CELLS ARE PRINTED ON PAPER, NOT LEFT TRANSPARENT.  The gutter is opaque
    # so the sheet shows its own grid on any background; the cells used to be
    # alpha 0, which opens as a hole in most viewers -- 不理解你给透明的有什么用
    # (2026-11-26).  Every pixel of this file is opaque now.  White and not the
    # gutter colour, because a cell the player skipped still has to be tellable
    # from one they filled: `cell_is_untouched` reads paper and stencil as
    # untouched, and anything else as their paint.
    poses = max(len(sld.frames) // a, 1)
    for i in range(a):
        x0, y0 = sheet_origin(i, cols, cw, ch, gap)
        for y in range(ch):
            o = ((y0 + y) * w + x0) * 4
            rgba[o:o + cw * 4] = bytes(SHEET_PAPER) * cw
        for x in range(-1, cw + 1):
            for y in (-1, ch):
                px, py = x0 + x, y0 + y
                if 0 <= px < w and 0 <= py < h:
                    o = (py * w + px) * 4
                    rgba[o:o + 4] = bytes(SHEET_EDGE)
        for y in range(ch):
            for x in (-1, cw):
                px, py = x0 + x, y0 + y
                if 0 <= px < w and 0 <= py < h:
                    o = (py * w + px) * 4
                    rgba[o:o + 4] = bytes(SHEET_EDGE)
        _number(rgba, w, h, x0, y0 - 8, i + 1, SHEET_INK)
        if hint:
            # THE STENCIL IS THE FRAME'S OWN RECT, NOT THE WHOLE CANVAS.  A
            # replay plane is canvas-sized, and a canvas is 400x400 while the
            # window is 32x84, so pasting the canvas would put an unknown corner
            # of the sprite in the cell.  The rect is the tight crop the engine
            # itself shows, which is exactly what the cell is the size of.
            k = i * poses
            if k >= len(sld.frames):
                continue
            walk = S.Walk()
            for j in range(k + 1):
                walk.take(sld.frames[j])
            got = walk.plane("main")
            if got is None:
                continue
            plane, PW, PH = got
            g = S.frame_grid(sld.frames[k]) if hasattr(S, "frame_grid") else None
            m = sld.frames[k].layers.get("main")
            if m is None:
                continue
            rect, _fmt, _ncmd, _cmds = S.parse_rect_layer(m)
            rx, ry, _rw, _rh, _bw, _bh = S.grid_of(rect)
            for y in range(min(ch, PH - ry)):
                for x in range(min(cw, PW - rx)):
                    s = ((ry + y) * PW + rx + x) * 4
                    if s + 3 >= len(plane) or plane[s + 3] < 40:
                        continue
                    o = ((y0 + y) * w + x0 + x) * 4
                    v = stencil_grey(plane[s], plane[s + 1], plane[s + 2])
                    rgba[o:o + 4] = bytes((v, v, v, 255))
    return w, h, rgba

def pose_grid(n):
    """(cols, rows) for `n` frames laid out in reading order."""
    return sheet_grid(n)


def pose_layout(sld, angle, angles, gap=SHEET_GAP):
    """(cols, rows, cw, ch, gap, frames) for ONE direction's frames.

    WHY THIS EXISTS AT ALL.  A direction sheet has sixteen cells, one per
    direction, so every pose of that direction is painted with the same
    picture -- and a walk cycle is thirty DIFFERENT drawings.  The player said
    so in as many words: 你就看这个走路，明显图片都是不一样的，你应该让用户每个都可以
    修改，而不是一张图片替换全部.  Here one cell is one FRAME, so each pose can
    be its own drawing, and a cell left alone keeps the game's own art.

    The cell is the LARGEST window in that direction, so the common frame is
    1:1 and the few tighter ones are fitted down by `_place_cell`.
    """
    a = int(angle)
    n_ang = max(int(angles or 1), 1)
    wins = _windows(sld)
    poses = max(len(wins) // n_ang, 1)
    mine = wins[a * poses:(a + 1) * poses]
    if not mine:
        raise PaintError("这个朝向没有可画的画面")
    cols, rows = pose_grid(len(mine))
    cw = max(W for _f, _x, _y, W, _H in mine)
    ch = max(H for _f, _x, _y, _W, H in mine)
    return cols, rows, cw, ch, gap, mine


def pose_template_size(sld, angle, angles, gap=SHEET_GAP):
    """(w, h) of the per-frame sheet for one direction, without drawing it."""
    cols, rows, cw, ch, gap, _mine = pose_layout(sld, angle, angles, gap)
    return gap + cols * (cw + gap), gap + rows * (ch + gap)


def cell_is_untouched(cell):
    """True when a cell still holds nothing but paper and our own pale stencil.

    Every opaque pixel we hand out is a stencil grey in a narrow band; nothing a
    brush lays down comes back as exactly that (and a player who picks one of
    those greys on purpose is drawing on a grey silhouette, so the answer they
    want and the answer they get agree).  A cell that still reads as stencil is
    never decoded at all: it is copied through byte for byte, which is the only
    way a frame nobody touched is guaranteed to keep the game's own pixels.
    """
    for o in range(0, len(cell), 4):
        if cell[o + 3] == 0 or is_paper_pixel(cell, o):
            continue
        if not is_stencil_pixel(cell, o):
            return False
    return True


def pose_sheet_shape(PW, PH, count, gap=SHEET_GAP):
    """(cols, rows, cw, ch, gap) read off a per-frame sheet, not off a file."""
    cols, rows = pose_grid(max(int(count), 1))
    cw = max(1, (int(PW) - gap * (cols + 1)) // cols)
    ch = max(1, (int(PH) - gap * (rows + 1)) // rows)
    return cols, rows, cw, ch, gap


def pose_cells_of(sld, angle, angles):
    """The frames of ONE direction, in file order, as `_windows` rows."""
    _cols, _rows, _cw, _ch, _gap, mine = pose_layout(sld, angle, angles)
    return mine


def pose_replay(sld, mine):
    """{frame index: (rgba, W, H)} -- each frame's own art, replayed in order.

    WHY REPLAY AND NOT THE FRAME ALONE.  Nine of ten shipped frames are PATCHES:
    they name only the cells that changed since the previous frame, so a frame
    decoded on its own is missing almost the whole figure (measured 2026-11-27:
    the archer idle is 903 patches out of 961).  Walking the file once and
    cropping the canvas at each frame's own rect gives back exactly the pixels
    that frame draws -- which is what an untouched cell has to keep.
    """
    out = {}
    walk = S.Walk()
    taken = -1
    for fr, _x, _y, W, H in mine:
        while taken < fr.index:
            taken += 1
            walk.take(sld.frames[taken])
        got = walk.plane("main")
        m = sld.frames[fr.index].layers.get("main")
        if got is None or m is None:
            continue
        plane, PW, PH = got
        rect = S.parse_rect_layer(m)[0]
        rx, ry = rect[0], rect[1]
        crop = bytearray(W * H * 4)
        for y in range(min(H, PH - ry)):
            s = ((ry + y) * PW + rx) * 4
            n = min(W, PW - rx) * 4
            if n > 0:
                crop[y * W * 4:y * W * 4 + n] = plane[s:s + n]
        out[fr.index] = (crop, W, H)
    return out


def looks_like_pose_sheet(sld, PW, PH, angle, angles):
    """Whether an upload is the per-frame sheet of `angle` for this file."""
    try:
        w, h = pose_template_size(sld, angle, angles)
    except PaintError:
        return False
    return abs(int(PW) - w) <= 1 and abs(int(PH) - h) <= 1

def pose_template(sld, angle, angles, hint=True, gap=SHEET_GAP):
    """The per-frame sheet for one direction: (w, h, rgba).

    Same gutter, same numbers, same pale stencil as `sheet_template` -- but one
    cell per FRAME of that direction, each showing that exact frame, so the
    player is painting over the pose they are looking at rather than over a
    single stand-in for the whole cycle.
    """
    a = max(int(angle), 0)
    cols, rows, cw, ch, gap, mine = pose_layout(sld, a, angles, gap)
    w = gap + cols * (cw + gap)
    h = gap + rows * (ch + gap)
    rgba = bytearray(w * h * 4)
    for i in range(w * h):
        rgba[i * 4:i * 4 + 4] = bytes(SHEET_GUTTER)
    for i in range(cols * rows):
        x0, y0 = sheet_origin(i, cols, cw, ch, gap)
        for y in range(ch):
            o = ((y0 + y) * w + x0) * 4
            rgba[o:o + cw * 4] = bytes(SHEET_PAPER) * cw
        for x in range(-1, cw + 1):
            for y in (-1, ch):
                px, py = x0 + x, y0 + y
                if 0 <= px < w and 0 <= py < h:
                    o = (py * w + px) * 4
                    rgba[o:o + 4] = bytes(SHEET_EDGE)
        for y in range(ch):
            for x in (-1, cw):
                px, py = x0 + x, y0 + y
                if 0 <= px < w and 0 <= py < h:
                    o = (py * w + px) * 4
                    rgba[o:o + 4] = bytes(SHEET_EDGE)
        _number(rgba, w, h, x0, y0 - 8, i + 1, SHEET_INK)
    if not hint:
        return w, h, rgba
    walk = S.Walk()
    taken = -1
    for i, (fr, _x, _y, _W, _H) in enumerate(mine):
        while taken < fr.index:
            taken += 1
            walk.take(sld.frames[taken])
        got = walk.plane("main")
        m = sld.frames[fr.index].layers.get("main")
        if got is None or m is None:
            continue
        plane, PW, PH = got
        rect = S.parse_rect_layer(m)[0]
        rx, ry = rect[0], rect[1]
        x0, y0 = sheet_origin(i, cols, cw, ch, gap)
        for y in range(min(ch, PH - ry)):
            for x in range(min(cw, PW - rx)):
                s = ((ry + y) * PW + rx + x) * 4
                if s + 3 >= len(plane) or plane[s + 3] < 40:
                    continue
                o = ((y0 + y) * w + x0 + x) * 4
                v = stencil_grey(plane[s], plane[s + 1], plane[s + 2])
                rgba[o:o + 4] = bytes((v, v, v, 255))
    return w, h, rgba



def looks_like_sheet(sld, PW, PH, angles):
    """Whether an upload is a direction sheet for this file, by its size.

    THE PICTURE ITSELF IS THE EVIDENCE.  Two buttons upload: one takes a single
    drawing (fitted into the window, the old behaviour) and one takes the
    direction sheet the page handed out.  A player who pressed the sheet button
    and got a fitted single drawing would see their sixteen directions squashed
    into one -- so the size is checked here rather than trusted from a flag the
    page could forget to send.

    One pixel of slack: an image editor that trims a fully opaque border by a
    pixel must not turn the answer off.
    """
    try:
        w, h = sheet_template_size(sld, angles)
    except PaintError:
        return False
    return abs(int(PW) - w) <= 1 and abs(int(PH) - h) <= 1


def paint_sld(sld, pic, PW, PH, animations=None, angles=1, sheet=False,
              pose=False, angle=0):
    """Repaint one loaded .sld.  Returns (new_bytes, report dict).

    One scale for the whole file, the picture drawn into every frame's own
    window at that scale, so one picture covers every angle of the animation
    at one steady size with its feet on the window's bottom edge (see ONE SCALE
    PER FILE at the top of this module).
    """
    bbox = union_bbox(sld)
    if bbox is None:
        raise PaintError("this file has no frame with a main layer")
    windows = _windows(sld)
    box = picture_box(pic, PW, PH)
    if box[2] <= 0 or box[3] <= 0:
        raise PaintError("the picture is %dx%d, which has no area" % (PW, PH))
    # FULL CELLS, NOT THE ORIGINAL SILHOUETTE.  A shipped run list is a MASK: the
    # villager idle frame 0 has 55 cells and draws only 35, because the cells its
    # art never reaches are not stored.  Repainting in place could touch only those
    # 35, so a picture that fills the window kept a hole wherever the OLD art was
    # empty -- the player saw the drawing come back 「缺损」 (2026-11-25).  The whole
    # grid is written now, and rebuild_dense emits a run list that says so.
    #
    # One scale for the whole file, read off a low percentile of the windows (see
    # WHY ONE SCALE above).  A frame whose window is under it draws the picture
    # proportionally smaller rather than losing its edges.
    fits = sorted((min(float(W) / box[2], float(H) / box[3]), W, H)
                  for _f, _x, _y, W, H in windows)
    if not fits:
        raise PaintError("this file has no frame with a main layer")
    pick = min(len(fits) - 1, int(round(KEEP * (len(fits) - 1))))
    sc = fits[pick][0]
    # `window` in the report is the window that DECIDED the scale, so a test can
    # check the drawn size against the very rect it came from.
    win_w, win_h = fits[pick][1], fits[pick][2]
    dw = max(1, int(box[2] * sc))
    dh = max(1, int(box[3] * sc))
    cache = {}
    smaller = []
    blank = []

    if pose:
        # ONE CELL PER FRAME of ONE DIRECTION.  This is the mode the player asked
        # for in as many words -- 你就看这个走路，明显图片都是不一样的，你应该让用户每个都可以
        # 修改，而不是一张图片替换全部 -- and it is a different contract from a
        # direction sheet: there one picture stands for a whole direction, here
        # every pose is its own drawing and a cell left untouched keeps the
        # game's own pixels for that frame.
        a = max(int(angle or 0), 0)
        _cols, _rows, pcw, pch, _pgap, mine = pose_layout(sld, a, angles)
        src = pose_sheet_shape(PW, PH, len(mine))
        cols, rows, scw, sch, sgap = src[0], src[1], src[2], src[3], src[4]
        cells = sheet_cells(pic, PW, PH, cols, rows, scw, sch, sgap)
        if len(cells) < len(mine):
            raise PaintError("这张图切不出 %d 格" % (len(mine),))
        # A CELL THAT STILL HOLDS ONLY THE PALE STENCIL WAS NEVER PAINTED.  Those
        # frames are copied through byte for byte rather than re-encoded from a
        # decoded replay: re-encoding a BC1 block from its own decoded pixels is
        # not guaranteed to give the same eight bytes back, and a frame nobody
        # touched has no business changing.
        painted = {}
        for i, (fr, _x, _y, W, H) in enumerate(mine):
            if not cell_is_untouched(cells[i]):
                painted[fr.index] = i
        if not painted:
            raise PaintError("这张空表一格都没画，没有可以贴上去的东西")
        keep = {fr.index for fr, _x, _y, _W, _H in mine if fr.index in painted}
        skip = {fr.index for fr in sld.frames if fr.index not in keep}
        art = pose_replay(sld, mine)
        cells = [_fit_cell(cells[i], scw, sch, pcw, pch) for i in range(len(cells))]

        def paint(fr, W, H):
            i = painted.get(fr.index)
            got = art.get(fr.index)
            if i is None:
                return got[0] if got else bytearray(W * H * 4)
            placed = _place_cell(cells[i], pcw, pch, W, H)
            if placed is cells[i]:
                # `_place_cell` hands the cell back untouched when the window
                # is exactly the cell, so writing into it here would edit the
                # cell that the NEXT frame of this direction also draws from.
                placed = bytearray(placed)
            # ONLY WHAT THE PLAYER LAID DOWN REPLACES THE SPRITE.  The cell they
            # paint on carries our stencil -- a pale grey silhouette of that very
            # frame -- so a cell where they drew a helmet and nothing else still
            # carries the body as grey: taking the cell as the whole truth would
            # hand back a helmet floating on nothing, or a figure painted flat
            # grey.  Measured 2026-11-26 on the legionary walk: a 14x14 blob in
            # one cell left 1516 opaque pixels where the shipped frame has 2423.
            # So the rule is paint-wins, stencil-and-empty-show-the-art, and a
            # frame nobody painted never reaches here at all (byte for byte).
            return _strip_stencil(placed, got[0] if got else None)

        # KEEP THE GAME'S TINT ON A FRAME THE PLAYER DREW.  `rebuild_dense`
        # clears playercolor by default because a whole new picture has a new
        # silhouette, but here the silhouette is mostly the shipped one: the
        # legionary's red cape IS the team colour, not a main-layer pixel, so
        # clearing the mask made one frame of the walk go grey while every
        # other frame stayed red (seen 2026-11-26 in floor_compare.png).
        buf = E.rebuild_dense(sld, paint, skip=skip, keep_masks=set(painted))
        fresh = S.Sld(sld.path, buf)
        E.verify_repaint(sld, fresh, touched=painted)
        report = {"frames_painted": len(painted), "frames_skipped":
                  sorted(skip), "frames_clipped": 0, "frames_smaller": [],
                  "frames_dense": len(painted), "bbox": list(bbox),
                  "picture_scaled_by": 1.0, "picture_box": list(box),
                  "window": [pcw, pch], "drawn_size": [pcw, pch],
                  # THE FRAMES THAT WERE ACTUALLY PAINTED.  Every other
                  # frame is a byte-for-byte copy of the shipped one, so a
                  # structural verifier has to be told which frames it may
                  # hold to the dense-picture rule: the copies still carry
                  # whatever run-list flag they were shipped with.
                  "frames_touched": sorted(painted),
                  "sheet": {"cols": cols, "rows": rows,
                             "cell": [pcw, pch], "gap": sgap,
                             "angles": max(int(angles or 1), 1),
                             "angle": a, "blank_cells": []}}
        return buf, report
    if sheet:
        # ONE CELL PER DIRECTION, HANDED OVER AT A PIXEL GRID, NOT FITTED.
        # Picture mode trims the drawing to its own opaque box and then scales
        # it to `min(W/bw, H/bh)`, which is why a 512 px square export lands as
        # 32x32 inside a 32x84 window and reads as grain.  A sheet cell carries
        # no trimming and no fitting: it is already a window, so it is copied
        # at 1:1 -- and when the caller hands over a geometry measured off a
        # DIFFERENT twin (`_x2` cells are exactly twice `_x1` cells), the only
        # resampling is that whole-number step, once per cell, before any frame
        # is touched.
        if sheet is True:
            # THE UPLOADED IMAGE SAYS ITS OWN GEOMETRY.  The template a player
            # painted on was generated from ONE twin (`_x2` cells are twice
            # `_x1` cells), and the same picture has to paint both; measuring
            # the grid off the picture means the answer does not depend on
            # which twin the template came from.
            src = sheet_shape(PW, PH, angles)
        else:
            src = tuple(sheet)
        cols, rows, scw, sch = src[0], src[1], src[2], src[3]
        sgap = src[4] if len(src) > 4 else SHEET_GAP
        cells = sheet_cells(pic, PW, PH, cols, rows, scw, sch, sgap)
        n_ang = max(int(angles or 1), 1)
        if len(cells) < n_ang:
            raise PaintError("这张图切不出 %d 个朝向" % (n_ang,))
        # A CELL THAT STILL HOLDS ONLY THE STENCIL WAS NEVER PAINTED.  The
        # template now carries an OPAQUE grey stencil, so `cell_is_blank` (alpha
        # all zero) would call sixteen untouched directions painted and paste
        # the stencil over all sixteen -- the same reason the per-frame sheet
        # tests with `cell_is_untouched`.  A blank cell here means "this
        # direction is still the game's", so those frames are skipped below.
        drawn = []
        for i in range(n_ang):
            if cell_is_untouched(cells[i]):
                blank.append(i)
            else:
                drawn.append(i)
        if not drawn:
            raise PaintError("这张空表一格都没画，没有可以贴上去的东西")
        cw, ch = sheet_size(sld)
        if (scw, sch) != (cw, ch):
            cells = [_fit_cell(c, scw, sch, cw, ch) for c in cells]
        poses = max(len(windows) // n_ang, 1)
        dir_of = {fr.index: min(fr.index // poses, n_ang - 1)
                  for fr, _x, _y, _W, _H in windows}
        keep = {i for i, d in dir_of.items() if d in drawn}
        skip = {fr.index for fr in sld.frames if fr.index not in keep}
        # Only the directions whose cell still shows stencil need the game's own
        # art replayed; a cell painted edge to edge replaces every pixel it
        # covers, so its frames are answered from the cell alone.
        floored = {i for i in drawn if has_stencil(cells[i])}
        art = pose_replay(sld, [w for w in windows
                                if w[0].index in keep and dir_of[w[0].index] in floored])

        def cell_for(fr):
            # The file's frames are laid out ANGLE BY ANGLE (`idx = angle *
            # poses + pose`), so the direction is the frame index over the pose
            # count -- not the frame index over the whole file.
            return cells[dir_of[fr.index]]

        def paint(fr, W, H):
            cell = _place_cell(cell_for(fr), cw, ch, W, H)
            if cell is cells[dir_of[fr.index]]:
                cell = bytearray(cell)
            got = art.get(fr.index)
            return _strip_stencil(cell, got[0] if got else None) if got else cell
    else:
        def paint(fr, W, H):
            fw, fh = dw, dh
            if fw > W or fh > H:
                k = min(float(W) / dw, float(H) / dh)
                fw, fh = max(1, int(dw * k)), max(1, int(dh * k))
                smaller.append(fr.index)
            return _window_pixels(pic, PW, PH, box, W, H, fw, fh, cache)

    # THE DIRECTIONS NOBODY PAINTED KEEP THE GAME'S OWN BYTES.  A direction sheet
    # used to be painted whole: sixteen cells, every frame rewritten from one of
    # them, so an untouched cell was copied over all thirty frames of its
    # direction -- and with an opaque stencil in the cell that would have painted
    # the game's art out in grey.  `keep` names the frames whose direction was
    # actually painted; the rest are copied through byte for byte, and a painted
    # direction keeps its own team tint for the same reason the per-frame sheet
    # does (see KEEP THE GAME'S TINT above).
    skip_here = skip if sheet else None
    keep_here = set(keep) if sheet else None
    buf = E.rebuild_dense(sld, paint, skip=skip_here, keep_masks=keep_here)
    # The file is LONGER now (a dense main layer stores every cell), so what gets
    # checked is structure: same frames, same rects, every other layer verbatim.
    fresh = S.Sld(sld.path, buf)
    E.verify_repaint(sld, fresh, touched=keep if sheet else None)
    done = len(keep) if sheet else len(windows)

    # `window` is the window the scale came from (the fifth-percentile one), so
    # "drawn_size fits window" is the claim this report lets a test check -- and
    # `frames_clipped` states the per-frame version of it outright.  `picture_box`
    # is what the picture was trimmed to: a square canvas with an oval drawing in
    # it reports a shorter box than it was handed, and that is not a bug.
    report = {"frames_painted": done,
              "frames_skipped": sorted(skip) if sheet else [],
              # THE FRAMES A SHEET ACTUALLY WROTE.  The rest are byte-for-byte
              # copies of the shipped frames, patch flags and all, so a
              # structural verifier has to be told which frames it may hold to
              # the dense rule.  Without this the shipped build refused a
              # fifteen-of-sixteen-untouched sheet with "frame 31 still reads
              # as a patch".
              "frames_touched": sorted(keep) if sheet else [],
              "frames_clipped": 0, "frames_smaller": smaller,
              "frames_dense": done,
              "bbox": list(bbox),
              "picture_scaled_by": round(sc, 4),
              "picture_box": list(box),
              "window": [win_w, win_h],
              "drawn_size": [dw, dh]}
    if sheet:
        cols, rows, cw, ch, gap = sheet_layout(sld, angles)
        report["sheet"] = {"cols": cols, "rows": rows, "cell": [cw, ch],
                          "gap": gap, "angles": int(angles or 1),
                          "blank_cells": blank,
                          "drawn_size": [cw, ch]}
    return buf, report


def picture_size(path):
    """(w, h) of a picture without decoding its pixels.

    A preview has to answer "how many files, do the grids fit?" and the answer
    only needs the dimensions.  Decoding a 4,000 px photo to learn two integers
    would make `plan()` cost as much as `build()`.
    """
    from ..game import picture as P
    try:
        return P.size(path)
    except P.PictureError as exc:
        raise PaintError("读不出这张图片：%s —— %s" % (path, exc))


def _targets(game_root, graphics, civs, unit_id, animations=None, scope="all"):
    """Every .sld this unit's animations live in, plus what could not be found.

    One enumeration for both `plan_unit` and `paint_unit`: a preview that walked
    its own list would eventually promise a file the build does not write.
    """
    idx = SP.art_index(game_root, graphics)
    by_id = {}
    for civ in civs:
        if scope not in ("all", None) and civ.get("name") not in scope:
            continue
        for u in civ.get("units") or ():
            if u.get("id") == unit_id:
                by_id.setdefault(civ.get("name"), idx.art(u))
                break
    if not by_id:
        raise PaintError("no civilisation in scope has a record for unit %d"
                         % unit_id)

    out, missing = [], []
    seen = {}
    covered = set()
    for civ_name, art in sorted(by_id.items()):
        if art.get("kind") != "loose":
            missing.append({"civ": civ_name, "reason": art.get("reason")
                            or "no loose .sld art"})
            continue
        # A civilisation counts as covered as soon as the files it needs are
        # being shipped -- which is true whether a file was first found here or
        # for a neighbour.  Counting only the civs that contributed a NEW file
        # said "2 civilisations" about a change that reaches all 63.
        wanted = [t for t in (art.get("tokens") or {})
                  if not animations or t in animations]
        if wanted:
            covered.add(civ_name)
        for token, base in sorted((art.get("tokens") or {}).items()):
            if animations and token not in animations:
                continue
            if not base.endswith("_x1"):
                continue
            for tail in ("_x1", "_x2"):
                name = base[:-3] + tail
                if name in seen:
                    # Another civilisation wants this exact file, and it is the
                    # same picture -- painting it twice would ship one answer.
                    continue
                seen[name] = civ_name
                path = os.path.join(game_root, *GRAPHICS_REL, name + ".sld")
                if not os.path.exists(path):
                    missing.append({"file": name + ".sld",
                                    "reason": "the target file is not on disk"})
                    continue
                out.append({"civ": civ_name, "animation": token,
                            "name": name + ".sld", "path": path,
                            "suffix": tail})
    present = set(t for a in by_id.values()
                  if a.get("kind") == "loose" for t in (a.get("tokens") or {}))
    return out, sorted(covered), missing, present


def _no_art(unit_id, missing):
    why = ""
    if missing:
        first = missing[0]
        why = " (%s)" % (first.get("reason") or "no loose .sld art")
    return PaintError(
        "unit %d has no loose .sld art to repaint, so there is nothing to "
        "paint on%s" % (unit_id, why))


def plan_unit(game_root, graphics, civs, unit_id, animations=None, scope="all"):
    """What repainting this unit WOULD touch, without painting anything.

    The per-file numbers here are the same ones `paint_unit` reports, computed by
    the same walk, because a preview that guesses is a preview that lies.
    """
    targets, covered, missing, present = _targets(
        game_root, graphics, civs, unit_id, animations, scope)
    if not targets:
        raise _no_art(unit_id, missing)
    per_file = []
    for t in targets:
        sld = S.read_sld(t["path"])
        bbox = union_bbox(sld)
        if bbox is None:
            missing.append({"file": t["name"],
                            "reason": "this file has no frame with a main layer"})
            continue
        per_file.append({"file": t["name"], "animation": t["animation"],
                         "civ_first_seen": t["civ"], "bbox": list(bbox),
                         "frames": len(sld.frames),
                         "bytes": len(sld.data)})
    if not per_file:
        raise _no_art(unit_id, missing)
    return {
        "intent": "unit.art",
        "mode": "repaint",
        "editable": True,
        "unit": unit_id,
        "file_count": len(per_file),
        "civ_count": len(covered),
        "per_file": per_file,
        "animations": sorted(present & set(animations) if animations
                             else present),
        "missing_essential": [t for t in ESSENTIAL if t not in present],
        "missing": missing,
        "changes_dat": False,
        "no_dat": True,
    }


def paint_unit(game_root, graphics, civs, unit_id, pic, PW, PH,
               animations=None, scope="all"):
    """Repaint every .sld of one unit's animations, for the civilisations asked.

    Returns a plan-shaped dict: the files to ship, plus what was measured.
    """
    targets, covered, missing, present = _targets(
        game_root, graphics, civs, unit_id, animations, scope)
    if not targets:
        raise _no_art(unit_id, missing)

    files, per_file = {}, []
    for t in targets:
        sld = S.read_sld(t["path"])
        try:
            data, rep = paint_sld(sld, pic, PW, PH, animations)
        except ValueError as e:
            missing.append({"file": t["name"], "reason": str(e)})
            continue
        files[_rel(t["name"][:-4])] = data
        rep["file"] = t["name"]
        rep["animation"] = t["animation"]
        rep["civ_first_seen"] = t["civ"]
        rep["bytes"] = len(data)
        per_file.append(rep)
    if not files:
        raise _no_art(unit_id, missing)
    return {
        "intent": "unit.art",
        "mode": "repaint",
        "editable": bool(files),
        "unit": unit_id,
        "files": files,
        "file_count": len(files),
        "civ_count": len(covered),
        "per_file": per_file,
        "animations": sorted(present & set(animations) if animations
                             else present),
        "missing_essential": [t for t in ESSENTIAL if t not in present],
        "missing": missing,
        "changes_dat": False,
        "no_dat": True,
    }
