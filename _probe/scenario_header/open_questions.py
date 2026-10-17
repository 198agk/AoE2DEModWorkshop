# -*- coding: utf-8 -*-
"""open_questions.py -- measure, over EVERY instance, the fields we cannot yet
name.  Guessing is not allowed in the report, so every "unknown" statement must
carry a measured value histogram.

Covers:
  * header_length (u32 @4)             -- per layout
  * legacy_unknown_after_instructions  -- per legacy layout
  * unknown_value_2 (u32)              -- per layout
  * unknown_numbers[N]                 -- per layout
  * individual_victories_used          -- per layout
  * trigger_count                       -- missing where absent
  * campaign prologue 256 B            -- what kind of bytes they are

Run:
    $env:PYTHONIOENCODING="utf-8"
    & $py "...\\_probe\\scenario_header\\open_questions.py"
"""
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from header_layout import field_offsets, locate, read_version, read_savable     # noqa: E402
from campaign_deterministic import parse_campaign_deterministic                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DRS = os.path.join(GAME, "resources", "_common", "drs")
CAMP_DIR = os.path.join(GAME, "resources", "_common", "campaign")
PROFILE = (r"C:\Users\26913\Games\Age of Empires 2 DE"
           r"\76561198406248391\resources\_common\scenario")

out = []
def P(*a):
    s = " ".join(str(x) for x in a).replace("\x00", "\\x00")
    print(s)
    out.append(s)


def walk(root):
    r = []
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            if f.lower().endswith((".aoe2scenario", ".scx")):
                r.append(os.path.join(dp, f))
    return sorted(r)


instances = []
for root in (DRS, CAMP_DIR, PROFILE):
    for p in walk(root):
        instances.append((os.path.basename(p), open(p, "rb").read()))
camps = {}
for cf in sorted(f for f in os.listdir(CAMP_DIR) if f.lower().endswith(".aoe2campaign")):
    b = open(os.path.join(CAMP_DIR, cf), "rb").read()
    c = parse_campaign_deterministic(b)
    camps[cf] = (b, c)
    for m in c["members"]:
        instances.append((f"{cf}::{m['name']}", m["data"]))

P("=" * 78)
P("OPEN-QUESTION FIELDS, MEASURED OVER ALL 289 INSTANCES")
P("=" * 78)
P(f"instances: {len(instances)}")

hist_hl = collections.defaultdict(collections.Counter)       # layout -> header_length
hist_legacy = collections.Counter()
hist_uv2 = collections.defaultdict(collections.Counter)      # layout -> unknown_value_2
hist_nums = collections.defaultdict(collections.Counter)     # layout -> tuple(numbers)
hist_ivu = collections.Counter()
hist_trig = collections.defaultdict(collections.Counter)
n_ok = 0

for label, b in instances:
    off, lay, body, diag = locate(b)
    if lay is None:
        continue
    h = field_offsets(b, lay)
    n_ok += 1
    if "header_length" in h:
        hist_hl[lay][struct.unpack_from("<I", b, 4)[0]] += 1
    if "legacy_unknown_after_instructions" in h:
        o = h["legacy_unknown_after_instructions"][0]
        hist_legacy[struct.unpack_from("<I", b, o)[0]] += 1
    if "unknown_value_2" in h:
        o = h["unknown_value_2"][0]
        hist_uv2[lay][struct.unpack_from("<I", b, o)[0]] += 1
    if "unknown_numbers" in h:
        hist_nums[lay][tuple(h["_numbers"])] += 1
    if "individual_victories_used" in h:
        o = h["individual_victories_used"][0]
        hist_ivu[struct.unpack_from("<I", b, o)[0]] += 1
    if "trigger_count" in h:
        hist_trig[lay][h["_trigger_count"]] += 1

P(f"parsed: {n_ok}")
P()
P("header_length (u32 @4) by layout:")
for lay in sorted(hist_hl):
    tot = sum(hist_hl[lay].values())
    P(f"   {lay:<10} n={tot:<4d} values={dict(hist_hl[lay].most_common())}")
