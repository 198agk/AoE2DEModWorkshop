# -*- coding: utf-8 -*-
"""Where exactly does the canvas repaint lose 255?  Locate it, do not guess."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sldlib as S
import sldencode as E

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"


def circle(CW, CH, r=64):
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


def main():
    name = "a_herd_sheep_idleA_x1.sld"
    s = S.read_sld(os.path.join(GP, name))
    CW, CH = s.frames[0].canvas_w, s.frames[0].canvas_h
    pic = circle(CW, CH)
    print("canvas %dx%d" % (CW, CH))

    for fi in (0, 1, 61, 200, 700):
        f = s.frames[fi]
        g = E.frame_grid(f)
        rect, bw, bh, W, H, ncmd, cmds = g
        x1, y1 = rect[0], rect[1]
        sub = E.sample_canvas(pic, CW, CH, x1, y1, W, H)
        n_alpha = sum(1 for i in range(W * H) if sub[i * 4 + 3])
        placed = S.placed_blocks(cmds, bw, bh)
        print("\nframe %3d rect=%s grid=%dx%d cells=%d placed=%d ncmd=%d "
              "sub-opaque=%d/%d"
              % (fi, rect, bw, bh, bw * bh, len(placed), ncmd, n_alpha, W * H))

        # encode/decode one block that is fully opaque, one fully transparent,
        # one mixed -- at the picture's own coordinates
        for label, cell in (("first", placed[0][0]),
                            ("last", placed[-1][0]),
                            ("mid", placed[len(placed) // 2][0])):
            gx, gy = (cell % bw) * 4, (cell // bw) * 4
            px = [tuple(sub[((gy + i // 4) * W + (gx + i % 4)) * 4:
                            ((gy + i // 4) * W + (gx + i % 4)) * 4 + 4])
                  for i in range(16)]
            blk = E.encode_bc1_block(px)
            back = E.decode_bc1_block(blk)
            err = 0
            for i in range(16):
                if px[i][3] == 0 and back[i][3] == 0:
                    continue
                if (px[i][3] == 0) != (back[i][3] == 0):
                    err = max(err, 255)
                    continue
                err = max(err, max(abs(back[i][c] - px[i][c]) for c in range(3)))
            print("   cell %3d px0=%s px15=%s -> err %d  c0c1=%04x/%04x"
                  % (cell, px[0], px[15], err, blk[0] | blk[1] << 8,
                     blk[2] | blk[3] << 8))

        # now paint only this frame and compare
        buf = bytearray(s.data)
        E.paint_blocks(buf, f, sub, W, H)
        s2 = S.Sld("x", bytes(buf))
        got = E.main_pixels(s2.frames[fi])[0]
        worst, at = 0, None
        for i in range(W * H):
            if sub[i * 4 + 3] == 0 and got[i * 4 + 3] == 0:
                continue
            if (sub[i * 4 + 3] == 0) != (got[i * 4 + 3] == 0):
                d = 255
            else:
                d = max(abs(sub[i * 4 + c] - got[i * 4 + c]) for c in range(3))
            if d > worst:
                worst, at = d, i
        print("   painted frame alone, decoded back: worst %d at pixel %s "
              "(want %s got %s)"
              % (worst, at,
                 tuple(sub[at * 4:at * 4 + 4]) if at is not None else None,
                 tuple(got[at * 4:at * 4 + 4]) if at is not None else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
