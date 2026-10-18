# -*- coding: utf-8 -*-
import sys, os, io, json, zlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
p = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
raw = open(p,'rb').read()
print("file bytes:", len(raw))
# AoE2 DE .dat: version header then raw deflate
import struct
ver = raw[:4]
print("first 8 bytes:", raw[:8].hex())
try:
    d = zlib.decompressobj(-15)
    out = d.decompress(raw[8:])
    print("inflated (raw deflate @8):", len(out), "unused:", len(d.unused_data))
except Exception as e:
    print("inflate fail:", e)
