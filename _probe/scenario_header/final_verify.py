# -*- coding: utf-8 -*-
"""final_verify.py -- the definitive, reproducible verification pass.

1. Structural locator (FIXED 5-candidate list, no byte-offset scanning) over every
   scenario instance on the machine (standalone + campaign members).
2. Campaign member-table determinism: tiling, fixed count-field offset, and
   byte-identity of a member slice against the standalone file of the same name.
3. Full prologue dump for all 42 campaigns (the 256-byte region at 32..288).
4. Per-family field dump at explicit byte offsets (the layouts the report cites).
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign import parse_campaign  # noqa: E402
from legacy_grammar import CANDS  # noqa: E402
from scenario_header import decompress_body  # noqa: E402

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


# ---------------------------------------------------------------------------
P("=" * 78)
P("1) STRUCTURAL LOCATOR over every scenario instance")
P("=" * 78)
standalone = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dp, dn, fn in os.walk(root):
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
P(f"instances: {len(instances)}  ({len(standalone)} standalone + "
  f"{sum(c['member_count'] for _,_,c in camp_rows)} members)")

res = {}
fails = []
for origin, name, b in instances:
    hits = []
    for cname, fn in CANDS:
        try:
            off, info = fn(b)
        except Exception:
            continue
        data, eof, err = decompress_body(b, off)
        if eof and len(data) > 1000:
            hits.append((cname, off, len(data)))
    if len(hits) == 1:
        res[(origin, name)] = hits[0]
    else:
        fails.append((origin, name, hits))

P(f"instances with EXACTLY ONE inflating candidate: {len(res)}/{len(instances)}")
P(f"instances with 0 or >1 candidates        : {len(fails)}")
for f in fails:
    P("   ", f)

# distinct (version, savable) -> winning candidate map
combo = {}
for origin, name, b in instances:
    ver = b[0:4].decode("ascii", "replace")
    sav = int.from_bytes(b[8:12], "little", signed=True)
    win = res.get((origin, name))
    combo.setdefault((ver, sav), set()).add(win[0] if win else None)
P()
P("measured (version, savable) -> layout, over all instances:")
for (v, s), w in sorted(combo.items()):
    P(f"   version={v!r:9s} savable={s}  ->  {sorted(x for x in w if x)}")

# version histogram (instances)
vh = {}
for origin, name, b in instances:
    vh[b[0:4].decode("ascii", "replace")] = vh.get(b[0:4].decode("ascii", "replace"), 0) + 1
P()
P("version histogram over instances:")
for k in sorted(vh):
    P(f"   {k!r}: {vh[k]}")

# ---------------------------------------------------------------------------
P()
P("=" * 78)
P("2) campaign member-table determinism")
P("=" * 78)
P(f"{'campaign':24s} {'cnt_off':>7s} {'hdr_end':>7s} {'gap':>4s} {'n':>3s} "
  f"{'tbl_end':>7s} {'last_end':>9s} {'filesize':>9s} {'tiles':>5s}")
allgap = set()
allcnt = set()
tiling_ok = 0
for cf, cb, c in camp_rows:
    he = 8 + 4 * c["amount_of_unknown_numbers"]
    gap = c["count_field_offset"] - he
    allgap.add(gap); allcnt.add(c["count_field_offset"])
    last = c["records"][-1]
    tiles = (last["offset"] + last["size"] == len(cb))
    tiling_ok += tiles
    P(f"{cf:24s} {c['count_field_offset']:>7d} {he:>7d} {gap:>4d} {c['member_count']:>3d} "
      f"{c['table_end']:>7d} {last['offset']+last['size']:>9d} {len(cb):>9d} {str(tiles):>5s}")
P()
P(f"gap values          : {sorted(allgap)}   (all 42 equal? {len(allgap)==1})")
P(f"count_field_offsets : {sorted(allcnt)}   (all 42 equal? {len(allcnt)==1})")
P(f"tiling exact        : {tiling_ok}/{len(camp_rows)}")
P(f"member counts       : {sorted({c['member_count'] for _,_,c in camp_rows})}")
P(f"member-table total   : {sum(c['member_count'] for _,_,c in camp_rows)}")
P(f"member record table is VARIABLE stride: record_size = 16 + 2*len(name); "
  f"measured distinct record sizes = "
  f"{sorted({r['record_size'] for _,_,c in camp_rows for r in c['records']})}")

# byte-identity of a member vs the standalone file with the same name
P()
P("member slice vs standalone file of the same basename:")
by_name = {}
for p in standalone:
    by_name.setdefault(os.path.basename(p), []).append(p)
found = 0
for cf, cb, c in camp_rows:
    for m in c["members"]:
        if m["name"] in by_name:
            for sp in by_name[m["name"]]:
                sb = open(sp, "rb").read()
                same = sb == m["data"]
                found += 1
                P(f"   {m['name']}  member({len(m['data'])}B sha1={hashlib.sha1(m['data']).hexdigest()[:12]})")
                P(f"      vs {sp}  ({len(sb)}B sha1={hashlib.sha1(sb).hexdigest()[:12]})  IDENTICAL={same}")
if not found:
    P("   (no member basename matches a standalone file)")

# ---------------------------------------------------------------------------
P()
P("=" * 78)
P("3) campaign prologue — bytes 32..288, all 42 campaigns")
P("=" * 78)
for cf, cb, c in camp_rows:
    he = 8 + 4 * c["amount_of_unknown_numbers"]
    reg = cb[he:he + 256]
    name = reg.split(b"\x00")[0]
    # split the region into u64 words and classify
    words = [struct.unpack_from("<Q", reg, i)[0] for i in range(0, 256, 8)]
    ptr_like = sum(1 for w in words if w >> 32 in (0x7FF6, 0x7FF7, 0x7FF8, 0x7FF9, 0x7FFA,
                                                   0x7FFB, 0x7FFC, 0x7FFD, 0x7FFE, 0x7FFF)
                   or (w >> 40) in (0x1F4, 0x1F5, 0x1F6, 0x1F7, 0x1F8, 0x214, 0x215))
    P(f"{cf:24s} name={name!r:10s} u64_ptr_like={ptr_like:2d}/32 "
      f"first8={reg[:8]!r} w0={words[0]:#018x} w1={words[1]:#018x} w2={words[2]:#018x}")
names = [cb[8 + 4 * c["amount_of_unknown_numbers"]:
            8 + 4 * c["amount_of_unknown_numbers"] + 256].split(b"\x00")[0].decode("ascii", "replace")
         for cf, cb, c in camp_rows]
P()
P(f"distinct campaign-name prefixes: {names}")
P("=> the 256-byte region begins with a NUL-terminated ASCII campaign name and is "
  "dominated by 64-bit values whose high words are 0x00007ffX (Windows stack) and "
  "0x0001f4XX (Windows heap): leaked uninitialized pointers [I].")

# ---------------------------------------------------------------------------
P()
P("=" * 78)
P("4) per-family FileHeader field dump at explicit byte offsets")
P("=" * 78)
by_base = {}
for p in standalone:
    by_base.setdefault(os.path.basename(p), p)

REPRESENTATIVES = [
    ("1.21 savable=2", "real_world_britain.scx"),
    ("1.21 savable=3", "real_world_antarctica.scx"),
    ("1.33 savable=4", "real_world_nippon.scx"),
    ("1.35 savable=5", "0_E3_Scenario.aoe2scenario"),
    ("1.36 savable=5", "special_map_canyons.scx"),
    ("1.53 savable=6", "The Siege.aoe2scenario"),
    ("1.59 savable=6", "default0.aoe2scenario"),
]
for label, base in REPRESENTATIVES:
    path = by_base.get(base)
    if not path:
        P(f"{label}: NOT FOUND (basename {base})")
        continue
    b = open(path, "rb").read()
    ver = b[0:4].decode("ascii", "replace")
    sav = int.from_bytes(b[8:12], "little", signed=True)
    instr_len = int.from_bytes(b[16:20], "little")
    win = None
    for cname, fn in CANDS:
        try:
            off, info = fn(b)
        except Exception:
            continue
        data, eof, err = decompress_body(b, off)
        if eof and len(data) > 1000:
            win = (cname, off, len(data))
            break
    P(f"{label:16s} ver={ver!r:8s} savable={sav} size={len(b)} "
      f"header_length={int.from_bytes(b[4:8],'little')} instr_len={instr_len}")
    P(f"    -> layout={win[0] if win else None} deflate_offset={win[1] if win else None} "
      f"body_bytes={win[2] if win else None}")
    P(f"    first 32 bytes: {b[:32].hex(' ')}")
    P(f"    tail-of-header 16 bytes before stream: {b[(win[1]-16) if win else 0:win[1] if win else 0]!r}")

open(os.path.join(HERE, "final_verify_output.txt"), "w", encoding="utf-8").write("\n".join(out))
json.dump({"instances": len(instances),
           "resolved": len(res),
           "fails": [(o, n, str(h)) for o, n, h in fails],
           "combo": {f"{v}|{s}": sorted(x for x in w if x) for (v, s), w in combo.items()},
           "version_hist": vh,
           "gap_values": sorted(allgap),
           "count_offsets": sorted(allcnt),
           "tiling_ok": tiling_ok,
           "member_total": sum(c['member_count'] for _, _, c in camp_rows)},
          open(os.path.join(HERE, "final_verify.json"), "w", encoding="utf-8"), indent=2)
P()
P("wrote final_verify_output.txt and final_verify.json")
