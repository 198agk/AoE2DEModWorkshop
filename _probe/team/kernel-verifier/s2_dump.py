# -*- coding: utf-8 -*-
"""Dump raw context around the changed offsets and around 'Archer'/'ARCHR'."""
import re
import zlib

DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
NEW = r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat"


def inflate(path):
    d = zlib.decompressobj(-15)
    return d.decompress(open(path, "rb").read()) + d.flush()


def hexw(b, start):
    return " ".join("%02x" % c for c in b)


def main():
    base = inflate(DAT)
    new = inflate(NEW)
    diffs = [i for i in range(len(base)) if base[i] != new[i]]
    d0 = diffs[0]
    print("first changed offset", d0)
    lo, hi = d0 - 96, d0 + 48
    print("BASE @%d-%d" % (lo, hi))
    print(hexw(base[lo:hi], lo))
    print("NEW  same window")
    print(hexw(new[lo:hi], lo))

    # printable strings in a wider window
    def strings(blob, lo, hi):
        out, cur, start = [], "", None
        for i in range(lo, hi):
            c = blob[i]
            if 32 <= c < 127:
                if start is None:
                    start = i
                cur += chr(c)
            else:
                if start is not None and len(cur) >= 3:
                    out.append((start, cur))
                cur, start = "", None
        if start is not None and len(cur) >= 3:
            out.append((start, cur))
        return out

    print("strings within -1200..+1200:")
    for off, s in strings(base, max(0, d0 - 1200), d0 + 1200):
        print("   %d %+d %r" % (off, off - d0, s))

    print()
    print("contexts of b'ARCHR' (first 3):")
    for m in list(re.finditer(re.escape(b"ARCHR"), base))[:3]:
        p = m.start()
        print("   @%d  %s | %s" % (p, hexw(base[p - 12:p + 12], p - 12),
                                   base[p - 12:p + 12]))
    print("contexts of b'Archer' (first 3):")
    for m in list(re.finditer(re.escape(b"Archer"), base))[:3]:
        p = m.start()
        print("   @%d  %s | %s" % (p, hexw(base[p - 12:p + 12], p - 12),
                                   base[p - 12:p + 12]))


if __name__ == "__main__":
    main()
