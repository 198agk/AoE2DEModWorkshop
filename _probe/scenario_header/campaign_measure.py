# -*- coding: utf-8 -*-
"""campaign_measure.py -- measure, don't assume.

Three measured questions:
  A) savable x version cross-tab over ALL scenario instances (standalone + members),
     to test whether `savable` (s32 @8) is a genuine grammar discriminator.
  B) the campaign prologue: where does the member-count field actually live, and is
     there ever a fixed 64-byte index table?  -> report the measured distribution.
  C) the old "magic scan" recipe (regex + header_len in 24..400) re-run by me on the
     same 42 campaigns, to quantify how many members it MISSES and why.
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

CAMP_DIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"
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


def old_magic_scan(b):
    """The previously used recipe: regex version hits, header_len 24..400."""
    found = []
    for m in VER_RE.finditer(b):
        base = m.start()
        for h in range(24, 401):
            off = base + h
            if off + 8 > len(b):
                break
            if inflate_eof(b, off) is not None:
                found.append((base, off, h))
                break
    return found


print("=" * 78)
print("A) savable x version cross-tab (all scenario instances on the machine)")
print("=" * 78)
xt = {}
standalone = []
for root in (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs",
             r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign",
             r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\scenario",
             r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"):
    if not os.path.isdir(root):
        continue
    for f in sorted(os.listdir(root)):
        if f.lower().endswith((".aoe2scenario", ".scx")):
            standalone.append(os.path.join(root, f))

instances = []   # (origin, name, bytes)
for p in standalone:
    instances.append(("standalone", os.path.basename(p), open(p, "rb").read(), p))

camp_rows = []
for cf in sorted(os.listdir(CAMP_DIR)):
    if not cf.lower().endswith(".aoe2campaign"):
        continue
    cb = open(os.path.join(CAMP_DIR, cf), "rb").read()
    c = parse_campaign(cb)
    camp_rows.append((cf, cb, c))
    for m in c["members"]:
        instances.append(("member", f"{cf}::{m['name']}", m["data"], None))

mem_count_by_camp = {cf: c["member_count"] for cf, _, c in camp_rows}

tot = 0
unreadable = []
for origin, name, b, p in instances:
    if len(b) < 12:
        continue
    ver = b[0:4].decode("ascii", "replace")
    sav = int.from_bytes(b[8:12], "little", signed=True)
    tot += 1
    xt.setdefault((ver, sav, origin), 0)
    xt[(ver, sav, origin)] += 1

print(f"{tot} scenario instances")
print(f"{'version':8s} {'savable':>8s}  {'standalone':>10s} {'member':>7s}")
keys = sorted({(v, s) for (v, s, o) in xt}, key=lambda k: (k[0], k[1]))
for v, s in keys:
    a = xt.get((v, s, "standalone"), 0)
    b_ = xt.get((v, s, "member"), 0)
    flag = "" if len({x[1] for x in xt if x[0] == v}) == 1 else "  <-- SAME VERSION, MULTIPLE SAVABLE"
    print(f"{v!r:8s} {s:>8d}  {a:>10d} {b_:>7d}{flag}")

# is savable constant per version tag?
per_ver = {}
for (v, s, o) in xt:
    per_ver.setdefault(v, set()).add(s)
print()
multi = {v: sorted(ss) for v, ss in per_ver.items() if len(ss) > 1}
print(f"versions whose tag maps to >1 savable value: {multi if multi else 'NONE'}")
print("=> savable is a per-version structural marker for every version present here."
      if not multi else "=> tag alone is NOT sufficient")

print()
print("=" * 78)
print("B) campaign prologue structure")
print("=" * 78)
print(f"{'campaign':40s} {'ver':6s} {'amt':>4s} {'junk':>5s} {'cnt_off':>8s} {'n':>4s} "
      f"{'tbl_end':>8s} {'hdr_end':>8s}")
junk_vals = {}
for cf, cb, c in camp_rows:
    junk = c["header_junk_len"]
    junk_vals[junk] = junk_vals.get(junk, 0) + 1
    print(f"{cf[:40]:40s} {c['version']:6s} {c['amount_of_unknown_numbers']:>4d} "
          f"{junk:>5d} {c['count_field_offset']:>8d} {c['member_count']:>4d} "
          f"{c['table_end']:>8d} {8 + 4 * c['amount_of_unknown_numbers']:>8d}")
print()
print(f"header_junk_len distribution: {dict(sorted(junk_vals.items()))}")
print(f"campaigns total: {len(camp_rows)}")
print("count_field_offset values: "
      f"{sorted({c['count_field_offset'] for _, _, c in camp_rows})}")
print("header lengths 8+4*amount values: "
      f"{sorted({8 + 4 * c['amount_of_unknown_numbers'] for _, _, c in camp_rows})}")
print("member counts by campaign: "
      f"{sorted(set(mem_count_by_camp.values()))}")

# the "64-byte index table" claim: is the prologue ever exactly 64 bytes before members?
gap = {c["count_field_offset"] - (8 + 4 * c["amount_of_unknown_numbers"]) for _, _, c in camp_rows}
print(f"distinct (count_field_offset - header_end) values: {sorted(gap)}")
print(f"campaigns where that gap == 64: "
      f"{sum(1 for _,_,c in camp_rows if c['count_field_offset'] - (8 + 4*c['amount_of_unknown_numbers']) == 64)}"
      f" / {len(camp_rows)}")

print()
print("=" * 78)
print("C) how many members does the OLD magic-scan recipe find?")
print("=" * 78)
tot_old = 0
missed = []
for cf, cb, c in camp_rows:
    old = old_magic_scan(cb)
    tot_old += len(old)
    gt_offsets = {m["offset"] for m in c["members"]}
    found_offsets = {off for _, off, _ in old}
    for m in c["members"]:
        if m["offset"] not in found_offsets:
            # measure why
            mb = m["data"]
            ver = mb[0:4].decode("ascii", "replace")
            instr_len = int.from_bytes(mb[16:20], "little")
            missed.append((cf, m["name"], ver, m["offset"], instr_len))
    extra = found_offsets - gt_offsets
    if extra:
        print(f"  NOTE {cf}: magic scan found {len(extra)} offsets not in the member table")
print(f"deterministic member table total : {sum(mem_count_by_camp.values())}")
print(f"old magic-scan recipe total      : {tot_old}")
print(f"missed by magic scan             : {len(missed)}")
print()
print("the missed members (why: instructions length pushes header past the 400 cap):")
maxinstr = 0
for cf, name, ver, off, instr_len in missed:
    maxinstr = max(maxinstr, instr_len)
    print(f"  {cf[:34]:34s} {name[:30]:30s} ver={ver!r:7s} off={off:<7d} instr_len={instr_len}")
if missed:
    print(f"max instructions length among missed members: {maxinstr}")

json.dump({"instances": tot,
           "cross_tab": {f"{v}|{s}|{o}": n for (v, s, o), n in xt.items()},
           "member_table_total": sum(mem_count_by_camp.values()),
           "old_scan_total": tot_old,
           "missed": missed,
           "junk_dist": {str(k): v for k, v in junk_vals.items()}},
          open(os.path.join(HERE, "campaign_measure.json"), "w", encoding="utf-8"), indent=2)
print()
print("wrote campaign_measure.json")
