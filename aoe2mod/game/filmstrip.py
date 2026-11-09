# -*- coding: utf-8 -*-
"""filmstrip.py -- draw a unit's animation as one row of pictures.

WHY THIS EXISTS

The editor can change a unit's numbers, its art (reskin), and now its tasks.
None of those screens answers the question a modder asks first: "what does this
thing look like right now?"  In AGE3 that is `ShowSLP` plus a frame spinner;
here it is one row of pictures you scroll by eye.

MEASURED COST (2026-11-04, `_probe/_tmp/spr2.py` / `spr3.py`)

    read_sld      a 900 KB villager .sld   0.003 s   (page cache warm)
    render_frame  200x200 canvas           0.8-2.0 ms
    strip + png   20 frames                0.003 s
    ------------------------------------------------
    20-frame walk row                      0.016 s total, 13,929 B PNG
    16-angle row (one frame each)          0.010 s, 9,588 B

So nothing is pre-baked and nothing streams: one request per animation costs
less than the HTTP round trip that carries it.

THE GRID IS A CLAIM, THE FILE IS THE TRUTH

A graphics record says `frame_count x angle_count` and the engine indexes
`frame * angle_count + angle`.  That holds for 7,602 of 7,618 shipped files; 16
files are claimed by records that DISAGREE (the ibex's idle art is claimed as
both 30x16 and 60x16).  Most files also carry one trailing frame past
`frame_count * angle_count` (961 = 60*16 + 1), but some carry none (a house's
3-state art is exactly 3).  So the pose count is decided by trying the
divisibility that fits, in this order:

    n % ac == 0        -> n / ac          (no trailing frame)
    (n - 1) % ac == 0  -> (n - 1) / ac    (the usual trailing frame)
    otherwise          -> n, one angle    (never slice at a made-up pitch)

A wrong pitch shows the same picture sixteen times, which looks like a bug in
the game rather than a bug in this file.

EMPTY POSES ARE DATA, NOT ERRORS

`b_dark_wall_palisade_flag_x1.sld` is 450 frames and 360 of them are frame_type
0x00 -- no layers at all.  `a_fish_marlin1_x1.sld` is 61 frames and 37 of them
are empty the same way.  Those poses are skipped and counted, because a row of
blank cells is worse than a shorter row; the caller prints "12 of 16 poses have
no pixels for this angle" instead of a refusal that blames the file.

WHAT IS NOT HERE

No scaling (the page draws at native size with `image-rendering: pixelated`), no
video (a row of PNGs is the same thing for this purpose and needs no codec), and
no per-civ team colour yet: `render_frame` gets a default red, so a villager is
shown in red, not in the selected civilization's colour.
"""
import os

from . import ddstex as D
from . import sld as S
from . import sprites as SP
from . import moments as M

#: Frames past this many are not drawn: a 60-frame idle is 2,400 px of picture at
#: 40 px a frame, which pushes the page sideways on a 1264 px window.  The caller
#: is told when the strip was capped rather than being handed a silent sample.
MAX_FRAMES = 48

#: The engine's animation keys as the file-name suffix spells them.  Kept here
#: rather than imported from `intent.reskin.MOMENT_WORD` because `game/` must not
#: depend on `intent/` (reskin imports this package, so that would be a cycle).
#: `_probe/test_filmstrip.py` asserts the two tables agree on every key they
#: share, so the duplication cannot drift into two vocabularies.
#: The English keys the engine uses for each animation, taken from `moments.py`
#: rather than kept here.  They used to be a second table and the two drifted:
#: `idlec` read 「闲着没事动一下」 on a chip and 「闲着的另一个动作」 in a reskin
#: sentence, about the same animation on two screens about the same unit.
ANIM_ZH = M.ANIM_ZH

#: Reading order, also from `moments.py` -- a player looks for 站着不动 before
#: 走路 before 倒下, and both screens must agree on that sequence too.
_ORDER = M.ORDER


class FilmError(Exception):
    """A filmstrip that cannot be drawn, with a reason a player can read."""


def anim_zh(key):
    """The Chinese word for an animation key, or None when there is none.

    Unknown keys are NOT invented: the caller prints the engine's own spelling,
    which at least can be searched for in a wiki.  A made-up word cannot.
    """
    return ANIM_ZH.get((key or "").lower())


def order_key(key):
    k = (key or "").lower()
    try:
        return (_ORDER.index(k), "")
    except ValueError:
        return (len(_ORDER), k)


def poses_of(num_frames, angles):
    """How many POSES a file holds, given its declared angle count.

    See the module docstring for why the order of the three tests matters: a
    house's 3-state art is exactly 3 frames, while a villager's 60-pose idle is
    961 because the engine appends one frame.  Getting this backwards turns a
    60-pose idle into a 961-pose one-angle strip, and every pose after the first
    is then the wrong picture.
    """
    n = int(num_frames or 0)
    ac = max(int(angles or 1), 1)
    if n <= 0:
        return 0
    if n % ac == 0:
        return n // ac
    if (n - 1) % ac == 0:
        return (n - 1) // ac
    return n


