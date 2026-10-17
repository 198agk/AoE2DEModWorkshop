# -*- coding: utf-8 -*-
"""The art pipeline's real unit: a CANVAS-sized picture sampled at each frame.

Each frame's `main` layer carries a rect (x1,y1,x2,y2) that is the TIGHT crop
of the canvas that frame draws.  Those crops move from frame to frame -- that
motion is the original animation.  So one drawing, in canvas coordinates, can
drive a whole animation: sample the drawing at each frame's own rect and the
original motion survives.

This probe measures that claim rather than asserting it:
  1  rects are (x1,y1,x2,y2) inside the canvas -- correct the earlier misparse
  2  paint a smooth canvas picture into every frame, decode back, measure error
  3  render a montage from the SHIPPED file and from the repainted one
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sldlib as S
import sldencode as E

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "_shots", "artpipe")


def rect_of(fr):
    m = fr.layers.get("main")
    if m is None:
        return None
    x1, y1, x2, y2 = S.parse_rect_layer(m)[0]
    return x1, y1, x2 - x1, y2 - y1


def check_rects(name):
    s = S.read_sld(os.path.join(GP, name))
    out = 0
    for f in s.frames:
        r = rect_of(f)
        if r is None:
            continue
        if r[0] + r[2] > f.canvas_w or r[1] + r[3] > f.canvas_h:
            out += 1
    cw = {f.canvas_w for f in s.frames}
    ch = {f.canvas_h for f in s.frames}
    print("   canvas %sx%s   rects outside canvas: %d of %d"
          % (sorted(cw), sorted(ch), out, len(s.frames)))
    return s, out


def circle_picture(CW, CH, r=64):
    """A picture whose shape shows immediately if a frame samples it wrong."""
    pic = bytearray(CW * CH * 4)
    cx, cy = CW / 2.0, CH / 2.0
    for y in range(CH):
        for x in range(CW):
            o = (y * CW + x) * 4
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d <= r:
                k = int(80 + 175 * (1 - d / r))
                pic[o:o + 4] = bytes((k, int(k * 0.55), 40, 255))
    return pic


def paint_canvas(name, pic=None, frames=None):
    s = S.read_sld(os.path.join(GP, name))
    CW, CH = s.frames[0].canvas_w, s.frames[0].canvas_h
    if pic is None:
        pic = circle_picture(CW, CH)
    if frames is not None:
        s = S.Sld(s.path, s.data)
    buf = bytearray(s.data)
    done, skipped = 0, 0
    for f in s.frames:
        g = E.frame_grid(f)
        if g is None:
            skipped += 1
            continue
        x1, y1, W, H = g[0][0], g[0][1], g[3], g[4]
        E.paint_blocks(buf, f, E.sample_canvas(pic, CW, CH, x1, y1, W, H), W, H)
        done += 1
    out = bytes(buf)
    s2 = S.Sld(name, out)
    worst = 0
    for f in s.frames:
        g = E.frame_grid(f)
        if g is None:
            continue
        x1, y1, W, H = g[0][0], g[0][1], g[3], g[4]
        want = E.sample_canvas(pic, CW, CH, x1, y1, W, H)
        got = E.main_pixels(s2.frames[f.index])[0]
        # Only the cells the run list actually draws carry pixels.  Comparing
        # the whole grid counts the by-design-empty cells as error -- that
        # measurement mistake once read as "the encoder is broken" when the
        # encoder was fine.
        for cell, _d in S.placed_blocks(g[6], g[1], g[2]):
            gx, gy = (cell % g[1]) * 4, (cell // g[1]) * 4
            for i in range(16):
                x, y = gx + i % 4, gy + i // 4
                o = (y * W + x) * 4
                if want[o + 3] == 0 and got[o + 3] == 0:
                    continue
                for c in range(3):
                    worst = max(worst, abs(want[o + c] - got[o + c]))
    print("   painted %d frames (%d without main), %d bytes -> %d"
          % (done, skipped, len(s.data), len(out)))
    print("   worst channel error over EVERY frame: %d" % worst)
    return out, CW, CH, worst, s


def montage_shipped(s, tag, idxs):
    from PIL import Image
    tiles = []
    for i in idxs:
        canvas, w, h, _info = S.render_frame(s.frames[i])
        img = Image.frombytes("RGBA", (w, h), bytes(canvas))
        bb = img.getbbox()
        if bb:
            img = img.crop(bb)
        tiles.append(img)
    tw = max(1, max(t.width for t in tiles))
    th = max(1, max(t.height for t in tiles))
    sh = Image.new("RGBA", (tw * len(tiles), th), (24, 24, 28, 255))
    for i, t in enumerate(tiles):
        sh.paste(t, (i * tw + (tw - t.width) // 2, (th - t.height) // 2), t)
    os.makedirs(SHOTS, exist_ok=True)
    p = os.path.join(SHOTS, tag + ".png")
    sh.convert("RGB").save(p)
    print("   -> %s (%dx%d, %d tiles)" % (p, sh.width, sh.height, len(tiles)))
    return p


def main():
    fails = []
    for name in ("a_herd_sheep_idleA_x1.sld", "u_arc_archer_idleA_x1.sld"):
        print(name)
        s, out = check_rects(name)
        if out:
            fails.append("%s: %d rects outside the canvas" % (name, out))
        outb, CW, CH, worst, s0 = paint_canvas(name)
        if worst > 12:
            fails.append("%s: repaint error %d" % (name, worst))
        idxs = [0, 1, 30, 61, 200, 700]
        print("   shipped art:")
        montage_shipped(s0, name.replace(".sld", "") + "__shipped", idxs)
        print("   repainted art:")
        montage_shipped(S.Sld("x", outb),
                        name.replace(".sld", "") + "__painted", idxs)
        print()
    if fails:
        print("CANVAS MODEL: %d PROBLEM(S) -> %s" % (len(fails), fails))
        return 1
    print("CANVAS MODEL: one canvas-sized picture drives a whole animation, and "
          "the motion the original encoded in its per-frame crops survives.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
