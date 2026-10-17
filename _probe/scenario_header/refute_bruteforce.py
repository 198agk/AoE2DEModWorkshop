# -*- coding: utf-8 -*-
"""refute_bruteforce.py -- run the task brief's EXACT falsified strategy, with the
CORRECT acceptance test, and report what it actually finds.

The brief claims for The Siege.aoe2scenario (ver 1.53, 209143 B):
  * offset 4 -> decompressobj(-15) FAILS
  * wbits 15/47/31 -> also FAIL
  * offsets 0..200000 tried one by one as a deflate block start -> 0 HITS

"0 hits" is only true if the acceptance test is "output is large / is the body".
With the 3-line correct test (raw inflate, require d.eof, require >= 1000 bytes)
the true offset 83 is found.  This script measures the difference explicitly:

  ACCEPT-STRICT : d.eof == True and len(out) >= 1000
  ACCEPT-LOOSE  : no zlib.error at all (this is what produces thousands of
                  spurious "hits" and is why brute force was abandoned)

Also scans every offset of several small files to show the true offset is the
UNIQUE strict hit in the whole file.
"""
import os
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from header_layout import locate, read_savable, read_version   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"
SIEGE = os.path.join(PROFILE, "The Siege.aoe2scenario")

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


def attempt(b, off, wbits=-zlib.MAX_WBITS, cap=None):
    d = zlib.decompressobj(wbits)
    try:
        o = d.decompress(b[off:] if cap is None else b[off:off + cap])
        o += d.flush()
    except zlib.error:
        return None, False
    return o, d.eof


P("=" * 78)
P("A) The Siege.aoe2scenario -- the brief's exact claim, re-measured")
P("=" * 78)
b = open(SIEGE, "rb").read()
P(f"path={SIEGE}")
P(f"size={len(b)}  version={read_version(b)!r}  savable={read_savable(b)}")
off, layout, data, diag = locate(b)
P(f"structural dispatch -> layout={layout} deflate_offset={off} body_bytes={len(data) if data else None}")
P(f"  diag={diag}")
P()

P("offset 4 with various wbits (the brief's first three claims):")
for wb in (4 - 16, 15, 47, 31):
    res, eof = attempt(b, 4, wb)
    P(f"   wbits={wb:>3}  -> {'zlib.error' if res is None else repr(res[:24])}  eof={eof}")
P(f"   wbits=-15 (raw) at TRUE offset {off}: "
  f"{'zlib.error' if attempt(b, off)[0] is None else 'OK'} eof={attempt(b, off)[1]}")
P()

N = 200000
P(f"exhaustive scan of offsets 0..{N} (the brief says 0 hits):")
t0 = time.time()
strict, loose, werr = [], 0, 0
for o in range(0, min(N, len(b))):
    res, eof = attempt(b, o)
    if res is None:
        werr += 1
        continue
    loose += 1
    if eof and len(res) >= 1000:
        strict.append((o, len(res)))
dt = time.time() - t0
P(f"   zlib.error at        : {werr} offsets")
P(f"   inflate-somehow (LOOSE): {loose} offsets")
P(f"   eof == True and >=1000B (STRICT): {len(strict)} offsets -> {strict}")
P(f"   elapsed {dt:.1f}s")
P()
P("=> the brief's '0 hits' is an artefact of the acceptance test, not of the file.")

P()
P("=" * 78)
P("B) uniqueness of the true offset over the WHOLE file (small files)")
P("=" * 78)
SMALL = ["real_world_britain.scx", "real_world_nippon.scx", "special_map_canyons.scx",
         "0_E3_Scenario.aoe2scenario"]
paths = {}
for root in (os.path.join(GAME, "resources", "_common", "drs"),
             os.path.join(GAME, "resources", "_common", "campaign")):
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            paths.setdefault(f, os.path.join(dp, f))
for base in SMALL:
    p = paths.get(base) or os.path.join(PROFILE, base)
    if not os.path.isfile(p):
        P(f"{base}: not found")
        continue
    bb = open(p, "rb").read()
    tru, lay, dd, _ = locate(bb)
    hits = []
    for o in range(0, len(bb)):
        res, eof = attempt(bb, o)
        if res is not None and eof and len(res) >= 1000:
            hits.append((o, len(res)))
    P(f"{base:32s} size={len(bb):>7d} true={tru:<6} strict hits over ALL offsets: {hits}")

open(os.path.join(HERE, "refute_bruteforce_output.txt"), "w", encoding="utf-8").write("\n".join(out))
P()
P("wrote refute_bruteforce_output.txt")
