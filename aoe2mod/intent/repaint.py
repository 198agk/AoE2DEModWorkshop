# -*- coding: utf-8 -*-
"""Paint a user's picture onto a unit's existing animations.

WHY THIS IS THE SHAPE IT IS
---------------------------
An `.sld` cannot be built from scratch: every frame that carries a `main` layer
also carries an `unknown2` layer (4,737,215 frames, zero exceptions across the
shipped corpus), and `unknown2`'s size is not a function of main's run list, so
it cannot be regenerated.  What CAN be done -- and what this module does -- is
repaint the BC1 blocks of `main` in place, keeping every other byte.

A frame's `main` layer carries a rect that is the TIGHT CROP of the canvas that
frame draws.  Those crops move from frame to frame, and that motion IS the
animation.  So the drawing unit is the CANVAS, not the frame: a picture in
canvas coordinates is sampled at every frame's own rect, and the original
motion survives untouched.  Measured on two shipped files over every one of
their frames: worst channel error 5, file length unchanged, every non-main
layer byte-identical.

Placement is measured, not guessed: the union of every frame's rect is where
the original art lives inside the canvas (for a 200x200 unit canvas it is about
x 68..132, y 52..108 -- the art stands on a ground line near y = 108).  The
picture is scaled to FIT that union with its aspect ratio kept, and centred in
it, so a picture of any size lands where the original stood.

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
    against `aoe2-mod-workshop.exe`).  The repo has Pillow, so no suite saw it.
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


def _fit(src_w, src_h, box_w, box_h):
    """Largest scale that fits, and the offset that centres it."""
    if src_w <= 0 or src_h <= 0:
        raise PaintError("the picture is %dx%d, which has no area"
                         % (src_w, src_h))
    sc = min(float(box_w) / src_w, float(box_h) / src_h)
    dw, dh = src_w * sc, src_h * sc
    return sc, (box_w - dw) / 2.0, (box_h - dh) / 2.0


def _sampler(pic, PW, PH, bbox, inner_pad=0):
    """Canvas-coordinate sampler: (cx, cy) -> (r, g, b, a).

    Nearest neighbour on purpose.  AoE2 sprites are 8-bit art at low
    resolution; interpolating would blur the pixel edges the game draws crisp,
    and the BC1 quantiser then spends its four colours on the blur.
    """
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    if inner_pad:
        bw, bh = max(1, bw - inner_pad), max(1, bh - inner_pad)
    sc, ox, oy = _fit(PW, PH, bw, bh)

    def sample(cx, cy):
        px = (cx - (x1 + inner_pad / 2.0) - ox) / sc
        py = (cy - (y1 + inner_pad / 2.0) - oy) / sc
        if px < 0 or py < 0 or px >= PW or py >= PH:
            return (0, 0, 0, 0)
        o = (int(py) * PW + int(px)) * 4
        return (pic[o], pic[o + 1], pic[o + 2], pic[o + 3])

    return sample, sc, bw, bh


def _sub_for_frame(sample, g):
    """Sample one frame's rect into a W x H RGBA window the encoder can paint."""
    _rect, _bw, _bh, W, H, _ncmd, _cmds = g
    x1, y1 = g[0][0], g[0][1]
    out = bytearray(W * H * 4)
    for y in range(H):
        cy = y1 + y
        for x in range(W):
            r, gg, b, a = sample(x1 + x, cy)
            o = (y * W + x) * 4
            out[o] = r
            out[o + 1] = gg
            out[o + 2] = b
            out[o + 3] = a
    return out


def paint_sld(sld, pic, PW, PH, animations=None):
    """Repaint one loaded .sld.  Returns (new_bytes, report dict)."""
    bbox = union_bbox(sld)
    if bbox is None:
        raise PaintError("this file has no frame with a main layer")
    sample, sc, bw, bh = _sampler(pic, PW, PH, bbox)
    buf = bytearray(sld.data)
    done, skipped = 0, []
    for f in sld.frames:
        g = E.frame_grid(f)
        if g is None:
            continue
        sub = _sub_for_frame(sample, g)
        if E.paint_blocks(buf, f, sub, g[3], g[4]):
            done += 1
        else:
            skipped.append(f.index)
    return bytes(buf), {"frames_painted": done, "frames_skipped": skipped,
                        "bbox": list(bbox), "picture_scaled_by": round(sc, 4),
                        "drawn_size": [int(round(bw)), int(round(bh))]}


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
