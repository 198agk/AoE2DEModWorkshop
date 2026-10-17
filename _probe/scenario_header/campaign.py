# -*- coding: utf-8 -*-
"""campaign.py -- structural parser for AoE II DE campaign files (.aoe2campaign).

Pure stdlib. Read-only.

FINDINGS THIS MODULE ENCODES (all measured against the 42 shipped campaigns)
--------------------------------------------------------------------------
A .aoe2campaign is NOT a bare concatenation of scenarios.  It is:

    campaign header           (version "2.00", ...)
    u32 member_count
    member_count * member_record
    member_count * <complete standalone .aoe2scenario file, back-to-back>

member_record (variable length, deterministic):
    u32 member_size          # byte length of the member scenario file
    u32 member_offset        # absolute offset of the member inside the campaign
    u16 0x0A60               # constant sentinel (2656)
    u16 name_len
    char name[name_len]      # e.g. b"A1_Tariq1.aoe2scenario"
    u16 0x0A60               # the same sentinel again
    u16 name_len             # repeated
    char name[name_len]      # repeated
  => record_size = 16 + 2 * name_len

The record table is therefore VARIABLE-length (its stride depends on the length of
each member's filename), which is exactly why a fixed 64-byte index table was
never found, and why members are not at fixed strides.
"""

from __future__ import annotations

import struct

__all__ = ["parse_campaign", "CampaignParseError", "SENTINEL"]

SENTINEL = 0x0A60          # the u16 constant found twice per member record
MAX_NAME = 255             # member filenames are far shorter
MIN_COUNT = 1
MAX_COUNT = 4096


class CampaignParseError(ValueError):
    pass


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _try_record(b, o):
    """Decode one member record at offset o.  Returns (record, next_offset) or None."""
    if o + 16 > len(b):
        return None
    size = _u32(b, o)
    off = _u32(b, o + 4)
    sent1 = _u16(b, o + 8)
    n = _u16(b, o + 10)
    if sent1 != SENTINEL or not (MIN_COUNT <= n <= MAX_NAME):
        return None
    p = o + 12
    if p + n > len(b):
        return None
    name1 = b[p:p + n]
    if not all(32 <= c < 127 for c in name1):
        return None
    p += n
    if p + 4 + n > len(b):
        return None
    if _u16(b, p) != SENTINEL:
        return None
    if _u16(b, p + 2) != n:
        return None
    p += 4
    name2 = b[p:p + n]
    if name2 != name1:
        return None
    p += n
    return {"size": size, "offset": off, "name": name1.decode("ascii"),
            "record_offset": o, "record_size": p - o}, p


def parse_campaign(b: bytes):
    """Parse a .aoe2campaign into its header, member table and member slices.

    Returns dict with: version, member_count, table_offset, records, members.
    Raises CampaignParseError if no consistent record table can be decoded.
    """
    if len(b) < 16:
        raise CampaignParseError("file too small")
    version = b[0:4].decode("ascii", "replace")
    if not version.startswith("2."):
        raise CampaignParseError(f"not a campaign version tag: {b[0:4]!r}")

    amount = _u32(b, 4)
    if not (0 <= amount <= 64):
        raise CampaignParseError(f"implausible amount_of_unknown_numbers {amount}")
    hdr_end = 8 + 4 * amount

    # The campaign name is NUL-padded ASCII right after the unknown-number list.
    name_bytes = b[hdr_end:hdr_end + 64].split(b"\x00")[0]
    try:
        camp_name = name_bytes.decode("ascii")
    except UnicodeDecodeError:
        camp_name = name_bytes.decode("ascii", "replace")

    # Search for a member table: u32 count, then `count` decodable records whose
    # first record's offset points exactly past the table and whose sizes tile the
    # remainder of the file.
    best = None
    for count_off in range(hdr_end, min(len(b), hdr_end + 4096)):
        count = _u32(b, count_off)
        if not (MIN_COUNT <= count <= MAX_COUNT):
            continue
        recs = []
        p = count_off + 4
        ok = True
        for _ in range(count):
            r = _try_record(b, p)
            if r is None:
                ok = False
                break
            recs.append(r[0])
            p = r[1]
        if not ok or not recs:
            continue
        if recs[0]["offset"] != p:
            continue
        if recs != sorted(recs, key=lambda r: r["offset"]):
            continue
        if any(r["offset"] + r["size"] > len(b) for r in recs):
            continue
        last = recs[-1]
        if last["offset"] + last["size"] != len(b):
            continue
        best = (count_off, count, recs, p)
        break

    if best is None:
        raise CampaignParseError("no consistent member record table found")
    count_off, count, recs, table_end = best

    members = []
    for r in recs:
        members.append({"name": r["name"], "offset": r["offset"],
                        "size": r["size"], "data": b[r["offset"]:r["offset"] + r["size"]]})

    return {
        "version": version,
        "amount_of_unknown_numbers": amount,
        "campaign_name": camp_name,
        "member_count": count,
        "count_field_offset": count_off,
        "table_offset": count_off + 4,
        "table_end": table_end,
        "header_junk_len": count_off - hdr_end,
        "records": recs,
        "members": members,
    }
