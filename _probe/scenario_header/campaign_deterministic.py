# -*- coding: utf-8 -*-
"""campaign_deterministic.py -- remove the last search from the campaign parser.

campaign.py finds the member table by scanning `count_off` over a 4096-byte
window.  That was a scaffolding device.  Measured on all 42 shipped campaigns:

    count_field_offset - (8 + 4*amount_of_unknown_numbers) == 256   (42/42)

so the member count is at a FIXED, structurally-derived offset:

    member_count_offset = 8 + 4 * amount_of_unknown_numbers + 256

This script (a) proves the 256 constant again, (b) parses every campaign with a
zero-search parser, and (c) dumps the campaign FileHeader field grid.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign import SENTINEL, _try_record                     # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CAMP_DIR = os.path.join(GAME, "resources", "_common", "campaign")

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


def parse_campaign_deterministic(b: bytes):
    """Parse .aoe2campaign with NO scanning: every offset is derived.

        @0   c4    version tag ("2.00")
        @4   u32   amount_of_unknown_numbers  (always 6 in the 42 shipped files)
        @8   u32[amount]  unknown_numbers
        @8+4*amount  fixed 256-byte prologue (NUL-terminated campaign name +
                     leaked runtime pointers, see report)
        @8+4*amount+256  u32 member_count
        then member_count variable-length member records
        then the member scenario files, back-to-back, tiling to EOF
    """
    if len(b) < 12:
        raise ValueError("campaign too small")
    version = b[0:4].decode("ascii", "replace")
    if not version.startswith("2."):
        raise ValueError(f"not a campaign: {b[0:4]!r}")

    amount = struct.unpack_from("<I", b, 4)[0]
    hdr_end = 8 + 4 * amount
    prologue = b[hdr_end:hdr_end + PROLOGUE_LEN]
    camp_name = prologue.split(b"\x00")[0].decode("ascii", "replace")

    count_off = hdr_end + PROLOGUE_LEN
    count = struct.unpack_from("<I", b, count_off)[0]

    recs = []
    p = count_off + 4
    for _ in range(count):
        r = _try_record(b, p)
        if r is None:
            raise ValueError(f"member record {len(recs)} undecodable at {p}")
        recs.append(r[0])
        p = r[1]

    if recs[0]["offset"] != p:
        raise ValueError(f"first member offset {recs[0]['offset']} != table_end {p}")
    if recs[-1]["offset"] + recs[-1]["size"] != len(b):
        raise ValueError("members do not tile to EOF")

    return {
        "version": version, "amount_of_unknown_numbers": amount,
        "hdr_end": hdr_end, "prologue": prologue, "campaign_name": camp_name,
        "count_field_offset": count_off, "member_count": count,
        "table_offset": count_off + 4, "table_end": p,
        "records": recs,
        "members": [{"name": r["name"], "offset": r["offset"], "size": r["size"],
                     "data": b[r["offset"]:r["offset"] + r["size"]]} for r in recs],
    }


PROLOGUE_LEN = 256


def main():
    files = sorted(f for f in os.listdir(CAMP_DIR) if f.lower().endswith(".aoe2campaign"))
    P("=" * 78)
    P("DETERMINISTIC CAMPAIGN PARSE  (member_count @ 8 + 4*amount + 256; no search)")
    P("=" * 78)
    P(f"campaigns: {len(files)}")
    P()

    gaps = {}
    header_ok = 0
    tile_ok = 0
    total_members = 0
    rows = []
    for cf in files:
        b = open(os.path.join(CAMP_DIR, cf), "rb").read()
        try:
            c = parse_campaign_deterministic(b)
        except Exception as e:
            P(f"FAIL {cf}: {type(e).__name__}: {e}")
            continue
        header_ok += 1
        total_members += c["member_count"]
        gaps.setdefault(c["count_field_offset"] - c["hdr_end"], 0)
        gaps[c["count_field_offset"] - c["hdr_end"]] += 1
        last = c["records"][-1]
        tiles = last["offset"] + last["size"] == len(b)
        tile_ok += tiles
        rows.append((cf, c, len(b), tiles))
        P(f"OK   {cf:22s} size={len(b):>9d} ver={c['version']!r} amount={c['amount_of_unknown_numbers']} "
          f"cnt_off={c['count_field_offset']:>5d} gap={c['count_field_offset']-c['hdr_end']:>4d} "
          f"n={c['member_count']:>2d} table_end={c['table_end']:>6d} tiles={tiles} name={c['campaign_name']!r}")

    P()
    P(f"campaigns parsed with zero search : {header_ok}/{len(files)}")
    P(f"campaigns whose members tile to EOF: {tile_ok}/{len(files)}")
    P(f"total members                      : {total_members}")
    P(f"gap (count_field_offset - hdr_end) histogram: {gaps}")
    P()

    P("=" * 78)
    P("CAMPAIGN FileHeader field grid (first 320 bytes)")
    P("=" * 78)
    for cf, c, size, _t in rows[:6]:
        b = open(os.path.join(CAMP_DIR, cf), "rb").read()
        P()
        P(f"--- {cf}  size={size}  amount={c['amount_of_unknown_numbers']} hdr_end={c['hdr_end']}")
        P(f"    @0  c4   version              {b[0:4]!r}")
        P(f"    @4  u32  amount_of_unknown_numbers {c['amount_of_unknown_numbers']}")
        nums = [struct.unpack_from('<I', b, 8 + 4 * i)[0] for i in range(c['amount_of_unknown_numbers'])]
        P(f"    @8  u32[{c['amount_of_unknown_numbers']}] unknown_numbers {nums}")
        P(f"    @{c['hdr_end']} u8[256] prologue: name={c['campaign_name']!r}")
        pro = c["prologue"]
        nz = sum(1 for x in pro if x)
        words = [struct.unpack_from("<Q", pro, i)[0] for i in range(0, 256, 8)]
        hi = {}
        for w in words:
            hi[w >> 40] = hi.get(w >> 40, 0) + 1
        P(f"        nonzero bytes: {nz}/256 ; top-40-bits histogram: "
          f"{sorted(hi.items(), key=lambda kv: -kv[1])[:6]}")
        P(f"        first 48: {pro[:48].hex(' ')}")
        P(f"    @{c['count_field_offset']} u32 member_count = {c['member_count']}")
        for i, r in enumerate(c["records"]):
            P(f"        rec{i} @{r['record_offset']:<6d} size={r['record_size']:<3d} "
              f"member_size={r['size']:<8d} member_offset={r['offset']:<9d} name={r['name']!r}")
        P(f"    table_end={c['table_end']}  first member at {c['records'][0]['offset']}")

    open(os.path.join(HERE, "campaign_deterministic_output.txt"), "w", encoding="utf-8").write("\n".join(out))
    json.dump({"campaigns": len(files), "parsed": header_ok, "tiling_ok": tile_ok,
               "total_members": total_members, "gaps": {str(k): v for k, v in gaps.items()}},
              open(os.path.join(HERE, "campaign_deterministic.json"), "w", encoding="utf-8"), indent=2)
    P()
    P("wrote campaign_deterministic_output.txt / campaign_deterministic.json")


if __name__ == "__main__":
    main()
