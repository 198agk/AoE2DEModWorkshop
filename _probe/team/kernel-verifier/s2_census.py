# -*- coding: utf-8 -*-
"""Establish the 63 copies independently: long-fingerprint census + context."""
import hashlib
import struct
import zlib

BASE = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
        r"\empires2_x2_p1.dat")
MOD = (r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch"
       r"\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat")
MARKER = b"\x60\x0a"


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


def find_all(hay, needle):
    out, i = [], hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


def main():
    base = inflate(BASE)
    new = inflate(MOD)
    diffs = [i for i in range(len(base)) if base[i] != new[i]]
    prim = diffs[0::2]
    a0 = prim[0]
    print("first primary:", a0, " primaries:", len(prim))

    # long fingerprint: 400 bytes before .. 400 after the FIRST primary.
    # Because every copy differs from the base fingerprint at the same two
    # bytes, search the *new* stream for the post-edit fingerprint.
    for span in (100, 200, 400, 800):
        fp_base = base[a0 - span:a0 + span]
        fp_new = new[a0 - span:a0 + span]
        print("span=%-4d base-hits=%d new-hits=%d"
              % (span, len(find_all(base, fp_base)), len(find_all(new, fp_new))))

    span = 600
    fp_new = new[a0 - span:a0 + span]
    hits = [h + span for h in find_all(new, fp_new)]
    print("copy anchors (span %d)   :" % span, len(hits))
    print("anchor == primary offsets:", hits == prim)
    print("first 5 anchors:", hits[:5])
    print("last  anchor   :", hits[-1])

    gaps = [b - a for a, b in zip(hits, hits[1:])]
    print("min/median/max gap between copies:", min(gaps),
          sorted(gaps)[len(gaps) // 2], max(gaps))
    print("civ-stage span check: first copy %d, last copy %d, span %.2f MB"
          % (hits[0], hits[-1], (hits[-1] - hits[0]) / 1048576.0))

    # nearest preceding debug_string payload for each copy
    def prev_strings(off, k=2):
        out = []
        i = base.rfind(MARKER, 0, off)
        while i != -1 and len(out) < k:
            ln = struct.unpack_from("<H", base, i + 2)[0]
            if 0 < ln <= 40:
                pay = base[i + 4:i + 4 + ln]
                if all(32 <= c < 127 for c in pay):
                    out.append((i + 4, pay.decode("ascii", "replace")))
                    i = base.rfind(MARKER, 0, i)
                    continue
            i = base.rfind(MARKER, 0, i)
        return out

    print("preceding debug-string payloads per copy:")
    for h in hits[:8]:
        print("   @%d -> %s" % (h, prev_strings(h, 2)))

    # does each copy sit in a distinct ~1.4 MB civ slot?
    slot = (hits[-1] - hits[0]) / 62.0
    print("mean copy spacing: %.0f bytes" % slot)
    print("all gaps > 1/4 mean spacing:", all(g > slot / 4 for g in gaps))


if __name__ == "__main__":
    main()
