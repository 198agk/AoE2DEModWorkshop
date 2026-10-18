# -*- coding: utf-8 -*-
"""CLAIM 2 final -- everything measured from raw bytes only.

(a) structure intact, (b) the intended value changed in all 63 copies,
(c) nothing within +/-200 bytes of each edit changed except the intended bytes.
"""
import struct
import zlib

BASE = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
        r"\empires2_x2_p1.dat")
MOD = (r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch"
       r"\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat")
MARK = b"\x60\x0a"


def inflate(p, tag):
    blob = open(p, "rb").read()
    d = zlib.decompressobj(-15)
    out = d.decompress(blob) + d.flush()
    print("%-4s compressed=%-9d raw=%-9d eof=%s unused=%d"
          % (tag, len(blob), len(out), d.eof, len(d.unused_data)))
    return out


def main():
    b = inflate(BASE, "base")
    n = inflate(MOD, "mod")
    print("raw length delta           :", len(n) - len(b))
    print("file_version both sides    :", b[:8], n[:8])
    print("debug_string marker count  : base=%d mod=%d"
          % (b.count(MARK), n.count(MARK)))
    print("byte-identical             :", b == n)

    diffs = [i for i in range(len(b)) if b[i] != n[i]]
    print("changed bytes              :", len(diffs))

    # ---- pair up and classify -------------------------------------------
    prim = diffs[0::2]
    mirr = diffs[1::2]
    print("gaps (all)                 :", sorted(set(m - a for a, m in zip(prim, mirr))))
    cls = {}
    for a, m in zip(prim, mirr):
        ab, an = struct.unpack_from("<H", b, a)[0], struct.unpack_from("<H", n, a)[0]
        mb, mn = struct.unpack_from("<H", b, m)[0], struct.unpack_from("<H", n, m)[0]
        k = (ab, an, mb, mn)
        cls[k] = cls.get(k, 0) + 1
    print("(primary_before,primary_after,mirror_before,mirror_after) ->", cls)
    print("every edit is u16 +2       :",
          all(an - ab == 2 and mn - mb == 2 for ab, an, mb, mn in cls))
    print("all pairs share one value  :", len(cls) == 1)

    # ---- (b) 63 distinct civ slots --------------------------------------
    a0 = prim[0]
    span = (prim[-1] - prim[0]) / 62.0
    print("first/last primary         : %d .. %d" % (prim[0], prim[-1]))
    print("mean spacing               : %.1f" % span)
    slots = [round((p - a0) / span) for p in prim]
    print("slot indices 0..62 unique  :", slots == list(range(63)))
    if slots != list(range(63)):
        print("  slot indices:", slots)
    dev = max(abs((p - a0) - round((p - a0) / span) * span) for p in prim)
    print("max deviation from lattice : %.1f bytes" % dev)

    # ---- same unit record? constant distance to its 'ARCHR' id string ----
    dist = []
    for p in prim:
        i = b.rfind(MARK, 0, p)
        tag = None
        while i != -1:
            ln = struct.unpack_from("<H", b, i + 2)[0]
            pay = b[i + 4:i + 4 + ln]
            if 0 < ln <= 40 and pay == b"ARCHR":
                tag = p - (i + 4)
                break
            i = b.rfind(MARK, 0, i)
        dist.append(tag)
    print("distance to 'ARCHR' string :", sorted(set(d for d in dist if d)),
          "misses:", sum(1 for d in dist if d is None))

    # ---- (c) +/-200 neighbourhood audit ----------------------------------
    changed = set(diffs)
    viol = 0
    for a, m in zip(prim, mirr):
        for lo, hi in ((a - 200, a + 200), (m - 200, m + 200)):
            inside = [o for o in changed if lo <= o < hi]
            allowed = {a, m}
            if set(inside) - allowed:
                viol += 1
                print("  violation around %d: %s" % (a, sorted(set(inside) - allowed)))
    print("neighbourhood violations   :", viol)

    # ---- (a) structure: every marker-payload still decodes, same count ---
    def payloads(blob):
        out = []
        i = blob.find(MARK)
        while i != -1:
            if i + 4 <= len(blob):
                ln = struct.unpack_from("<H", blob, i + 2)[0]
                if 0 < ln <= 65535 and i + 4 + ln <= len(blob):
                    out.append((i, ln, blob[i + 4:i + 4 + ln]))
            i = blob.find(MARK, i + 1)
        return out
    pb, pn = payloads(b), payloads(n)
    print("marker-shaped strings      : base=%d mod=%d" % (len(pb), len(pn)))
    same_offsets = [x[0] for x in pb] == [x[0] for x in pn]
    print("all marker offsets stable  :", same_offsets)
    diffpays = [(x[0], x[2], y[2]) for x, y in zip(pb, pn) if x[2] != y[2]]
    print("marker payloads differing  :", len(diffpays), diffpays[:3])
    print("total structure byte span  :", len(b))


if __name__ == "__main__":
    main()
