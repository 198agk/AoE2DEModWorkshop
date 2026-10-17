"""Diagnose the real Name offset: scan forward from a changed HitPoints for the
serializeDebugString marker (uint16 0x0A60 = 2656) and decode what follows."""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "raw", "dat_game.raw"), "rb") as f:
    g = f.read()
with open(os.path.join(HERE, "v2_dat_rawdiff.json"), encoding="utf-8") as f:
    runs = json.load(f)["runs"]

MARK = 0x0A60
for r in runs[:6]:
    hp = r["start"]
    uid = struct.unpack_from("<h", g, hp - 21)[0]
    print("=== HP offset %d  (id %d) ===" % (hp, uid))
    hits = []
    for d in range(0, 400):
        o = hp + d
        if struct.unpack_from("<H", g, o)[0] == MARK:
            ln = struct.unpack_from("<H", g, o + 2)[0]
            if 0 < ln < 64:
                raw = g[o + 4:o + 4 + ln]
                hits.append((d, ln, raw))
    for d, ln, raw in hits:
        print("   +%-4d len=%-3d raw=%r" % (d, ln, raw))
    print()
