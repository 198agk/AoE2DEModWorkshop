# -*- coding: utf-8 -*-
"""Compare /api/icon output against the Python icon path, pixel for pixel.

Bytes cannot be compared (two zlib levels produce different PNGs of identical
pixels), so both sides are decoded back to RGBA. Three sizes are checked because
the resize path only runs above `max`: 0 (no resize), 64 (4x box filter), and 100
(factor 2, an uneven divisor of 256).
"""
import os
import struct
import sys
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import ddstex as D         # noqa: E402

BASE = "http://127.0.0.1:7873"


def rgba(blob):
    if blob[:4] == b"\x89PNG":
        pass
    else:
        raise ValueError(blob[:200])
    i = 8
    idat = b""
    w = h = None
    while i < len(blob):
        ln = struct.unpack_from(">I", blob, i)[0]
        k = blob[i + 4:i + 8]
        d = blob[i + 8:i + 8 + ln]
        if k == b"IHDR":
            w, h = struct.unpack_from(">II", d, 0)
        elif k == b"IDAT":
            idat += d
        elif k == b"IEND":
            break
        i += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 4
    out = bytearray()
    pos = 0
    for _y in range(h):
        pos += 1
        out += raw[pos:pos + stride]
        pos += stride
    return w, h, bytes(out)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    bad = 0
    total = 0
    for sid in (1, 15, 30, 60, 100, 200):
        got = tk.icons.picture("Units", sid)
        if not got.get("ok"):
            continue
        for max_side in (0, 64, 100):
            url = "%s/api/icon?kind=unit&id=%d&section=Units&max=%d" % (
                BASE, sid, max_side)
            try:
                b = urllib.request.urlopen(url, timeout=60).read()
            except Exception as exc:
                print("unit %-4d max=%-4d REQUEST FAILED %s" % (sid, max_side, exc))
                bad += 1
                continue
            try:
                rw, rh, rpx = rgba(b)
            except Exception as exc:
                print("unit %-4d max=%-4d UNREADABLE %s" % (sid, max_side, exc))
                bad += 1
                continue
            py = D.to_png(got["path"], max_side=max_side)
            pw, ph, ppx = rgba(py)
            total += 1
            same = (rw, rh, rpx) == (pw, ph, ppx)
            print("unit %-4d max=%-4d %dx%d %s"
                  % (sid, max_side, rw, rh, "ok" if same else "MISMATCH"))
            if not same:
                bad += 1
    print()
    print("ICON: %d/%d pixel-identical" % (total - bad, total))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
