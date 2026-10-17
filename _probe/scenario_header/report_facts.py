# -*- coding: utf-8 -*-
"""report_facts.py -- regenerate EVERY number quoted in SCENARIO_HEADER_REPORT.md.

One pass, no search, pure stdlib.  Read-only w.r.t. the game directory.
Writes report_facts.json + report_facts_output.txt next to this file.

Run:
    $env:PYTHONIOENCODING="utf-8"
    $py = "C:\\Users\\26913\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe"
    & $py "...\\_probe\\scenario_header\\report_facts.py"
"""
import hashlib
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from header_layout import locate, parse_header, SAVABLE_LAYOUT, read_version   # noqa: E402
from campaign_deterministic import parse_campaign_deterministic               # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DRS = os.path.join(GAME, "resources", "_common", "drs")
CAMP_DIR = os.path.join(GAME, "resources", "_common", "campaign")
PROFILE = (r"C:\Users\26913\Games\Age of Empires 2 DE"
           r"\76561198406248391\resources\_common\scenario")

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    # keep the transcript a pure-text file: version tags can embed a raw NUL
    s = s.replace("\x00", "\\x00")
    print(s)
    out.append(s)

facts = {}


def walk_scenarios(root):
    found = []
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            if f.lower().endswith((".aoe2scenario", ".scx")):
                found.append(os.path.join(dp, f))
    return sorted(found)


# ===========================================================================
P("=" * 78)
P("1. CORPUS ENUMERATION")
P("=" * 78)
singles = []
for root in (DRS, CAMP_DIR, PROFILE):
    singles.extend(walk_scenarios(root))
singles = sorted(set(singles))
P(f"standalone scenario-like files (recursive, .aoe2scenario + .scx): {len(singles)}")
by_ext = {}
for p in singles:
    by_ext[os.path.splitext(p)[1].lower()] = by_ext.get(os.path.splitext(p)[1].lower(), 0) + 1
P(f"  by extension: {by_ext}")
by_root = {}
for p in singles:
    for tag, root in (("drs", DRS), ("campaign", CAMP_DIR), ("profile", PROFILE)):
        if p.lower().startswith(root.lower()):
            by_root[tag] = by_root.get(tag, 0) + 1
P(f"  by root: {by_root}")

camp_files = sorted(f for f in os.listdir(CAMP_DIR) if f.lower().endswith(".aoe2campaign"))
P(f"campaign containers (.aoe2campaign): {len(camp_files)}")
facts["standalone_files"] = len(singles)
facts["standalone_by_ext"] = by_ext
facts["standalone_by_root"] = by_root
facts["campaign_files"] = len(camp_files)

# ===========================================================================
P()
P("=" * 78)
P("2. STRUCTURAL LOCATOR OVER EVERY INSTANCE  (the denominator)")
P("=" * 78)

instances = []          # (label, bytes)
for p in singles:
    instances.append((os.path.basename(p), open(p, "rb").read()))

members_by_camp = {}
for cf in camp_files:
    b = open(os.path.join(CAMP_DIR, cf), "rb").read()
    c = parse_campaign_deterministic(b)
    members_by_camp[cf] = c
    for m in c["members"]:
        instances.append((f"{cf}::{m['name']}", m["data"]))

P(f"total instances = {len(singles)} standalone + "
  f"{sum(len(c['members']) for c in members_by_camp.values())} members = {len(instances)}")

ok = 0
fail = []
pair_layout = {}        # (version, savable) -> set(layouts)
ver_hist = {}
sav_hist = {}
layout_hist = {}
offsets_sample = {}
records = []
for label, b in instances:
    off, lay, body, diag = locate(b)
    ver = diag["version"]
    sav = diag["savable"]
    ver_hist[ver] = ver_hist.get(ver, 0) + 1
    if sav is not None:
        sav_hist[sav] = sav_hist.get(sav, 0) + 1
    if off is None or lay is None or body is None:
        fail.append({"label": label, "diag": diag})
        continue
    ok += 1
    layout_hist[lay] = layout_hist.get(lay, 0) + 1
    pair_layout.setdefault((ver, sav), set()).add(lay)
    records.append({"label": label, "size": len(b), "version": ver, "savable": sav,
                    "layout": lay, "deflate_offset": off, "body_bytes": len(body)})

