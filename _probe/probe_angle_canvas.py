# -*- coding: utf-8 -*-
"""Is the block grid a property of the ANGLE, not of the frame?

An SLD holds frame_count x angle_count frames.  The pipeline needs to know
whether one picture can cover an animation, or whether each direction needs its
own drawing.  This probe answers it by measuring, for one file:
  * how many distinct rects there are
  * whether the rect changes exactly on a stride of frame_count
  * what a per-angle picture would have to be
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sldlib as S
import sldencode as E

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"


def analyse(name, frame_count=None, angle_count=None):
    s = S.read_sld(os.path.join(GP, name))
    rects = []
    for fr in s.frames:
        m = fr.layers.get("main")
        if m is None:
            rects.append(None)
            continue
        rects.append(S.parse_rect_layer(m)[0])
    n = len(s.frames)
    distinct = collections.Counter(rects)
    print("%-36s frames %4d  distinct rects %d" % (name, n, len(distinct)))

    # do equal rects always sit in one unbroken run?
    runs = []
    for r in rects:
        if runs and runs[-1][0] == r:
            runs[-1][1] += 1
        else:
            runs.append([r, 1])
    print("   runs of equal rect: %d  (lengths %s)"
          % (len(runs), sorted(set(r[1] for r in runs))))

    # if the animation has angle_count directions, is each direction one run?
    if angle_count:
        fc = n // angle_count
        per_angle = [tuple(rects[a * fc:(a + 1) * fc]) for a in range(angle_count)]
        uniq = len(set(per_angle))
        print("   frames per angle if angle_count=%d: %d -> distinct angle "
              "signatures: %d" % (angle_count, fc, uniq))
        if uniq == angle_count:
            print("   => EVERY direction has its own canvas; one picture cannot "
                  "cover the animation")
        elif uniq == 1:
            print("   => one canvas for all directions")
        else:
            print("   => some directions share a canvas")
        sig = collections.Counter(per_angle)
        print("   directions per signature: %s"
              % sorted(sig.values(), reverse=True))

    # grid size per distinct rect
    print("   grids: %s" % sorted((S.grid_of(r)[4:] if r else None,
                                   c) for r, c in distinct.items()
                                  if r is not None))
    return rects


def main():
    analyse("a_herd_sheep_idleA_x1.sld", angle_count=16)
    print()
    analyse("u_arc_archer_idleA_x1.sld", angle_count=16)
    print()
    analyse("u_vil_male_villager_idleA_x1.sld", angle_count=16)
    print()
    analyse("b_dark_barracks_age1_x1.sld", angle_count=1)
    print()
    analyse("u_shp_fishing_ship_x1.sld", angle_count=16)
    return 0


if __name__ == "__main__":
    sys.exit(main())
