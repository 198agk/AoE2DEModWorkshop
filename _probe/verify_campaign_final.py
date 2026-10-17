# -*- coding: utf-8 -*-
"""FINAL independent campaign verification.

Model derived from raw bytes (my own derivation, not from any report):

    @0                c4  version          ("2.00")
    @4                u32 amount           (constant 6 across all 42)
    @8                u32[amount]          (2,3,4,5,6,7 for dcam0)
    @8+4*amount       u8[256]              prologue (campaign name + heap junk)
    +256              u32 member_count
                      then member_count records:
                          u32 length    (byte length of the member body)
                          u32 offset    (ABSOLUTE offset of the body in file)
                          (u16 0x0A60 | u16 namelen | name) x2
                      then the bodies, back-to-back, starting at table end

Reproduced consequences I test here:
  T1 all 42 parse; offsets chain contiguously from table_end; end == file size
  T2 first body offset == table end (i.e. bodies follow the table directly)
  T3 each body's first 4 bytes are a version string
  T4 each body contains an exactly-consuming raw-deflate stream
  T5 dcam0 member "The Siege" is byte-identical to the standalone user file
  T6 the u32 "amount" field is NOT the member count (they differ) -- so no
     parser may use it as such
Read-only.
"""
import hashlib
import os
import struct
import zlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
C16 = 0x0A60


def campaigns():
    out = []
    for root in (GAME, USER):
        for b, s, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(".aoe2campaign"):
                    out.append(os.path.join(b, f))
    return sorted(set(out))


def parse(blob):
    amount = struct.unpack_from("<I", blob, 4)[0]
    pro = 8 + 4 * amount
    o = pro + 256
    cnt = struct.unpack_from("<I", blob, o)[0]
    o += 4
    recs = []
    for i in range(cnt):
        ln, off = struct.unpack_from("<II", blob, o)
        o += 8
        c1, n1 = struct.unpack_from("<HH", blob, o)
        nm1 = blob[o + 4:o + 4 + n1]
        o += 4 + n1
        c2, n2 = struct.unpack_from("<HH", blob, o)
        nm2 = blob[o + 4:o + 4 + n2]
        o += 4 + n2
        recs.append(dict(i=i, length=ln, offset=off, c1=c1, c2=c2, n1=n1,
                         n2=n2, name=nm1, name2=nm2))
    return dict(version=blob[0:4], amount=amount, count=cnt, table_end=o,
                recs=recs)


def inflate_exact(b, lo=16, hi=1500):
    for off in range(lo, min(hi, len(b))):
        if ((b[off] >> 1) & 3) not in (1, 2):
            continue
        d = zlib.decompressobj(-15)
        try:
            raw = d.decompress(b[off:])
            raw += d.flush()
        except zlib.error:
            continue
        if d.eof and not d.unused_data and len(raw) > 1000:
            return off, len(raw)
    return None


files = campaigns()
print("campaigns:", len(files))
tot = 0
t1_bad = t2_bad = t3_bad = t4_bad = 0
amount_vs_count = []
ver_dist = {}
detail = []
for p in files:
    b = open(p, "rb").read()
    r = parse(b)
    tot += r["count"]
    amount_vs_count.append((r["amount"], r["count"]))
    # T1 contiguous chain
    cur = r["table_end"]
    good = True
    for m in r["recs"]:
        if m["offset"] != cur:
            good = False
        cur = m["offset"] + m["length"]
    if not good or cur != len(b):
        t1_bad += 1
    # T2
    if r["recs"] and r["recs"][0]["offset"] != r["table_end"]:
        t2_bad += 1
    for m in r["recs"]:
        body = b[m["offset"]:m["offset"] + m["length"]]
        if len(body) != m["length"]:
            t3_bad += 1
            continue
        ver_dist[body[0:4]] = ver_dist.get(body[0:4], 0) + 1
        if inflate_exact(body) is None:
            t4_bad += 1
            detail.append((os.path.basename(p), m["name"], m["length"]))

print("total members:", tot)
print("T1 offset-chain / exact-EOF failures:", t1_bad, "/", len(files))
print("T2 first-body-offset != table_end:", t2_bad)
print("T3 body truncations:", t3_bad)
print("T4 bodies with no exactly-consuming deflate stream:", t4_bad)
for d in detail[:8]:
    print("    ", d)
print()
print("T6 is u32@4 the member count?  (amount, count) pairs:",
      sorted(set(amount_vs_count)))
print("   -> distinct counts:", sorted(set(c for a, c in amount_vs_count)))
print()
print("member body version tags:")
for k, v in sorted(ver_dist.items(), key=lambda t: -t[1]):
    print("   %-8r %d" % (k.decode("latin1", "replace"), v))

# T5
ub = open(os.path.join(USER, "76561198406248391", "resources", "_common",
                       "scenario", "The Siege.aoe2scenario"), "rb").read()
print()
print("T5 standalone The Siege: size=%d sha1=%s"
      % (len(ub), hashlib.sha1(ub).hexdigest()))
b = open(os.path.join(GAME, "resources", "_common", "campaign",
                      "dcam0.aoe2campaign"), "rb").read()
r = parse(b)
for m in r["recs"]:
    body = b[m["offset"]:m["offset"] + m["length"]]
    same = hashlib.sha1(body).hexdigest() == hashlib.sha1(ub).hexdigest()
    print("   %-40s len=%-8d off=%-8d ver=%r %s"
          % (m["name"].decode("latin1"), m["length"], m["offset"], body[0:4],
             "<== IDENTICAL" if same else ""))
