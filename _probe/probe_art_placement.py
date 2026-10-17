# -*- coding: utf-8 -*-
"""Where does the art sit inside the canvas?  Needed to place a user picture.

A picture dropped into a canvas has to stand where the original stood, or the
sprite floats or sinks.  Measure the union bbox of every frame's main rect,
per file, and relative to the canvas.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sldlib as S
import sldencode as E

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"


def union_bbox(name):
    s = S.read_sld(os.path.join(GP, name))
    CW, CH = s.frames[0].canvas_w, s.frames[0].canvas_h
    xs, ys, xe, ye = 9999, 9999, 0, 0
    n = 0
    for f in s.frames:
        g = E.frame_grid(f)
        if g is None:
            continue
        x1, y1, W, H = g[0][0], g[0][1], g[3], g[4]
        xs, ys = min(xs, x1), min(ys, y1)
        xe, ye = max(xe, x1 + W), max(ye, y1 + H)
        n += 1
    print("%-34s canvas %3dx%-3d  union bbox x %3d..%-3d y %3d..%-3d  "
          "(%.0f%% wide, %.0f%% tall)  frames %d"
          % (name, CW, CH, xs, xe, ys, ye,
             100.0 * (xe - xs) / CW, 100.0 * (ye - ys) / CH, n))
    return CW, CH, xs, ys, xe, ye


def main():
    for n in ("a_herd_sheep_idleA_x1.sld", "a_herd_sheep_walkA_x1.sld",
              "u_arc_archer_idleA_x1.sld", "u_arc_archer_walkA_x1.sld",
              "u_vil_male_villager_idleA_x1.sld",
              "u_vil_male_villager_walkA_x1.sld",
              "u_inf_champi_scout_idleA_x1.sld",
              "b_dark_barracks_age1_x1.sld"):
        union_bbox(n)

    print()
    print("per-direction union bbox for archer idle (16 directions):")
    s = S.read_sld(os.path.join(GP, "u_arc_archer_idleA_x1.sld"))
    fc = len(s.frames) // 16
    for a in range(16):
        xs, ys, xe, ye = 9999, 9999, 0, 0
        for f in s.frames[a * fc:(a + 1) * fc]:
            g = E.frame_grid(f)
            if g is None:
                continue
            x1, y1, W, H = g[0][0], g[0][1], g[3], g[4]
            xs, ys = min(xs, x1), min(ys, y1)
            xe, ye = max(xe, x1 + W), max(ye, y1 + H)
        print("  dir %2d  x %3d..%-3d  y %3d..%-3d  centre (%5.1f,%5.1f)"
              % (a, xs, xe, ys, ye, (xs + xe) / 2.0, (ys + ye) / 2.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
