# -*- coding: utf-8 -*-
"""Campaign member record + body layout, derived from bytes.

Record (derived):  u32 A | u32 B | [u16 const | u16 namelen | name] x2
                   => record_size = 8 + 2*(4+namelen) = 16 + 2*namelen

Open question this answers: WHERE do member bodies live, and what are A/B?
Candidates: bodies concatenated after the record table, length A or B.
Read-only.
"""
import hashlib
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
C16 = 0x0A60


def load(name):
    for root in (GAME, USER):
        for b, s, fs in os.walk(root):
            if name in fs:
                return open(os.path.join(b, name), "rb").read()
    return None


def table(blob, verbose=True):
    amount = struct.unpack_from("<I", blob, 4)[0]
    o = 8 + 4 * amount + 256
    cnt = struct.unpack_from("<I", blob, o)[0]
    o += 4
    recs = []
    for i in range(cnt):
        A, B = struct.unpack_from("<II", blob, o)
        o += 8
        c1, n1 = struct.unpack_from("<HH", blob, o)
        nm1 = blob[o + 4:o + 4 + n1]
        o += 4 + n1
        c2, n2 = struct.unpack_from("<HH", blob, o)
        nm2 = blob[o + 4:o + 4 + n2]
        o += 4 + n2
        recs.append(dict(i=i, A=A, B=B, c1=c1, c2=c2, n1=n1, n2=n2,
                         name=nm1, name2=nm2))
    if verbose:
        print("   amount=%d count=%d table_end=%d size=%d"
              % (amount, cnt, o, len(blob)))
        for r in recs:
            print("     rec%d A=%-9d B=%-9d n=%-4d const=%s name=%s"
                  % (r["i"], r["A"], r["B"], r["n1"], hex(r["c1"]),
                     r["name"].decode("latin1")))
        print("   bytes right after table:", blob[o:o + 40])
    return recs, o, bl


for name in ("dcam0.aoe2campaign", "acam1.aoe2campaign"):
    blob = load(name)
    print("===", name, "size", len(blob))
    recs, table_end, _ = table(blob)
    print("   sum(B) =", sum(r["B"] for r in recs),
          " sum(A) =", sum(r["A"] for r in recs),
          " after_table_bytes =", len(blob) - table_end)
    print()
