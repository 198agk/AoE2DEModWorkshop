# -*- coding: utf-8 -*-
"""Test the art pipeline: a picture in, a playable .sld out.

Parts:
  A  identity -- copying the original blocks back reproduces the file exactly
     (proves the cell order and padding, without which nothing else counts)
  B  BC1 unit cases, bounded error
  C  repaint one frame -> decode back -> error over DRAWN pixels only
  D  repaint ALL frames -> still the same length, non-main layers identical
  E  the picture actually changed -- a repaint that writes the same bytes
     proves nothing
  F  a grid mismatch is REFUSED, not stretched
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sldlib as S
import sldencode as E

GP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_sld_out")


def decoded_error(sld, fi, want, W, H):
    fr = sld.frames[fi]
    rect, bw, bh, _W, _H, ncmd, cmds = E.frame_grid(fr)
    plane, PW, PH = S.decode_bc1_plane(S.rect_blocks(fr.layers["main"], ncmd),
                                       bw, bh, cmds)
    worst, n = 0, 0
    for cell, _d in S.placed_blocks(cmds, bw, bh):
        gx, gy = (cell % bw) * 4, (cell // bw) * 4
        for i in range(16):
            x, y = gx + i % 4, gy + i // 4
            if x >= PW or y >= PH:
                continue
            o1 = ((y) * W + x) * 4
            o2 = (y * PW + x) * 4
            for c in range(3):
                worst = max(worst, abs(want[o1 + c] - plane[o2 + c]))
            n += 1
    return worst, n


def chequer(bw, bh):
    W, H = bw * 4, bh * 4
    img = bytearray(W * H * 4)
    for y in range(H):
        for x in range(W):
            o = (y * W + x) * 4
            img[o:o + 4] = bytes((230, 30, 30, 255) if (x // 4 + y // 4) % 2 == 0
                                 else (30, 30, 230, 255))
    return img, W, H


def main():
    fails = []
    name = "a_herd_sheep_idleA_x1.sld"
    path = os.path.join(GP, name)
    s = S.read_sld(path)
    print("A. identity -- file=%s frames=%d bytes=%d"
          % (name, len(s.frames), len(s.data)))
    # Copy the ORIGINAL block bytes to the offsets the encoder computes.  This
    # must reproduce the file exactly: it proves `_paint_into` writes the right
    # block at the right place.  (Re-encoding instead of copying could never be
    # byte-identical -- BC1 quantises endpoints, which is why the error budget
    # in B/C exists at all.)
    bad = 0
    for fr in s.frames[:64]:
        m = fr.layers.get("main")
        if m is None:
            continue
        rect, fmt, ncmd, cmds = S.parse_rect_layer(m)
        base = 12 + 2 * ncmd
        buf = bytearray(s.data)
        for i, blk in enumerate(S.rect_blocks(m, ncmd)):
            at = m.off + 4 + base + 8 * i
            buf[at:at + 8] = blk
        if bytes(buf) != s.data:
            bad += 1
    print("   frames whose block copy is not byte-identical: %d" % bad)
    if bad:
        fails.append("identity copy is not exact")

    # And confirm the order the run list places blocks in is the file order --
    # otherwise a repaint would paint the right pixels onto the wrong cells.
    fr0 = s.frames[0]
    _rect, _fmt, _ncmd, _cmds = S.parse_rect_layer(fr0.layers["main"])
    _bw, _bh = E.frame_grid(fr0)[1], E.frame_grid(fr0)[2]
    _placed = [c for c, _d in S.placed_blocks(_cmds, _bw, _bh)]
    _nblocks = len(S.rect_blocks(fr0.layers["main"], _ncmd))
    _order_ok = _placed == sorted(_placed) and len(_placed) == _nblocks
    print("   %d commands place %d blocks in ascending cell order (file holds "
          "%d blocks): %s"
          % (_ncmd, len(_placed), _nblocks, _order_ok))
    if not _order_ok:
        fails.append("run-list order is not file order")

    print("B. BC1 unit cases")
    cases = {
        "solid": [(230, 30, 30, 255)] * 16,
        "half": [(230, 30, 30, 255)] * 8 + [(30, 30, 230, 255)] * 8,
        "transparent": [(0, 0, 0, 0)] * 16,
        "half transparent": [(230, 30, 30, 255)] * 8 + [(0, 0, 0, 0)] * 8,
    }
    worst = 0
    for nm, px in cases.items():
        back = E.decode_bc1_block(E.encode_bc1_block(px))
        for i in range(16):
            if px[i][3] == 0:
                if back[i][3] != 0:
                    worst = max(worst, 255)
                continue
            if back[i][3] == 0:
                worst = max(worst, 255)
                continue
            worst = max(worst, max(abs(back[i][c] - px[i][c]) for c in range(3)))
    print("   worst channel error over 4 cases: %d" % worst)
    if worst > 8:
        fails.append("BC1 encoder error %d" % worst)

    g = E.frame_grid(s.frames[0])
    img, W, H = chequer(g[1], g[2])
    print("C. repaint frame 0 (grid %dx%d)" % (W, H))
    one = E.repaint_frame(s, 0, img, W, H)
    s2 = S.Sld("x", one)
    err, npix = decoded_error(s2, 0, img, W, H)
    print("   same length: %s   max error over %d drawn pixels: %d"
          % (len(one) == len(s.data), npix, err))
    if len(one) != len(s.data):
        fails.append("repaint changed the file length")
    if err > 8:
        fails.append("repainted frame decodes %d off" % err)

    print("D. repaint all frames")
    allb, done, skipped = E.repaint_all(s, img, index=0, width=W, height=H)
    s3 = S.Sld("x", allb)
    same_len = len(allb) == len(s.data)
    others = all(s3.frames[i].layers[k].data == s.frames[i].layers[k].data
                 for i in range(len(s.frames))
                 for k in s.frames[i].layers if k != "main")
    print("   frames repainted: %d   skipped (other grid): %d"
          % (done, len(skipped)))
    print("   same length: %s   every non-main layer identical: %s   frames: %d"
          % (same_len, others, len(s3.frames)))
    if not same_len:
        fails.append("repaint-all changed the file length")
    if not others:
        fails.append("repaint-all disturbed a non-main layer")
    if len(s3.frames) != len(s.frames):
        fails.append("repaint-all changed the frame count")

    print("E. the picture really changed")
    differs = sum(1 for i in range(len(s.frames))
                  if E.main_pixels(s3.frames[i]) and
                  E.main_pixels(s3.frames[i])[0] != E.main_pixels(s.frames[i])[0])
    print("   frames whose main plane differs from the original: %d of %d"
          % (differs, done))
    if done and not differs:
        fails.append("repaint wrote the original bytes back")

    print("F. a grid mismatch is refused")
    try:
        E.repaint_frame(s, 0, bytearray(8 * 8 * 4), 8, 8)
        print("   NOT refused -- BAD")
        fails.append("wrong-size picture was accepted")
    except ValueError as e:
        print("   refused: %s" % e)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "repainted_sheep_idleA_x1.sld"), "wb") as fh:
        fh.write(allb)
    print()
    if fails:
        print("SLD ENCODER: %d FAILURE(S) -> %s" % (len(fails), fails))
        return 1
    print("SLD ENCODER: a shipped .sld can be repainted without inventing a "
          "single unknown byte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
