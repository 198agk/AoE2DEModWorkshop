# -*- coding: utf-8 -*-
"""CLAIM 1 -- byte-exact round trip of the real game .dat.

Loads empires2_x2_p1.dat (raw deflate, wbits=-15), fully parses it with the
product's parser, re-serializes with no edits, and compares byte-for-byte.
Also does the second-pass idempotency check (serialize the re-parsed model of
the emitted stream) and reports the first differing offset if any.
"""
import hashlib
import struct
import sys
import time
import zlib

sys.path.insert(0, r"D:\Software\AI\帝国项目")

from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import writer as W          # noqa: E402

DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def firstdiff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    if len(a) != len(b):
        return n
    return -1


def main():
    t0 = time.time()
    blob = open(DAT, "rb").read()
    print("input file bytes          :", len(blob))
    print("input sha256              :", sha(blob))
    print("input magic (4)           :", blob[:4])

    d = zlib.decompressobj(-15)
    raw = d.decompress(blob) + d.flush()
    print("decompressed bytes        :", len(raw))
    print("stream eof / unused_data  :", d.eof, len(d.unused_data))
    print("decompressed sha256       :", sha(raw))
    print("file_version (first 8)    :", raw[:8])

    t1 = time.time()
    st = P.Parser(raw).parse()
    print("parse seconds             : %.2f" % (time.time() - t1))
    print("game_version              :", st.get("game_version"))
    print("counts: units=%d civs=%d techs=%d graphics=%d effects=%d"
          % (st["unit_header_count"], len(st["civs"]), len(st["techs"]),
             st["graphic_count"], len(st["effects"])))

    t2 = time.time()
    out, rep = W.serialize_dat(st, raw=raw, strict=True)
    print("serialize seconds         : %.2f" % (time.time() - t2))
    print("writer report keys        :", sorted(rep.keys()))
    for k in ("mismatches", "first_mismatch", "model_bytes", "opaque_bytes",
              "opaque_sites", "final_offset"):
        if k in rep:
            print("  report[%-16s] = %r" % (k, rep[k]))

    print()
    print("output bytes              :", len(out))
    print("output sha256             :", sha(out))
    print("sha256 match              :", sha(out) == sha(raw))
    print("byte-exact                :", out == raw)
    fd = firstdiff(out, raw)
    if fd == -1:
        print("first differing offset    : (none)")
    else:
        print("FIRST DIFFERING OFFSET    :", fd)
        lo = max(0, fd - 16)
        print("  base:", " ".join("%02x" % c for c in raw[lo:fd + 16]))
        print("  out :", " ".join("%02x" % c for c in out[lo:fd + 16]))

    # idempotency: re-parse the emitted stream, serialize again
    t3 = time.time()
    st2 = P.Parser(out).parse()
    out2, rep2 = W.serialize_dat(st2, raw=out, strict=True)
    print()
    print("reparse leftover bytes    :", len(out) - rep2.get("final_offset", 0))
    print("second-pass identical     :", out2 == out)
    print("second-pass seconds       : %.2f" % (time.time() - t3))
    print("TOTAL seconds             : %.2f" % (time.time() - t0))


if __name__ == "__main__":
    main()
