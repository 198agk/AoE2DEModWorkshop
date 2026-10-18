# -*- coding: utf-8 -*-
"""Is the .dat shipped by an availability mod the SAME DATA, just recompressed?"""
import hashlib
import os
import zlib

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(ROOT, r"resources\_common\dat\empires2_x2_p1.dat")
MODS = {
    "avail_revoke": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "scratch", "s4b", "revoke",
                                 r"resources\_common\dat\empires2_x2_p1.dat"),
    "delta_zero": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "scratch", "s4b", "delta0",
                               r"resources\_common\dat\empires2_x2_p1.dat"),
}


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


def h(b):
    return hashlib.sha256(b).hexdigest()


base_raw = inflate(BASE)
print("base: file=%d raw=%d raw_sha=%s" % (os.path.getsize(BASE), len(base_raw), h(base_raw)))
for tag, p in MODS.items():
    if not os.path.isfile(p):
        print(tag, "MISSING")
        continue
    r = inflate(p)
    diffs = sum(1 for i in range(min(len(r), len(base_raw))) if r[i] != base_raw[i])
    print("%-14s file=%d raw=%d  same_data=%s  differing_bytes=%d  length_delta=%d"
          % (tag, os.path.getsize(p), len(r), r == base_raw, diffs,
             len(r) - len(base_raw)))
