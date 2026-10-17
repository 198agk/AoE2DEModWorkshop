# -*- coding: utf-8 -*-
"""Grammar-aware decode of the post-instructions header region for EVERY scenario
on this machine, all versions.

Key realisation this script tests:
  * `scenario_instructions` is a str32 whose LENGTH IS OFTEN ODD (e.g. 1), so a
    naive '+4 at a time' walk falls out of alignment immediately.
  * `savable` (s32 at offset 8) takes only the small values 2..6 and appears to
    select the post-instructions field grammar.  This is what we test here.

No offset scanning: the deflate offset used is the ground truth obtained once,
purely as a reference to measure the region against.
"""
import os
import struct
import sys
import zlib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenario_header import locate_deflate  # noqa: E402

ROOTS = [
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario",
]
EXTS = (".aoe2scenario", ".scx")
SENTINEL = 1000


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def gt_off(b, limit=4096):
    """Reference deflate offset (largest-eof stream) -- measurement only."""
    best = (None, 0)
    for off in range(4, min(len(b), limit)):
        d = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            out = d.decompress(b[off:])
        except zlib.error:
            continue
        if d.eof and len(out) > best[1]:
            best = (off, len(out))
    return best


files = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dp, _d, names in os.walk(root):
        for n in names:
            if n.lower().endswith(EXTS):
                files.append(os.path.join(dp, n))

rows = []
for p in sorted(files):
    b = open(p, "rb").read()
    goff, gout = gt_off(b)
    if goff is None:
        continue
    ver = b[:4].decode("ascii", "replace")
    hl = u32(b, 4)
    sv = u32(b, 8)
    ts = u32(b, 12)
    ilen = u32(b, 16)
    ins_end = 20 + ilen
    rows.append(dict(path=p, name=os.path.basename(p), ver=ver, hl=hl, sv=sv, ts=ts,
                     ilen=ilen, ins_end=ins_end, gt=goff, gout=gout, size=len(b), b=b))

print(f"scenarios with a located deflate stream: {len(rows)}")
print()

# ---- savable histogram per version ----
by_ver = defaultdict(Counter)
for r in rows:
    by_ver[r["ver"]][r["sv"]] += 1
print("version -> {savable: count}")
for ver in sorted(by_ver, key=lambda v: tuple(map(int, v.split(".")))):
    print(f"  {ver:6s} {dict(sorted(by_ver[ver].items()))}")

print()
print("=" * 118)
print("post-instructions region decode, grouped by savable")
print("=" * 118)
by_sv = defaultdict(list)
for r in rows:
    by_sv[r["sv"]].append(r)

for sv in sorted(by_sv):
    items = by_sv[sv]
    lens = Counter(r["gt"] - r["ins_end"] for r in items)
    print(f"\n### savable={sv}   n={len(items)}   (gt - ins_end) lengths={dict(sorted(lens.items()))}")
    for r in items[:4]:
        b, o, gt = r["b"], r["ins_end"], r["gt"]
        print(f"  {r['ver']} {r['name'][:44]:44s} size={r['size']:<8} inslen={r['ilen']:<5} "
              f"ins_end={o:<5} gt={gt:<6} region={gt - o} B")
        # scan for the 1000 sentinel aligned to o
        pos = []
        q = o
        while q + 4 <= gt:
            if u32(b, q) == SENTINEL:
                pos.append(q)
            q += 4
        print(f"      1000 sentinel at u32 steps from ins_end: {[x - o for x in pos]}")
        seq = []
        q = o
        while q + 4 <= gt:
            seq.append(u32(b, q))
            q += 4
        print(f"      u32s: {seq}")
        if q != gt:
            print(f"      trailing {gt - q} byte(s): {b[q:gt].hex(' ')}")
