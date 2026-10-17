# -*- coding: utf-8 -*-
"""unknown2 -- systematic structural analysis.

Established facts (this run, verified over the whole tree):
  * 4,737,215 unknown2 layers, EVERY one starts with u16 5 then u16 0.
  * payload parity is ~50/50 -> NOT an 8-byte block layer.
  * from offset 4 there is a strictly-increasing u16 run of variable length K.

Hypotheses tested here:
  H1  unknown2 is identical across all frames of one file (file-level datum)
  H2  unknown2 payloads are shared across many files (a lookup table)
  H3  the u16 run is a table of cumulative end-offsets of sub-records
  H4  the tail is a list of self-delimiting chunks (u8 tag + data + u16 0)
  H5  the tail is zlib/deflate compressed
  H6  K correlates with grid dims / span / block count
"""
import hashlib
import os
import struct
import sys
import zlib
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, parse_rect_layer, grid_of

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")


def run_len(d, base=4):
    """strictly-increasing u16 run starting at `base`; returns (k, vals)."""
    vals = []
    prev = -1
    k = 0
    while base + 2 * (k + 1) <= len(d):
        v = struct.unpack_from("<H", d, base + 2 * k)[0]
        if v > prev:
            vals.append(v)
            prev = v
            k += 1
        else:
            break
    return k, vals


def main():
    files = sorted(f for f in os.listdir(GP) if f.endswith(".sld"))

    # ---------- H1: constant within a file ----------
    h1_same = h1_diff = h1_files = 0
    # ---------- H2: cross-file sharing ----------
    digests = Counter()
    k_hist = Counter()
    # ---------- H6 correlations ----------
    corr = defaultdict(Counter)
    # ---------- H3/H4 samples ----------
    samples = []

    for f in files:
        p = os.path.join(GP, f)
        if os.path.getsize(p) == 0:
            continue
        try:
            s = read_sld(p)
        except Exception:
            continue
        per_file = []
        for fr in s.frames:
            L = fr.layers
            if not isinstance(L, dict) or "main" not in L or "unknown2" not in L:
                continue
            u = L["unknown2"]
            d = u.data
            per_file.append(d)
            digests[hashlib.sha1(d).digest()] += 1
            k, vals = run_len(d, 4)
            k_hist[k] += 1
            r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
            x1, y1, w, h, bw, bh = grid_of(r)
            g = bw * bh
            mspan = sum(b for a, b in mcmds)
            corr["K vs cells"][(k, g)] += 1
            corr["K vs ncmd"][(k, mn)] += 1
            corr["K vs span"][(k, mspan)] += 1
            if len(samples) < 4 and len(d) < 40:
                samples.append((f, fr.index, u.size, k, vals, g, mspan,
                                d.hex(" ")))
        if len(per_file) > 1:
            h1_files += 1
            if len(set(per_file)) == 1:
                h1_same += 1
            else:
                h1_diff += 1

    print("=== H1: is unknown2 identical across the frames of one file? ===")
    print("   files with >1 unknown2 layer : %d" % h1_files)
    print("     all identical              : %d" % h1_same)
    print("     differ                     : %d" % h1_diff)
    if h1_files:
        print("     => %s" % ("CONSTANT PER FILE" if h1_diff == 0
                              else "varies per frame"))

    print()
    print("=== H2: how many DISTINCT unknown2 payloads exist? ===")
    print("   total layers    : %d" % sum(digests.values()))
    print("   distinct payloads: %d" % len(digests))
    print("   most repeated    : %s" % digests.most_common(5))

    print()
    print("=== H6: K histogram (top 10) ===")
    for k, n in k_hist.most_common(10):
        print("   K=%-4d %9d" % (k, n))

    print()
    print("=== H6: does K equal a grid dimension? ===")
    hit = Counter()
    for k, n in corr["K vs cells"].items():
        # K vs number of grid cells / grid width / height can't be seen from
        # this bucket alone; report the raw joint histogram's most common K
        pass
    # recompute with explicit comparisons
    cmp_ct = Counter()
    for f in files[:4000]:
        p = os.path.join(GP, f)
        if os.path.getsize(p) == 0:
            continue
        try:
            s = read_sld(p)
        except Exception:
            continue
        for fr in s.frames:
            L = fr.layers
            if not isinstance(L, dict) or "main" not in L or "unknown2" not in L:
                continue
            d = L["unknown2"].data
            k, vals = run_len(d, 4)
            r, mfmt, mn, mcmds = parse_rect_layer(L["main"])
            x1, y1, w, h, bw, bh = grid_of(r)
            g = bw * bh
            mspan = sum(b for a, b in mcmds)
            cmp_ct["total"] += 1
            cmp_ct["K == bw*bh"] += 1 if k == g else 0
            cmp_ct["K == bw"] += 1 if k == bw else 0
            cmp_ct["K == bh"] += 1 if k == bh else 0
            cmp_ct["K == ncmd"] += 1 if k == mn else 0
            cmp_ct["K == span"] += 1 if k == mspan else 0
            cmp_ct["K == bw*bh - 1"] += 1 if k == g - 1 else 0
            cmp_ct["K == bw*(bh-1)"] += 1 if k == bw * (bh - 1) else 0
            # compare K against number of DISTINCT rows used
            rows = set()
            ci = 0
            for skip, draw in mcmds:
                ci += skip
                for _ in range(draw):
                    rows.add(ci // bw if bw else 0)
                    ci += 1
            cmp_ct["K == len(rows)"] += 1 if k == len(rows) else 0
            cmp_ct["K == g - len(rows)"] += 1 if k == g - len(rows) else 0
    print()
    for kk in sorted(cmp_ct):
        print("   %-24s %9d" % (kk, cmp_ct[kk]))

    print()
    print("=== H3/H4: small-layer dumps ===")
    for s in samples:
        print("   %s f%s size=%s K=%s vals=%s grid=%s span=%s"
              % (s[0], s[1], s[2], s[3], s[4][:12], s[5], s[6]))
        print("      %s" % s[7])

    print()
    print("=== H5: zlib test on unknown2 tail ===")
    z_ok = z_try = 0
    z_err = Counter()
    for f in files[:3000]:
        p = os.path.join(GP, f)
        if os.path.getsize(p) == 0:
            continue
        try:
            s = read_sld(p)
        except Exception:
            continue
        for fr in s.frames:
            L = fr.layers
            if not isinstance(L, dict) or "unknown2" not in L:
                continue
            d = L["unknown2"].data
            for off in (0, 4):
                z_try += 1
                try:
                    o = zlib.decompressobj(-15)
                    out = o.decompress(d[off:])
                    if out and o.eof:
                        z_ok += 1
                except Exception as e:
                    z_err[type(e).__name__] += 1
    print("   tried %d, decoded-with-exact-eof %d" % (z_try, z_ok))
    print("   errors: %s" % z_err.most_common(4))


if __name__ == "__main__":
    main()
