# -*- coding: utf-8 -*-
"""probe_icon_sheet.py -- put several icons on ONE image, in a known order.

Reading twelve 256x256 files one at a time is slow and easy to misread; a grid
makes "which section holds which picture" a single look.  Order is fixed and
printed, so the grid is self-describing: cell (row, col) is IDS[row*cols+col].

Usage: probe_icon_sheet.py <Units|Buildings|Techs> id1 id2 ...
Writes _shots/icons/sheet_<section>.png and prints the layout.
"""
from __future__ import print_function

import codecs
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import probe_icon_look as LK  # decode(), png(), load(), resolve()


def main(argv):
    section = argv[1] if len(argv) > 1 else "Buildings"
    ids = [int(x) for x in argv[2:]] or [2, 7, 17, 28, 34, 35, 40, 58]
    cols = 4
    rows = (len(ids) + cols - 1) // cols
    cell = 128
    icons, atls, mats = LK.load()

    tiles = []
    for i in ids:
        got, why = LK.resolve(icons, atls, mats, section, i)
        if not got:
            print("  %-4d %s" % (i, why))
            tiles.append(None)
            continue
        mname, atlas, rel, fp = got
        try:
            w, h, rgba = LK.decode(fp)
        except Exception as exc:
            print("  %-4d %s (%s)" % (i, mname, exc))
            tiles.append(None)
            continue
        print("  cell %-2d id=%-4d %-30s %s" % (len(tiles), i, mname,
                                               os.path.basename(rel)))
        tiles.append((w, h, rgba))

    W, H = cols * cell, rows * cell
    out = bytearray(W * H * 4)
    for idx, tile in enumerate(tiles):
        r, c = divmod(idx, cols)
        for y in range(cell):
            for x in range(cell):
                o = ((r * cell + y) * W + (c * cell + x)) * 4
                if tile is None:
                    out[o:o + 4] = bytes((40, 40, 40, 255))
                    continue
                w, h, rgba = tile
                sx = min(w - 1, x * w // cell)
                sy = min(h - 1, y * h // cell)
                s = (sy * w + sx) * 4
                out[o:o + 4] = rgba[s:s + 4]
    path = os.path.join(LK.OUT, "sheet_%s.png" % section)
    if not os.path.isdir(LK.OUT):
        os.makedirs(LK.OUT)
    LK.png(path, W, H, bytes(out), scale=1, checker=True)
    print("\nwrote %s  (%dx%d, %d cols)" % (path, W, H, cols))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv))
