# -*- coding: utf-8 -*-
"""campaign_measure2.py -- corrected measurements.

Fixes two bugs in campaign_measure.py:
  * A) used os.listdir (non-recursive) so the 1.21/1.33 .scx files under
    resources\\_common\\drs\\** were never enumerated -> use os.walk.
  * C) compared the magic scan's DEFLATE offsets against the member table's member
    START offsets -> must compare member starts (the regex hit position).

Also: characterize the fixed 256-byte campaign prologue region (32 .. 288).
"""
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign import parse_campaign  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ROOTS = [os.path.join(GAME, "resources", "_common", "drs"),
         os.path.join(GAME, "resources", "_common", "campaign"),
         os.path.join(GAME, "resources", "_common", "scenario"),
         r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"]
CAMP_DIR = os.path.join(GAME, "resources", "_common", "campaign")
VER_RE = re.compile(rb"1\.\d\d\x00\x00\x00\x00")


def inflate_eof(b, off, min_out=1000):
    d = zlib.decompressobj(-zlib.MAX_WBITS)
    try:
        out = d.decompress(b[off:])
    except zlib.error:
        return None
    if d.eof and len(out) >= min_out:
        return out
    return None


def old_magic_scan_starts(b):
    """Returns the set of member-START positions (regex hits) for which some
    header_len in 24..400 yields a valid raw-deflate stream."""
    starts = set()
    for m in VER_RE.finditer(b):
        base = m.start()
        for h in range(24, 401):
            off = base + h
            if off + 8 > len(b):
                break
            if inflate_eof(b, off) is not None:
                starts.add(base)
                break
    return starts


# ---------------------------------------------------------------------------
print("=" * 78)
print("A) version x savable cross-tab, recursive enumeration")
print("=" * 78)
standalone = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.lower().endswith((".aoe2scenario", ".scx")):
                standalone.append(os.path.join(dp, f))
standalone.sort()
print(f"standalone scenario-like files found recursively: {len(standalone)}")

instances = []
instances += [("standalone", os.path.basename(p), open(p, "rb").read(), p)
              for p in standalone]

camp_rows = []
for cf in sorted(os.listdir(CAMP_DIR)):
    if not cf.lower().endswith(".aoe2campaign"):
        continue
    cb = open(os.path.join(CAMP_DIR, cf), "rb").read()
    c = parse_campaign(cb)
    camp_rows.append((cf, cb, c))
    for m in c["members"]:
        instances.append(("member", f"{cf}::{m['name']}", m["data"], None))

xt = {}
for origin, name, b, p in instances:
    if len(b) < 12:
        continue
    ver = b[0:4].decode("ascii", "replace")
    sav = int.from_bytes(b[8:12], "little", signed=True)
    xt[(ver, sav, origin)] = xt.get((ver, sav, origin), 0) + 1

print(f"total scenario instances: {sum(xt.values())}")
print(f"{'version':10s} {'savable':>8s}  {'standalone':>10s} {'member':>7s}")
for v, s in sorted({(v, s) for (v, s, o) in xt}, key=lambda k: (k[0], k[1])):
    a = xt.get((v, s, "standalone"), 0)
    c_ = xt.get((v, s, "member"), 0)
    print(f"{v!r:10s} {s:>8d}  {a:>10d} {c_:>7d}")

per_ver = {}
for (v, s, o) in xt:
    per_ver.setdefault(v, set()).add(s)
multi = {v: sorted(ss) for v, ss in per_ver.items() if len(ss) > 1}
print()
print(f"version tags mapping to >1 savable value: {multi if multi else 'NONE'}")
print(f"distinct (version,savable) pairs: {len(per_ver and xt)} -> "
      f"{sorted({(v, s) for (v, s, o) in xt})}")

print()
print("=" * 78)
print("B) campaign prologue: bytes 32..288")
print("=" * 78)
print(f"header_end (= 8 + 4*amount) values: "
      f"{sorted({8 + 4 * c['amount_of_unknown_numbers'] for _, _, c in camp_rows})}")
print(f"count_field_offset values        : "
      f"{sorted({c['count_field_offset'] for _, _, c in camp_rows})}")
print()
for cf, cb, c in camp_rows[:4]:
    amt = c["amount_of_unknown_numbers"]
    he = 8 + 4 * amt
    reg = cb[he:c["count_field_offset"]]
    print(f"{cf}: amount={amt} header_end={he} region_len={len(reg)}")
    print(f"   u32 list (first 12): "
          f"{[struct.unpack_from('<I', reg, i)[0] for i in range(0, 48, 4)]}")
    print(f"   ascii  : {reg[:96]!r}")
    print(f"   nonzero u32 count: {sum(1 for i in range(0, len(reg)-3, 4) if struct.unpack_from('<I', reg, i)[0])} / {len(reg)//4}")
    print()
# is the region always exactly 256 and mostly zero?
allz = []
for cf, cb, c in camp_rows:
    he = 8 + 4 * c["amount_of_unknown_numbers"]
    reg = cb[he:c["count_field_offset"]]
    nz = sum(1 for x in reg if x)
    allz.append((cf, len(reg), nz, reg[:64]))
print(f"region length set: {sorted({l for _, l, _, _ in allz})}")
print(f"nonzero byte counts: min={min(n for _,_,n,_ in allz)} max={max(n for _,_,n,_ in allz)}")
print(f"u32 words at region[0:4] (first word of region) set: "
      f"{sorted({struct.unpack_from('<I', cb, 8+4*c['amount_of_unknown_numbers'])[0] for _, cb, c in camp_rows})}")
print()
print("first 64 bytes of the prologue region for 5 campaigns:")
for cf, l, nz, head in allz[:5]:
    print(f"  {cf:26s} nonzero={nz:3d} {head!r}")

print()
print("=" * 78)
print("C) magic-scan coverage vs member table (corrected comparison)")
print("=" * 78)
tot_table = sum(c["member_count"] for _, _, c in camp_rows)
tot_old = 0
missed = []
for cf, cb, c in camp_rows:
    starts = old_magic_scan_starts(cb)
    tot_old += len(starts)
    table_starts = {m["offset"] for m in c["members"]}
    for m in c["members"]:
        if m["offset"] not in starts:
            mb = m["data"]
            missed.append((cf, m["name"], mb[0:4].decode("ascii", "replace"),
                           m["offset"], int.from_bytes(mb[16:20], "little")))
    extra = starts - table_starts
    if extra:
        print(f"  NOTE {cf}: magic scan reported {len(extra)} starts NOT in the table")
print(f"member table total          : {tot_table}")
print(f"magic-scan recipe total     : {tot_old}")
print(f"members the scan MISSED     : {len(missed)}")
print(f"campaigns with any miss     : {len({m[0] for m in missed})} / {len(camp_rows)}")
for r in missed:
    print(f"   {r[0]:22s} {r[1][:34]:34s} ver={r[2]!r:8s} off={r[3]:<8d} instr_len={r[4]}")
if missed:
    print(f"max instructions_len among missed: {max(r[4] for r in missed)}")
    print("=> reason: instructions bytes push the header past the 24..400 window the "
          "old recipe scanned (the window's UPPER bound is the binding constraint).")

json.dump({"standalone": len(standalone),
           "instances": sum(xt.values()),
           "pairs": [list(k) for k in sorted({(v, s) for (v, s, o) in xt})],
           "table_total": tot_table, "scan_total": tot_old,
           "missed": missed},
          open(os.path.join(HERE, "campaign_measure2.json"), "w", encoding="utf-8"), indent=2)
print()
print("wrote campaign_measure2.json")
