# -*- coding: utf-8 -*-
"""CLAIM 2(b) -- prove the 63 edited primaries are one per civilization,
using ONLY bytes from the .dat plus the game's own civilizations.json.

Method: enumerate every debug_string payload (u16 marker 0x0A60, u16 len,
bytes) in the decompressed stream, keep those that equal a civilization name
from civilizations.json, then for each edited primary take the nearest
preceding civ-name marker and check that the 63 primaries map 1:1 onto 63
distinct civilizations.
"""
import io
import json
import struct
import zlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = GAME + r"\resources\_common\dat\empires2_x2_p1.dat"
MOD = (r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch"
       r"\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat")
CIVJSON = GAME + r"\resources\_common\dat\civilizations.json"
MARKER = b"\x60\x0a"


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


def debug_strings(blob):
    """Yield (payload_offset, payload_bytes) for every marker-shaped string."""
    out = []
    i = blob.find(MARKER)
    n = len(blob)
    while i != -1:
        if i + 4 <= n:
            ln = struct.unpack_from("<H", blob, i + 2)[0]
            if 0 < ln <= 64 and i + 4 + ln <= n:
                payload = blob[i + 4:i + 4 + ln]
                if all(32 <= c < 127 for c in payload):
                    out.append((i + 4, payload))
                    i = blob.find(MARKER, i + 4 + ln)
                    continue
        i = blob.find(MARKER, i + 1)
    return out


def main():
    base = inflate(BASE)
    new = inflate(MOD)
    diffs = [i for i in range(len(base)) if base[i] != new[i]]
    primaries = diffs[0::2]
    print("primaries:", len(primaries), "first:", primaries[0])

    civ = json.load(io.open(CIVJSON, encoding="utf-8-sig"))["civilization_list"]
    names = {}
    for i, c in enumerate(civ):
        for key in ("internal_name", "data_name", "tech_tree_name"):
            v = c.get(key)
            if v:
                names.setdefault(v.encode("ascii", "ignore"), i)
    print("civ entries:", len(civ), " distinct name tokens:", len(names))

    ds = debug_strings(base)
    print("total debug_strings parsed:", len(ds))
    hits = [(off, names[p]) for off, p in ds if p in names]
    print("civ-name debug_strings found:", len(hits))

    # nearest preceding civ-name marker per primary
    assign = []
    for a in primaries:
        prev = [h for h in hits if h[0] < a]
        assign.append(prev[-1] if prev else None)
    idxs = [x[1] for x in assign if x]
    print("primary -> distinct civ index count:", len(set(idxs)), "/", len(primaries))
    print("mapping:", idxs)
    print("all 63 civs covered:", sorted(idxs) == list(range(63)))

    # spacing between primitive civ-name markers tells us record boundaries
    starts = [h[0] for h in hits]
    print("civ marker offsets (first 8):", starts[:8])
    if len(starts) > 1:
        gaps = [b - a for a, b in zip(starts, starts[1:])]
        print("civ marker gaps (min/median/max):", min(gaps),
              sorted(gaps)[len(gaps) // 2], max(gaps))
    # distance from each primary back to its civ marker
    d = [a - prev[0] for a, prev in zip(primaries, assign) if prev]
    print("primary - civ marker distance (min/max):", min(d), max(d))

    # every primary must sit inside a distinct civ record: verify strictly
    # increasing civ index sequence
    print("civ indices strictly increasing:",
          all(x < y for x, y in zip(idxs, idxs[1:])))
    print("sha256 raw base:", __import__("hashlib").sha256(base).hexdigest())


if __name__ == "__main__":
    main()
