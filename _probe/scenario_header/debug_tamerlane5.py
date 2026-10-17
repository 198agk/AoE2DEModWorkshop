# -*- coding: utf-8 -*-
"""Diagnose the one campaign member whose deflate stream the structural locator
could not confirm: K1_Tamerlane_5.aoe2scenario (from King's campaign).
Dumps its header and brute-force ground-truths the offsets, so we can tell whether
the structural model is wrong, or the file itself is unusual/truncated.
"""
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign import parse_campaign   # noqa: E402
from scenario_header import parse_file_header, decompress_body, candidate_layouts, HeaderParseError  # noqa: E402

CAMP_DIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"
VER_RE = re.compile(rb"1\.\d\d\x00\x00\x00\x00")

target = None
for f in sorted(os.listdir(CAMP_DIR)):
    if not f.endswith(".aoe2campaign"):
        continue
    b = open(os.path.join(CAMP_DIR, f), "rb").read()
    try:
        c = parse_campaign(b)
    except Exception:
        continue
    for m in c["members"]:
        if m["name"].startswith("K1_Tamerlane_5"):
            target = (f, m)
if target is None:
    print("not found")
    sys.exit(1)

camp, m = target
d = m["data"]
print(f"campaign={camp} member={m['name']} size={len(d)} version={d[:4]!r}")
print(f"first 96 bytes: {d[:96].hex(' ')}")
print(f"magic hits inside member: {[x.start() for x in VER_RE.finditer(d)]}")

for layout in candidate_layouts(d[:4].decode("ascii", "replace")):
    try:
        h = parse_file_header(d, layout)
    except HeaderParseError as e:
        print(f"  layout {layout}: HeaderParseError {e}")
        continue
    print(f"  layout {layout}: deflate_offset={h['deflate_offset']} "
          f"unknown_value={h['unknown_value']} player_count={h['player_count']} "
          f"amount={h['amount_of_unknown_numbers']} creator={h['creator_name']!r} "
          f"trigger_count={h['trigger_count']} instructions_len={len(h['scenario_instructions'])}")
    data, eof, err = decompress_body(d, h["deflate_offset"])
    print(f"     -> eof={eof} out={len(data)} err={err}")

print("-- ground truth: every offset with a raw-deflate stream reaching eof --")
found = []
for off in range(4, len(d) - 1):
    data, eof, err = decompress_body(d, off)
    if eof:
        found.append((off, len(data)))
found.sort(key=lambda t: -t[1])
for off, n in found[:10]:
    print(f"   off={off} out={n}")
print(f"   total valid offsets={len(found)}")
if found:
    print(f"   LONGEST = off={found[0][0]} out={found[0][1]}")
