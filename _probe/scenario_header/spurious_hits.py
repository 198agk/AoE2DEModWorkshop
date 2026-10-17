# -*- coding: utf-8 -*-
"""spurious_hits.py -- measure how many offsets pass the STRICT acceptance test.

Strict test = raw-inflate b[off:] with wbits=-15, no zlib.error, d.eof == True,
and len(out) >= 1000.

The honest question this answers: is the true deflate offset the ONLY offset
that passes?  If spurious offsets also pass, then brute force is not merely
slow -- it is UNRELIABLE, which is a stronger and more useful statement than
"0 hits".

Also measures the AMBIGUITY RATIO len(out) at the true offset vs spurious ones,
which is the only reason a magnitude heuristic ever works.
"""
import os
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from header_layout import locate   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"

CANDS = [
    os.path.join(PROFILE, "default0.aoe2scenario"),
    os.path.join(PROFILE, "The Siege.aoe2scenario"),
    os.path.join(PROFILE, "7V1变态山谷-炮塔盛宴-变态难.aoe2scenario"),
    os.path.join(GAME, "resources", "_common", "campaign", "0_E3_Scenario.aoe2scenario"),
    os.path.join(GAME, "resources", "_common", "drs", "special_map_canyons.scx"),
]

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


P("=" * 78)
P("STRICT ACCEPTANCE: is the true offset the unique pass?")
P("=" * 78)
P("strict = raw inflate (wbits=-15), no error, d.eof == True, len(out) >= 1000")
P()
for p in CANDS:
    if not os.path.isfile(p):
        P(f"{os.path.basename(p)}: NOT FOUND")
        continue
    b = open(p, "rb").read()
    tru, lay, body, _ = locate(b)
    t0 = time.time()
    hits = []
    for o in range(0, len(b)):
        d = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            oo = d.decompress(b[o:])
            oo += d.flush()
        except zlib.error:
            continue
        if d.eof and len(oo) >= 1000:
            hits.append((o, len(oo)))
    dt = time.time() - t0
    real = len(body) if body else None
    P(f"{os.path.basename(p)}")
    P(f"   size={len(b)}  true_offset={tru}  true_body={real}")
    P(f"   STRICT hits over ALL {len(b)} offsets: {len(hits)}  ({dt:.1f}s)")
    for o, n in hits:
        tag = "  <-- TRUE" if o == tru else "  <-- SPURIOUS"
        P(f"      offset={o:<8d} out={n}{tag}")
    P()

open(os.path.join(HERE, "spurious_hits_output.txt"), "w", encoding="utf-8").write("\n".join(out))
P("wrote spurious_hits_output.txt")