P(f"successfully located (header parsed AND raw-deflate reaches eof): {ok}/{len(instances)}")
P(f"FAILURES: {len(fail)}")
for f in fail:
    P(f"   {f['label']}: {f['diag']}")

facts["instances_total"] = len(instances)
facts["instances_ok"] = ok
facts["instances_fail"] = len(fail)
facts["failures"] = fail
facts["version_histogram"] = dict(sorted(ver_hist.items()))
facts["savable_histogram"] = dict(sorted(sav_hist.items()))
facts["layout_histogram"] = dict(sorted(layout_hist.items()))

P()
P("savable histogram (the layout selector):")
for k in sorted(sav_hist):
    P(f"   savable={k}  n={sav_hist[k]:<4d} -> {sorted(set().union(*[v for (vv, s), v in pair_layout.items() if s == k]))}")
P()
P("version-tag histogram over all instances:")
P("   " + ", ".join(f"{k}x{v}" for k, v in sorted(ver_hist.items())))

# ===========================================================================
P()
P("=" * 78)
P("3. (version, savable) -> layout : is savable ALONE sufficient?")
P("=" * 78)
amb = {k: sorted(v) for k, v in pair_layout.items() if len(v) > 1}
P(f"distinct (version, savable) pairs           : {len(pair_layout)}")
P(f"distinct version tags                       : {len(ver_hist)}")
P(f"pairs mapping to MORE THAN ONE layout        : {len(amb)}")
ver_to_sav = {}
for (v, s) in pair_layout:
    ver_to_sav.setdefault(v, set()).add(s)
multi = {v: sorted(s) for v, s in ver_to_sav.items() if len(s) > 1}
P(f"version tags mapping to MORE THAN ONE savable: {len(multi)}  -> {multi}")
P()
for (v, s) in sorted(pair_layout):
    P(f"   version={v!r:<8} savable={s}  -> {sorted(pair_layout[(v, s)])}")
facts["pairs"] = {f"{v}|{s}": sorted(l) for (v, s), l in sorted(pair_layout.items())}
facts["version_to_multiple_savables"] = multi
facts["savable_to_layout"] = {str(k): sorted(set().union(
    *[l for (vv, ss), l in pair_layout.items() if ss == k])) for k in sorted(sav_hist)}

# ===========================================================================
P()
P("=" * 78)
P("4. CAMPAIGN CONTAINER STRUCTURE (deterministic, zero search)")
P("=" * 78)
gaps = {}
hdr_ends = {}
count_offsets = {}
tile_ok = 0
rec_sizes = set()
counts = {}
total_members = 0
for cf in camp_files:
    c = members_by_camp[cf]
    gaps[c["count_field_offset"] - c["hdr_end"]] = gaps.get(c["count_field_offset"] - c["hdr_end"], 0) + 1
    hdr_ends[c["hdr_end"]] = hdr_ends.get(c["hdr_end"], 0) + 1
    count_offsets[c["count_field_offset"]] = count_offsets.get(c["count_field_offset"], 0) + 1
    last = c["records"][-1]
    tiles = last["offset"] + last["size"] == len(open(os.path.join(CAMP_DIR, cf), "rb").read())
    tile_ok += tiles
    for r in c["records"]:
        rec_sizes.add(r["record_size"])
    counts[c["member_count"]] = counts.get(c["member_count"], 0) + 1
    total_members += c["member_count"]

P(f"campaigns parsed with ZERO search              : {len(camp_files)}/{len(camp_files)}")
P(f"gap (count_field_offset - header_end) histogram: {gaps}")
P(f"header_end histogram                           : {hdr_ends}")
P(f"count_field_offset histogram                   : {count_offsets}")
P(f"member_count histogram                         : {counts}")
P(f"total members                                  : {total_members}")
P(f"distinct record sizes (16 + 2*len(name))       : {sorted(rec_sizes)}")
P(f"members tile exactly to EOF                    : {tile_ok}/{len(camp_files)}")

# the refuted 64-byte claim
P()
P("REFUTATION of the '64-byte index table' claim:")
P(f"   campaigns where (count_field_offset - header_end) == 64 : "
  f"{gaps.get(64, 0)}/{len(camp_files)}")
P(f"   campaigns where (count_field_offset - header_end) == 256: "
  f"{gaps.get(256, 0)}/{len(camp_files)}")
