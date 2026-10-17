# -*- coding: utf-8 -*-
"""Does the x2 file of an animation have exactly double the canvas and rects?

If yes, one user picture can drive both resolutions by scaling it to each
file's own canvas, and the product must emit BOTH files (the engine derives
`_x2` from `_x1`, so shipping only x1 leaves UHD users with the old art).
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sldlib as S
import sldencode as E

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"


def main():
    fails = []
    names = ["a_herd_sheep_idleA", "u_arc_archer_idleA",
             "u_vil_male_villager_idleA", "u_inf_champi_scout_idleA",
             "u_arc_longbowman_walkA", "u_monk_west_attackA"]
    for stem in names:
        p1 = os.path.join(GP, stem + "_x1.sld")
        p2 = os.path.join(GP, stem + "_x2.sld")
        if not (os.path.exists(p1) and os.path.exists(p2)):
            print("%-32s MISSING (x1 %s x2 %s)"
                  % (stem, os.path.exists(p1), os.path.exists(p2)))
            fails.append(stem + ": missing pair")
            continue
        s1 = S.read_sld(p1)
        s2 = S.read_sld(p2)
        c1 = collections.Counter((f.canvas_w, f.canvas_h) for f in s1.frames)
        c2 = collections.Counter((f.canvas_w, f.canvas_h) for f in s2.frames)
        g1 = collections.Counter()
        g2 = collections.Counter()
        for f in s1.frames:
            g = E.frame_grid(f)
            if g:
                g1[(g[0][0], g[0][1], g[3], g[4])] += 1
        for f in s2.frames:
            g = E.frame_grid(f)
            if g:
                g2[(g[0][0], g[0][1], g[3], g[4])] += 1
        k1 = (list(c1)[0] if len(c1) == 1 else None)
        k2 = (list(c2)[0] if len(c2) == 1 else None)
        doubled = bool(k1 and k2 and k2[0] == 2 * k1[0] and k2[1] == 2 * k1[1])
        # are the x2 rects exactly 2x the x1 rects, frame by frame?
        exact = 0
        pairs = 0
        for f1, f2 in zip(s1.frames, s2.frames):
            a = E.frame_grid(f1)
            b = E.frame_grid(f2)
            if not a or not b:
                continue
            pairs += 1
            if (b[0][0], b[0][1]) == (2 * a[0][0], 2 * a[0][1]) and \
                    (b[3], b[4]) == (2 * a[3], 2 * a[4]):
                exact += 1
        print("%-32s x1 %dx%d (%d frames)  x2 %s  doubled %s  "
              "frame rects exactly 2x: %d/%d"
              % (stem, k1[0] if k1 else -1, k1[1] if k1 else -1,
                 len(s1.frames), ("%dx%d" % k2) if k2 else "varies",
                 doubled, exact, pairs))
        print("    distinct x1 rects %d / x2 rects %d   bytes %d / %d"
              % (len(g1), len(g2), len(s1.data), len(s2.data)))
        if not doubled:
            fails.append(stem + ": x2 canvas is not exactly double")
    print()
    if fails:
        print("X1/X2: %d PROBLEM(S) -> %s" % (len(fails), fails))
        return 1
    print("X1/X2: every x2 canvas is exactly double the x1 canvas, so one "
          "picture scaled to each file's own canvas drives both.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
