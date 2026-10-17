# -*- coding: utf-8 -*-
"""Test explicit structural GRAMMAR candidates (no byte scanning) against the
ground-truth deflate offset for every scenario on this machine.

Candidate list (all are *structural*; the only search is over this fixed list):
  M_IVU      modern layout WITH individual_victories_used   (1.35/1.36/1.37)
  M_NOIVU    modern layout WITHOUT it                        (1.40+ observed)
  L_SHORT    legacy short  (savable 2): ...instr, X, player_count
  L_LONG_NC  legacy long   (savable>=3): ...instr, X, player_count, 1000, uv2, amount, nums
  L_LONG_C   legacy long + creator_name str32 (no trigger_count)

The winner is the candidate whose offset raw-inflates to end-of-stream.
"""
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenario_header import (  # noqa: E402
    HeaderParseError, LAYOUT_WITH_IVU, LAYOUT_WITHOUT_IVU, parse_file_header,
)

CACHE = os.path.join(HERE, "gt_cache.json")
SENTINEL = 1000


def u32(b, o):
    if o + 4 > len(b):
        raise HeaderParseError("past eof")
    return struct.unpack_from("<I", b, o)[0]


def str32(b, o, maxlen):
    n = u32(b, o)
    o += 4
    if n > maxlen or o + n > len(b):
        raise HeaderParseError(f"bad str32 len {n}")
    return b[o:o + n], o + n


def common_prefix(b):
    """version, header_length, savable, timestamp, scenario_instructions."""
    if not (b[0:1] == b"1" and b[1:2] == b"."):
        raise HeaderParseError("bad version")
    o = 4
    header_length = u32(b, o); o += 4
    savable = u32(b, o); o += 4
    timestamp = u32(b, o); o += 4
    instr, o = str32(b, o, 1 << 22)
    return o, header_length, savable, timestamp, instr


def cand_l_short(b):
    o, hl, sv, ts, ins = common_prefix(b)
    x = u32(b, o); o += 4
    pc = u32(b, o); o += 4
    return o, dict(header_length=hl, savable=sv, instructions_len=len(ins),
                   x=x, player_count=pc, trailing_creator=None, trigger_count=None)


def cand_l_long(b, creator: bool):
    o, hl, sv, ts, ins = common_prefix(b)
    x = u32(b, o); o += 4
    pc = u32(b, o); o += 4
    if not (1 <= pc <= 16):
        raise HeaderParseError(f"player_count implausible: {pc}")
    uval = u32(b, o); o += 4
    if uval != SENTINEL:
        raise HeaderParseError(f"unknown_value != 1000: {uval}")
    uv2 = u32(b, o); o += 4
    amount = u32(b, o); o += 4
    if amount > 64:
        raise HeaderParseError(f"amount implausible: {amount}")
    nums = []
    for _ in range(amount):
        nums.append(u32(b, o)); o += 4
    creator_bytes = None
    if creator:
        creator_bytes, o = str32(b, o, 256)
    return o, dict(header_length=hl, savable=sv, instructions_len=len(ins),
                   x=x, player_count=pc, unknown_value=uval, unknown_value_2=uv2,
                   amount=amount, numbers=nums, trailing_creator=creator_bytes,
                   trigger_count=None)


def cand_modern(b, layout):
    h = parse_file_header(b, layout)
    return h["deflate_offset"], dict(h)


def inflate_eof(b, off, min_out=256):
    d = zlib.decompressobj(-zlib.MAX_WBITS)
    try:
        out = d.decompress(b[off:])
    except zlib.error as e:
        return None, False, str(e)
    if not d.eof:
        return out, False, "no eof"
    if len(out) < min_out:
        return out, False, f"too short ({len(out)})"
    return out, True, None


CANDS = [
    ("M_IVU", lambda b: cand_modern(b, LAYOUT_WITH_IVU)),
    ("M_NOIVU", lambda b: cand_modern(b, LAYOUT_WITHOUT_IVU)),
    ("L_SHORT", cand_l_short),
    ("L_LONG_NC", lambda b: cand_l_long(b, creator=False)),
    ("L_LONG_C", lambda b: cand_l_long(b, creator=True)),
]


def main():
    recs = json.load(open(CACHE, encoding="utf-8"))
    print(f"{len(recs)} files in cache")
    print()
    results = []
    for r in recs:
        b = open(r["path"], "rb").read()
        gt = r["gt_offset"]
        hits = []
        for name, fn in CANDS:
            try:
                off, info = fn(b)
            except (HeaderParseError, struct.error):
                continue
            data, ok, err = inflate_eof(b, off)
            if ok:
                hits.append((name, off, len(data)))
        mark = "OK " if (gt is not None and any(h[1] == gt for h in hits)) else "MISS"
        results.append((mark, r, hits, gt))
        print(f"{mark} {r['version']:6s} savable={r['savable']:<3} gt={str(gt):<6} "
              f"{os.path.basename(r['path'])[:40]:40s} -> {[(h[0], h[1]) for h in hits]}")

    ok = sum(1 for m, *_ in results if m == "OK ")
    print()
    print(f"RESULT: structured grammar locator matched ground truth on {ok}/{len(results)} files")
    print()
    print("misses:")
    for m, r, hits, gt in results:
        if m != "OK ":
            print(f"  {r['version']} savable={r['savable']} gt={gt} {r['path']}")
            print(f"     candidates that inflated: {hits}")


if __name__ == "__main__":
    main()
