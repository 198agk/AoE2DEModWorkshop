# -*- coding: utf-8 -*-
"""Why does repaint_all skip 780 of 960 frames?  Measure the grid per frame.

The answer decides the art pipeline's shape: if grids vary per frame, one
square picture cannot cover an animation, and the pipeline must work in
frame groups.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sldlib as S
import sldencode as E

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"


def hist(name):
    s = S.read_sld(os.path.join(GP, name))
    c = collections.Counter()
    for fr in s.frames:
        g = E.frame_grid(fr)
        c[None if g is None else (g[3], g[4])] += 1
    print("%-38s frames %4d  grids %s" % (name, len(s.frames), dict(c)))
    return c


def main():
    for n in ("a_herd_sheep_idleA_x1.sld",
              "a_herd_sheep_walkA_x1.sld",
              "u_arc_archer_idleA_x1.sld",
              "u_vil_male_villager_idleA_x1.sld",
              "u_inf_champi_scout_idleA_x1.sld",
              "b_dark_barracks_age1_x1.sld"):
        hist(n)

    print()
    print("the sheep idle file, frame by frame (first 40):")
    s = S.read_sld(os.path.join(GP, "a_herd_sheep_idleA_x1.sld"))
    for fr in s.frames[:40]:
        m = fr.layers.get("main")
        if m is None:
            print("  frame %2d  no main" % fr.index)
            continue
        rect, fmt, ncmd, cmds = S.parse_rect_layer(m)
        print("  frame %2d  rect=%s  ncmd=%d  sum(draw)=%d"
              % (fr.index, rect, ncmd, sum(d for _c, d in cmds)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