def grid_for(num_frames, claimed):
    """The (frame_count, angle_count) a set of records claims, if it fits.

    `claimed` is the set of grids shipped records ask for -- `SpriteIndex.grid`
    returns a SET precisely because they can disagree.  Returns
    `((fc, ac), "record")` when a claim reproduces the file, else
    `((poses, 1), "file")`.  The second element is what the caller prints: "the
    record and the file agree" and "I read the grid off the file" are different
    facts and only one of them is good news.
    """
    n = int(num_frames or 0)
    for fc, ac in sorted(tuple(g) for g in (claimed or ())):
        if fc and ac and poses_of(n, ac) == fc:
            return (fc, ac), "record"
    return (max(n, 1), 1), "file"


def animations(art):
    """The animations this unit's art actually has, ready for a chip row.

    Returns a list sorted by reading order.  Each entry carries the grids the
    records claim for it (`claimed`) so the caller can show that 16 of them are
    ambiguous rather than pretending to have chosen correctly.
    """
    if not art or art.get("kind") != "loose":
        return []
    tokens = art.get("tokens") or {}
    labels = art.get("token_labels") or {}
    grids = art.get("grids") or {}
    out = []
    for key in sorted(tokens, key=order_key):
        out.append({"key": key,
                    "zh": anim_zh(key) or (labels.get(key) or key),
                    "file": tokens[key],
                    "claimed": [list(g) for g in sorted(grids.get(key) or ())]})
    return out


def _opaque(rgba):
    """True when any pixel has a non-zero alpha."""
    for i in range(3, len(rgba), 4):
        if rgba[i]:
            return True
    return False


def _pad(rgba, w, h, W, H):
    """Centre-ish a w x h canvas on a W x H one, top-left aligned.

    Frames inside one .sld can carry different canvas sizes -- a house's
    age states are 300x300 and 400x400 in the SAME file -- so the strip is laid
    out on the largest canvas rather than assuming the first frame's.
    """
    if w == W and h == H:
        return rgba
    out = bytearray(W * H * 4)
    for y in range(min(h, H)):
        src = y * w * 4
        dst = y * W * 4
        out[dst:dst + min(w, W) * 4] = rgba[src:src + min(w, W) * 4]
    return out


def _bbox(frames, w, h):
    """The content box shared by every frame, or None when all are transparent."""
    x1, y1, x2, y2 = w, h, -1, -1
    for rgba in frames:
        for y in range(h):
            row = y * w * 4 + 3
            for x in range(w):
                if rgba[row + x * 4]:
                    if x < x1:
                        x1 = x
                    if x > x2:
                        x2 = x
                    if y < y1:
                        y1 = y
                    if y > y2:
                        y2 = y
    return (x1, y1, x2 + 1, y2 + 1) if x2 >= 0 else None


def _lay(frames, w, h, box, gap=2, bg=(24, 24, 28, 255)):
    x1, y1, x2, y2 = box
    cw, ch = x2 - x1, y2 - y1
    n = len(frames)
    ow = cw * n + gap * (n - 1)
    out = bytearray(bytes(bg) * (ow * ch))
    for i, f in enumerate(frames):
        ox = i * (cw + gap)
        for y in range(ch):
            src = ((y1 + y) * w + x1) * 4
            dst = (y * ow + ox) * 4
            out[dst:dst + cw * 4] = f[src:src + cw * 4]
    return out, ow, ch