P()
P("legacy_unknown_after_instructions (u32, legacy layouts only):")
P(f"   n={sum(hist_legacy.values())}  value histogram={dict(hist_legacy.most_common())}")
P()
P("individual_victories_used (u32, M_IVU only):")
P(f"   n={sum(hist_ivu.values())}  value histogram={dict(hist_ivu.most_common())}")
P()
P("unknown_value_2 (u32) by layout:")
for lay in sorted(hist_uv2):
    tot = sum(hist_uv2[lay].values())
    P(f"   {lay:<10} n={tot:<4d} values={dict(hist_uv2[lay].most_common())}")
P()
P("unknown_numbers (u32[N]) by layout:")
for lay in sorted(hist_nums):
    tot = sum(hist_nums[lay].values())
    P(f"   {lay:<10} n={tot:<4d} distinct arrays={len(hist_nums[lay])}")
    for arr, cnt in hist_nums[lay].most_common(6):
        P(f"        {list(arr)}  x{cnt}")
P()
P("trigger_count by layout (shows WHERE it exists at all):")
for lay in sorted(hist_trig):
    tot = sum(hist_trig[lay].values())
    vals = sorted(hist_trig[lay])
    P(f"   {lay:<10} n={tot:<4d} min={min(vals)} max={max(vals)}")

# ---------------------------------------------------------------------------
P()
P("=" * 78)
P("CAMPAIGN PROLOGUE 256 B -- what ARE those bytes?")
P("=" * 78)
nz_counts = []
hi40 = collections.Counter()
name_ok = 0
names = []
for cf, (b, c) in sorted(camps.items()):
    pro = c["prologue"]
    nz_counts.append(sum(1 for x in pro if x))
    for i in range(0, 256 - 7, 8):
        hi40[struct.unpack_from("<Q", pro, i)[0] >> 40] += 1
    first = pro.split(b"\x00")[0]
    if first and all(32 <= ch < 127 for ch in first):
        name_ok += 1
        names.append(first.decode("ascii"))
P(f"campaigns: {len(camps)}")
P(f"prologue starts with a printable NUL-terminated ASCII name: {name_ok}/{len(camps)}")
P(f"distinct names: {len(set(names))}  e.g. {sorted(set(names))[:12]}")
P(f"nonzero byte count over the 256 B block: min={min(nz_counts)} max={max(nz_counts)}")
P()
P("top-40-bits of each 64-bit word in the prologue (0x7ffX / 0x0000 / ...):")
for k, v in hi40.most_common(10):
    kind = ""
    if k == 0x7FF:
        kind = "  <- Windows USER-MODE STACK pointer high bits"
    elif k == 0x000:
        kind = "  <- small integer / NULL"
    elif k in (0x001, 0x002, 0x1F4, 0x1F5):
        kind = "  <- Windows HEAP-ish / small"
    P(f"   0x{k:010x}  x{v}{kind}")

json.dump({
    "header_length": {k: dict(v) for k, v in hist_hl.items()},
    "legacy_unknown_after_instructions": dict(hist_legacy),
    "individual_victories_used": dict(hist_ivu),
    "unknown_value_2": {k: dict(v) for k, v in hist_uv2.items()},
    "unknown_numbers": {k: {"|".join(map(str, a)): c for a, c in v.items()}
                        for k, v in hist_nums.items()},
    "trigger_count_range": {k: [min(v), max(v), sum(v.values())] for k, v in hist_trig.items()},
    "prologue": {"campaigns": len(camps), "named_ok": name_ok,
                 "distinct_names": len(set(names)),
                 "nonzero_min": min(nz_counts), "nonzero_max": max(nz_counts)},
}, open(os.path.join(HERE, "open_questions.json"), "w", encoding="utf-8"), indent=2)
open(os.path.join(HERE, "open_questions_output.txt"), "w", encoding="utf-8").write("\n".join(out))
P()
P("wrote open_questions.json / open_questions_output.txt")