facts["campaign_gap_histogram"] = gaps
facts["campaign_header_end_histogram"] = hdr_ends
facts["campaign_count_field_offset_histogram"] = count_offsets
facts["campaign_member_count_histogram"] = counts
facts["campaign_total_members"] = total_members
facts["campaign_record_sizes"] = sorted(rec_sizes)
facts["campaign_tiling_ok"] = tile_ok

# ===========================================================================
P()
P("=" * 78)
P("5. BACK-TO-BACK INDEPENDENCE  (byte identity + exact consumption)")
P("=" * 78)
ident = []
for m in members_by_camp["dcam0.aoe2campaign"]["members"]:
    sp = os.path.join(PROFILE, m["name"])
    if os.path.isfile(sp):
        sb = open(sp, "rb").read()
        ident.append({"name": m["name"], "member_size": len(m["data"]),
                      "standalone_size": len(sb),
                      "member_sha1": hashlib.sha1(m["data"]).hexdigest(),
                      "standalone_sha1": hashlib.sha1(sb).hexdigest(),
                      "identical": m["data"] == sb})
for i in ident:
    P(f"   {i['name']}: member={i['member_size']}B standalone={i['standalone_size']}B "
      f"identical={i['identical']} sha1={i['member_sha1'][:12]}")
facts["byte_identity"] = ident

# exact consumption: member's own byte count vs its deflate stream end
consume_ok = 0
for label, b in instances:
    if "::" not in label:
        continue
    off, lay, body, diag = locate(b)
    if off is None:
        continue
    d = zlib.decompressobj(-15)
    outb = d.decompress(b[off:])
    # unused_data is what the inflater did NOT consume -> should be empty
    if d.eof and len(d.unused_data) == 0:
        consume_ok += 1
P(f"   members whose deflate stream consumes the member's bytes EXACTLY: "
  f"{consume_ok}/{total_members}")
facts["members_exact_consumption"] = consume_ok

# ===========================================================================
P()
P("=" * 78)
P("6. HEADER FIELD GRID, ONE REPRESENTATIVE PER LAYOUT")
P("=" * 78)
reps = {}
for label, b in instances:
    off, lay, body, diag = locate(b)
    if lay and lay not in reps:
        reps[lay] = (label, b, off, body)
for lay in ("L_SHORT", "L_LONG_NC", "L_LONG_C", "M_IVU", "M_NOIVU"):
    if lay not in reps:
        P(f"   {lay}: NO REPRESENTATIVE FOUND")
        continue
    label, b, off, body = reps[lay]
    h = parse_header(b, lay)
    P()
    P(f"--- {lay}   file={label}  size={len(b)}  version={read_version(b)!r} "
      f"savable={struct.unpack_from('<i', b, 8)[0]}")
    for k, v in h.items():
        if k.startswith("_"):
            continue
        P(f"      @{v[0]:<6d} {k:<38} {v[1] if v[1] is not None else 'var'} bytes")
    P(f"      @{h['_deflate_offset'][0]:<6d} >>> RAW DEFLATE STREAM STARTS <<<")
    P(f"      instructions={len(h['_instructions'])}B creator={h['_creator']!r} "
      f"player_count={h['_player_count']} numbers={h['_numbers']} "
      f"trigger_count={h['_trigger_count']}")
    P(f"      inflated body = {len(body):,} bytes")

# ===========================================================================
P()
P("=" * 78)
P("7. UNIQUE-OFFSET CHECK: (version, savable) group -> is the offset constant?")
P("=" * 78)
grp = {}
for r in records:
    if "::" in r["label"]:
        continue          # standalone files with long instructions vary; use as-is below
    grp.setdefault((r["version"], r["savable"]), []).append(r)
for k in sorted(grp):
    offs = sorted({r["deflate_offset"] for r in grp[k]})
    P(f"   {k}: n={len(grp[k]):<3d} deflate offsets seen = {offs}")
P()
P("   NOTE: the deflate offset is NOT a constant per version -- it is a function of")
P("   the header's VARIABLE-LENGTH str32 fields.  The offset ALGORITHM is constant;")
P("   the offset VALUE is data-dependent.  (Both statements are measured above.)")

json.dump(facts, open(os.path.join(HERE, "report_facts.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
open(os.path.join(HERE, "report_facts_output.txt"), "w", encoding="utf-8").write("\n".join(out))
P()
P("wrote report_facts.json / report_facts_output.txt")
