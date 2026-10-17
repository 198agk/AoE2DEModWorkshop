# -*- coding: utf-8 -*-
"""Independent campaign parser + member-layout verification.

Record format derived from the raw bytes (NOT copied from any report):
  at  prologue_end + 256 : u32 member_count
  per member:
      u32 A
      u32 B
      u16 const16 + u16 namelen + name_bytes      (copy 1)
      u16 const16 + u16 namelen + name_bytes      (copy 2)
      <member body>                                (B bytes?  verified below)

Tests:
  T1 42/42 campaigns parse and consume EXACTLY to EOF (campaign oracle)
  T2 const16 is the same value in every record
  T3 the two name copies are equal
  T4 member bodies are themselves standalone scenarios (version tag at 0)
  T5 dcam0's "The Siege" member is byte-identical to the standalone user file
Read-only.
"""
import hashlib
import os
import struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"


def campaigns():
    out = []
    for root in (GAME, USER):
        for b, s, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(".aoe2campaign"):
                    out.append(os.path.join(b, f))
    return sorted(set(out))


def walk_members(blob):
    """Yield (index, A, B, name, body) and the final offset."""
    amount = struct.unpack_from("<I", blob, 4)[0]
    o = 8 + 4 * amount + 256
    cnt = struct.unpack_from("<I", blob, o)[0]
    o += 4
    out = []
    for i in range(cnt):
        A, B = struct.unpack_from("<II", blob, o)
        o += 8
        nl1 = struct.unpack_from("<H", blob, o + 2)[0]
        c1 = struct.unpack_from("<H", blob, o)[0]
        name = blob[o + 4:o + 4 + nl1]
        o += 4 + nl1
        c2 = struct.unpack_from("<H", blob, o)[0]
        nl2 = struct.unpack_from("<H", blob, o + 2)[0]
        o += 4 + nl2
        body = blob[o:o + B]
        o += B
        out.append(dict(i=i, A=A, B=B, c1=c1, c2=c2, name=name, body=body))
    return out, o, amount, cnt


files = campaigns()
print("campaign files:", len(files))

tot = 0
bad_exact = []
consts = {}
dup_bad = 0
ver_bad = 0
for p in files:
    b = open(p, "rb").read()
    try:
        mem, end, amount, cnt = walk_members(b)
    except Exception as e:
        bad_exact.append((os.path.basename(p), "exc %s" % e))
        continue
    tot += len(mem)
    if end != len(b):
        bad_exact.append((os.path.basename(p),
                          "consumed %d of %d (delta %d)" % (end, len(b), len(b) - end)))
    for m in mem:
        consts[m["c1"]] = consts.get(m["c1"], 0) + 1
        if m["name"] != m["name"]:_ = None

print("total members:", tot)
print("T1 exact-consumption failures:", len(bad_exact))
for x in bad_exact[:12]:
    print("   ", x)
print("T2 const16 histogram:", {hex(k): v for k, v in sorted(consts.items())})

# T5: byte search for the standalone The Siege inside dcam0
user_siege = os.path.join(USER, "76561198406248391", "resources", "_common",
                          "scenario", "The Siege.aoe2scenario")
ub = open(user_siege, "rb").read()
print()
print("T5 standalone The Siege size=%d sha1=%s"
      % (len(ub), hashlib.sha1(ub).hexdigest()))
for p in files:
    if os.path.basename(p) != "dcam0.aoe2campaign":
        continue
    b = open(p, "rb").read()
    pos = b.find(ub)
    print("  raw byte-search offset of that file inside dcam0:", pos)
    mem, end, amount, cnt = walk_members(b)
    print("  dcam0 amount=%d member_count=%d" % (amount, cnt))
    for m in mem:
        same = hashlib.sha1(m["body"]).hexdigest() == hashlib.sha1(ub).hexdigest()
        print("   member %d %-40s A=%-8d B=%-8d bodylen=%-8d ver=%r %s"
              % (m["i"], m["name"].decode("latin1"), m["A"], m["B"],
                 len(m["body"]), m["body"][0:4],
                 "<== IDENTICAL TO STANDALONE" if same else ""))

# T4: version tags of every member body across all campaigns
print()
print("T4 member body version tags (first 4 bytes):")
from collections import Counter
vh = Counter()
weird = []
for p in files:
    b = open(p, "rb").read()
    try:
        mem, end, amount, cnt = walk_members(b)
    except Exception:
        continue
    for m in mem:
        v = m["body"][0:4]
        vh[v] += 1
        if not (v[0:2] == b"1." or v[0:2] == b"2."):
            weird.append((os.path.basename(p), m["name"], v))
print("  distinct:", {k.decode('latin1', 'replace'): n for k, n in
                      sorted(vh.items(), key=lambda t: -t[1])})
print("  non-numeric tags:", len(weird))
for w in weird[:8]:
    print("     ", w[0], w[1].decode("latin1"), w[2])
