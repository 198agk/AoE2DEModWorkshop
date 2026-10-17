# -*- coding: utf-8 -*-
"""DECISIVE rule for SLD layer records:

    record length = ceil4(size)      # size is the u32 at the record start
    next record   = q + ceil4(size)

The old rule was  next = ceil4(q + size)  (absolute 4-alignment).  The two
agree whenever q % 4 == 0, which is why the old rule already walked 15,053 of
15,486 files.  In the 431 files with frame_offset = 14 every q is ≡ 2 (mod 4),
so the old rule lands 2 bytes early and desynchronises on frame 0/1.

Validate both rules over the whole tree.  Read-only.
"""
import os
import struct
import collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
BITNAMES = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
ceil4 = lambda x: x + ((4 - x % 4) % 4)

files = sorted(f for f in os.listdir(GP) if f.lower().endswith(".sld"))
print("files in dir:", len(files))

zero = 0
fo_hist = collections.Counter()
res = {}

for fn in files:
    b = open(os.path.join(GP, fn), "rb").read()
    if len(b) == 0:
        zero += 1
        continue
    sig, ver, n, u1, fo, magic = struct.unpack_from("<4s 2H 2H H", b, 0)
    fo_hist[fo] += 1

    def walk(rule):
        p = fo
        prev = None
        it = 0
        lay = collections.Counter()
        while p < len(b):
            if p + 12 > len(b):
                return ("frame hdr past EOF f%d" % it, it, lay)
            cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, p)
            if prev is not None and idx != prev + 1:
                return ("frame_index break f%d %d->%d" % (it, prev, idx), it, lay)
            prev = idx
            q = p + 12
            for bit, nm in BITNAMES:
                if not (ft & (1 << bit)):
                    continue
                if q + 4 > len(b):
                    return ("size past EOF f%d %s" % (it, nm), it, lay)
                size = struct.unpack_from("<I", b, q)[0]
                if size < 4 or q + size > len(b):
                    return ("size=%d bad f%d %s" % (size, it, nm), it, lay)
                lay[nm] += 1
                q = q + ceil4(size) if rule == "E" else ceil4(q + size)
            p = q
            it += 1
        return ("ok" if p == len(b) else "overrun %d" % p, it, lay)

    e = walk("E")
    o = walk("O")
    res[fn] = (e, o, fo, n)

ok_e = [f for f, v in res.items() if v[0][0] == "ok"]
ok_o = [f for f, v in res.items() if v[1][0] == "ok"]
print("zero-byte files    :", zero)
print("frame_offset hist  :", dict(fo_hist))
print()
print("RULE E  (next = q + ceil4(size))    reaching EXACT EOF: %d / %d" % (len(ok_e), len(res)))
print("OLD     (next = ceil4(q + size))     reaching EXACT EOF: %d / %d" % (len(ok_o), len(res)))
print()
fe = [(f, v[0][1], v[2], v[3]) for f, v in res.items() if v[0][0] != "ok"]
fo_ = [(f, v[1][1], v[2], v[3]) for f, v in res.items() if v[1][0] != "ok"]
print("FAILURES rule E :", len(fe))
for f in fe[:30]:
    print("   ", f)
print()
print("FAILURES old    :", len(fo_))
for f in fo_[:8]:
    print("   ", f)
print()

# --- invariants under rule E ---
frames = sum(res[f][0][1] for f in ok_e)
lay = collections.Counter()
for f in ok_e:
    lay.update(res[f][0][2])
print("total frames (rule E):", frames)
print("layers per file (rule E) :", dict(lay))