def _shadow_silhouette(info, w, h, rgba):
    """Paint a shadow-only frame as the silhouette the engine actually draws.

    `sld.render_frame` decodes the shadow plane and reports it, but never
    composites it: a shadow is meant to sit UNDER a main plane and the engine
    draws it as a soft dark blob.  148 of the 8,973 shipped animations are
    shadow-only files (`p_arrow_shadow_x1', every projectile's shadow, the town
    centre's `_shadow' states), and 34 of them are the same arrow.  Without this
    they render as 20 empty cells and the caller is told "these frames are all
    transparent" -- true of the main plane, useless to the reader.

    The mask is blitted where the shadow rect says it goes, at 60% black, which
    is what it looks like in game rather than a guess at the exact blend.  This
    is the only place this module invents anything, and what it invents is a
    blend factor, never a shape.
    """
    got = info.get("shadow_plane")
    rect = info.get("shadow_rect")
    if not got or not rect:
        return rgba
    plane, PW, _PH = got
    x1, y1, _rw, _rh, _bw, _bh = S.grid_of(rect)
    out = bytearray(rgba)
    for gy in range(len(plane) // max(PW, 1)):
        for gx in range(PW):
            m = plane[gy * PW + gx]
            if not m:
                continue
            sx, sy = x1 + gx, y1 + gy
            if not (0 <= sx < w and 0 <= sy < h):
                continue
            o = (sy * w + sx) * 4
            out[o:o + 4] = bytes((0, 0, 0, max((m * 3) // 5, out[o + 3])))
    return out


def strip(game_root, file_name, frames=20, start=0, angles=0, angle=0,
          team=(220, 60, 60), with_shadow=False, max_width=1200):
    """Render a run of poses of one .sld into a single PNG.

    `frames` counts POSES, not file records: with 16 angles, pose 5 is file index
    `5*16 + angle`, which is the engine's own indexing and the only one a player
    can reason about.  `angles` is the record's `angle_count`; pass 0 when the
    caller does not know and the file is read as one angle.

    Poses with no pixels are skipped and counted in `blank` rather than drawn as
    empty cells -- 360 of `b_dark_wall_palisade_flag_x1`'s 450 frames are
    frame_type 0x00, and that is the file being honest, not a parse failure.
    When EVERY pose is blank and the shadow layer was off, the run is retried
    once with the shadow on so a shadow-only file still shows something.

    `max_width` caps the row: a castle's 150-frame destruction at 347 px a frame
    is 52,050 px of picture, which no window scrolls usefully.  Frames past the
    cap are dropped from the END and counted in `trimmed`, so what the caller
    gets is always "the first N poses" and never a silently resampled animation.

    Returns `{ok, png, w, h, frames, asked, poses, blank, angles, angle, start,
    capped, trimmed, has_main, shadow_only, with_shadow, cropped, file}`.  Raises
    `FilmError` -- it never returns a blank picture.
    """
    path = os.path.join(SP.graphics_dir(game_root), file_name + ".sld")
    if not os.path.isfile(path):
        raise FilmError("这个游戏目录里没有这张图：%s.sld" % file_name)
    s = S.read_sld(path)
    n = int(s.num_frames or 0)
    if n <= 0:
        raise FilmError("这张图里一帧都没有：%s.sld" % file_name)
    ac = max(int(angles or 1), 1)
    poses = poses_of(n, ac) or n
    angle = max(0, min(int(angle), ac - 1))
    start = max(0, int(start))
    asked = int(frames or 20)
    if asked < 1:
        raise FilmError("至少要画一帧")
    capped = asked > MAX_FRAMES
    want = min(asked, MAX_FRAMES)

    def draw(shadow):
        got, blank, main, biggest = [], 0, False, (0, 0)
        for i in range(want):
            pose = start + i
            if pose >= poses:
                break
            idx = pose * ac + angle
            if idx >= n:
                break
            rgba, w, h, info = S.render_frame(s.frames[idx], team=team,
                                              with_shadow=shadow, with_pc=True)
            if shadow and not main and "main_rect" not in info:
                rgba = _shadow_silhouette(info, w, h, rgba)
            if "main_rect" in info:
                main = True
            if not _opaque(rgba):
                blank += 1
                continue
            biggest = (max(biggest[0], w), max(biggest[1], h))
            got.append((rgba, w, h))
        return got, blank, main, biggest

    got, blank, has_main, (W, H) = draw(with_shadow)
    shadow_only = False
    if not got and not with_shadow:
        got, blank, has_main, (W, H) = draw(True)
        if got:
            with_shadow, shadow_only = True, not has_main
    if not got:
        if blank:
            raise FilmError("这 %d 帧在这个朝向上一个像素都没有（整个文件 %d 帧）"
                            % (blank, n))
        raise FilmError("这个动作从第 %d 帧起就没有画面了（一共 %d 帧）"
                        % (start, poses))
    flat = [_pad(rgba, w, h, W, H) for rgba, w, h in got]
    box = _bbox(flat, W, H)
    if box is None:
        raise FilmError("这几帧全是透明的：%s.sld" % file_name)
    trimmed = 0
    cw = box[2] - box[0]
    if max_width and cw > 0:
        room = max(1, (int(max_width) + 2) // (cw + 2))
        if len(flat) > room:
            trimmed = len(flat) - room
            flat = flat[:room]
    rgba, ow, oh = _lay(flat, W, H, box)
    return {"ok": True,
            "png": D.encode_png(ow, oh, rgba),
            "w": ow, "h": oh,
            "frames": len(flat),
            "asked": asked,
            "poses": poses,
            "blank": blank,
            "angles": ac,
            "angle": angle,
            "start": start,
            "capped": capped,
            "trimmed": trimmed,
            "has_main": has_main,
            "shadow_only": shadow_only,
            "with_shadow": with_shadow,
            "cropped": list(box),
            "file": file_name}
