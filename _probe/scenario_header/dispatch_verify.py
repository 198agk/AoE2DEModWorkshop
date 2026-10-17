# -*- coding: utf-8 -*-
"""dispatch_verify.py -- final verification of the savable-dispatch locator.

Runs header_layout.locate() -- a pure dispatch, NO candidate list, NO byte
scanning -- over every scenario instance on this machine (standalone files and
campaign members), and dumps the full field grid for one representative of
each savable family.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign import parse_campaign                      # noqa: E402
from header_layout import (                              # noqa: E402
    SAVABLE_LAYOUT, field_offsets, inflate_body, locate, read_savable, read_version,
)

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
ROOTS = [os.path.join(GAME, "resources", "_common", "drs"),
         os.path.join(GAME, "resources", "_common", "campaign"),
         os.path.join(GAME, "resources", "_common", "scenario"),
         r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"]
CAMP_DIR = os.path.join(GAME, "resources", "_common", "campaign")

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


# ---- enumerate -------------------------------------------------------------
standalone = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            if f.lower().endswith((".aoe2scenario", ".scx")):
                standalone.append(os.path.join(dp, f))
standalone.sort()

camp_rows = []
for cf in sorted(os.listdir(CAMP_DIR)):
    if cf.lower().endswith(".aoe2campaign"):
        cb = open(os.path.join(CAMP_DIR, cf), "rb").read()
        camp_rows.append((cf, cb, parse_campaign(cb)))

instances = [("standalone", os.path.basename(p), open(p, "rb").read()) for p in standalone]
for cf, cb, c in camp_rows:
    for m in c["members"]:
        instances.append(("member", f"{cf}::{m['name']}", m["data"]))

P("=" * 78)
P("PURE-DISPATCH LOCATOR  (deflate_offset = HEADER_LAYOUT[savable].size(bytes))")
P("=" * 78)
P(f"standalone files: {len(standalone)}   campaign members: "
  f"{sum(c['member_count'] for _, _, c in camp_rows)}   instances: {len(instances)}")
P()

ok = 0
bad = []
unregistered = {}
per_combo = {}
for origin, name, b in instances:
    off, layout, data, diag = locate(b)
    combo = (read_version(b), read_savable(b))
    per_combo.setdefault(combo, {"layouts": set(), "offsets": set(), "n": 0})
    per_combo[combo]["n"] += 1
    per_combo[combo]["layouts"].add(layout)
    per_combo[combo]["offsets"].add(off)
    if off is not None and layout is not None and data:
        ok += 1
    else:
        sv = read_savable(b)
        if sv not in SAVABLE_LAYOUT:
            unregistered.setdefault(sv, []).append(f"{origin}:{name}")
        bad.append((origin, name, diag))

P(f"RESULT: {ok}/{len(instances)} instances resolved by pure dispatch")
P(f"        {len(bad)} unresolved")
for x in bad[:40]:
    P("   FAIL", x)
P()

P("measured (version, savable) -> layout / deflate offset / count:")
for (v, s), d in sorted(per_combo.items()):
    offs = sorted(x for x in d["offsets"] if x is not None)
    P(f"   ver={v!r:8s} savable={s}  n={d['n']:3d}  layout={sorted(x for x in d['layouts'] if x)}"
      f"  deflate_offset(s)={offs if len(offs) < 6 else str(offs[:6]) + '...'}")
P()

# ---- field grid per family -------------------------------------------------
P("=" * 78)
P("FIELD GRID PER FAMILY  (explicit byte offsets)")
P("=" * 78)
by_base = {}
for p in standalone:
    by_base.setdefault(os.path.basename(p), p)

REPS = ["real_world_britain.scx", "real_world_antarctica.scx", "real_world_nippon.scx",
        "0_E3_Scenario.aoe2scenario", "special_map_canyons.scx",
        "The Siege.aoe2scenario", "default0.aoe2scenario"]
for base in REPS:
    p = by_base.get(base)
    if not p:
        P(f"{base}: NOT FOUND")
        continue
    b = open(p, "rb").read()
    sv = read_savable(b)
    lay = SAVABLE_LAYOUT.get(sv)
    P()
    P(f"--- {base}   size={len(b)}  ver={read_version(b)!r}  savable={sv}  layout={lay}")
    if lay is None:
        continue
    h = field_offsets(b, lay)
    for k in ("header_length", "savable", "timestamp_of_last_save", "scenario_instructions",
              "legacy_unknown_after_instructions", "individual_victories_used", "player_count",
              "unknown_value", "unknown_value_2", "amount_of_unknown_numbers",
              "unknown_numbers", "creator_name", "trigger_count"):
        if k in h:
            o, n = h[k]
            raw = b[o:o + n] if n else b""
            P(f"      @{o:<6d} len={str(n):<6s} {k:38s} {raw[:28]!r}")
    P(f"      @{h['_deflate_offset'][0]:<6d} {'STREAM STARTS HERE':38s} "
      f"next16={b[h['_deflate_offset'][0]:h['_deflate_offset'][0]+16].hex(' ')}")
    data, eof, err = inflate_body(b, h["_deflate_offset"][0])
    P(f"      -> eof={eof} body_bytes={len(data)} err={err}")
    # prologue-independent cross-check: does any OTHER offset in 4..3000 inflate
    # to end-of-stream with >=1000 bytes?  (proves uniqueness, not used to locate)
    others = []
    for cand in range(4, min(3000, len(b))):
        if cand == h["_deflate_offset"][0]:
            continue
        d2, e2, _ = inflate_body(b, cand)
        if e2 and len(d2) >= 1000:
            others.append((cand, len(d2)))
    P(f"      other offsets in 4..3000 that fully inflate: {others if others else 'NONE'}")

# ---- savable histogram -----------------------------------------------------
P()
P("=" * 78)
P("SAVABLE HISTOGRAM over all instances")
P("=" * 78)
hist = {}
for _o, _n, b in instances:
    hist[read_savable(b)] = hist.get(read_savable(b), 0) + 1
for k in sorted(hist):
    P(f"   savable={k}  n={hist[k]:3d}  -> {SAVABLE_LAYOUT.get(k, 'UNREGISTERED')}")
P()
P(f"distinct savable values: {sorted(hist)}   registered: {sorted(SAVABLE_LAYOUT)}")
P(f"unregistered savable values: {sorted(set(hist) - set(SAVABLE_LAYOUT))}")

open(os.path.join(HERE, "dispatch_verify_output.txt"), "w", encoding="utf-8").write("\n".join(out))
json.dump({"instances": len(instances), "resolved": ok, "unresolved": len(bad),
           "savable_hist": hist,
           "combo": {f"{v}|{s}": {"n": d["n"], "layouts": sorted(x for x in d["layouts"] if x),
                                  "offsets": sorted(x for x in d["offsets"] if x is not None)}
                     for (v, s), d in per_combo.items()}},
          open(os.path.join(HERE, "dispatch_verify.json"), "w", encoding="utf-8"), indent=2)
P()
P("wrote dispatch_verify_output.txt / dispatch_verify.json")
