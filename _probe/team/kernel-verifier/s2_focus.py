# -*- coding: utf-8 -*-
"""Focused dump of the changed-offset geometry (stdlib only)."""
import struct
import zlib

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
MOD = (r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch"
       r"\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat")


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


def hx(b, lo, hi):
    return " ".join("%02x" % c for c in b[lo:hi])


def main():
    b = inflate(BASE)
    n = inflate(MOD)
    diffs = [i for i in range(len(b)) if b[i] != n[i]]
    pairs = [(diffs[i], diffs[i + 1]) for i in range(0, len(diffs), 2)]
    print("pairs:", len(pairs))
    for a, m in pairs[:4]:
        print("pair a=%d m=%d gap=%d" % (a, m, m - a))
        print("  base a-12..a+8 :", hx(b, a - 12, a + 8))
        print("  new  a-12..a+8 :", hx(n, a - 12, a + 8))
        print("  base m-12..m+8 :", hx(b, m - 12, m + 8))
        print("  new  m-12..m+8 :", hx(n, m - 12, m + 8))
        for align in (a - 1, a):
            print("   u16@%d base=%d new=%d"
                  % (align, struct.unpack_from("<H", b, align)[0],
                     struct.unpack_from("<H", n, align)[0]))
        for base_off in (m - 3, m - 2, m - 1, m):
            print("   f32@%d base=%.6f new=%.6f"
                  % (base_off, struct.unpack_from("<f", b, base_off)[0],
                     struct.unpack_from("<f", n, base_off)[0]))
        print("  i32@a-3 base=%d new=%d"
              % (struct.unpack_from("<i", b, a - 3)[0],
                 struct.unpack_from("<i", n, a - 3)[0]))

    # per-pair alignment census
    ca, cm = {}, {}
    for a, m in pairs:
        key = None
        for align in (a - 1, a, a - 2, a - 3):
            if struct.unpack_from("<H", b, align)[0] == 4 and \
               struct.unpack_from("<H", n, align)[0] == 6:
                key = align - a
                break
        ca[key] = ca.get(key, 0) + 1
        key2 = None
        for off in (m - 3, m - 2, m - 1, m, m - 4):
            if struct.unpack_from("<f", b, off)[0] == 4.0 and \
               struct.unpack_from("<f", n, off)[0] == 6.0:
                key2 = off - m
                break
        cm[key2] = cm.get(key2, 0) + 1
    print("primary u16 alignment offsets (relative):", ca)
    print("mirror f32 alignment offsets (relative) :", cm)

    # byte before/after each changed byte, as a table
    ctx = {}
    for a, m in pairs:
        k = (b[a - 1], b[a], b[a + 1], n[a])
        ctx[k] = ctx.get(k, 0) + 1
    print("primary context (prev, before, next, after):", ctx)
    ctx2 = {}
    for a, m in pairs:
        k = (b[m - 1], b[m], b[m + 1], n[m])
        ctx2[k] = ctx2.get(k, 0) + 1
    print("mirror  context (prev, before, next, after):", ctx2)


if __name__ == "__main__":
    main()
