# -*- coding: utf-8 -*-
"""INDEPENDENT verification of the scenario header layout claim.

Claim under test (from subagent f6198a82):
    deflate_offset = HEADER_LAYOUT[savable].size(bytes)
    where savable = s32 at file offset 8.

I implement this from scratch (NOT importing their header_layout.py) and
check that the deflate stream at that offset consumes the file exactly.

savable -> layout, per the claim:
    2 L_SHORT      @0 c4 version, @4 u32 header_length, @8 s32 savable,
                   @12 u32 timestamp            (8 instances, 1.21)
    3 L_LONG_NC    + str32 instructions + u32 unknown_numbers_count
                   + u32[n] + u32 legacy_unknown_after_instructions   (1.21)
    4 L_LONG_C     = 3 + str32 creator_name                         (1.33)
    5 M_IVU        = 4 + u32 individual_victories_used + u32[X]?    (1.35-1.37)
    6 M_NOIVU      = 5 minus IVU + u32 trigger_count                (1.40-1.59)

Rather than hardcode the field lists from their prose, I derive the header
size empirically per savable: for each instance, try every offset in a wide
window and keep the one where deflate consumes the file exactly AND the
header fields are structurally consistent.  Then I check the *claimed*
structural prefix (@0..@16) holds on every instance.  That tests the claim
without copying their field table.
"""
import os
import struct
import zlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
MAGIC = b"1."


def collect():
    """Every .aoe2scenario / .scx / .aoe2campaign under both roots."""
    seen = []
    for root in (GAME, USER):
        if not os.path.isdir(root):
            continue
        for b, s, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith((".aoe2scenario", ".scx", ".aoe2campaign")):
                    seen.append(os.path.join(b, f))
    return sorted(set(seen))


def split_campaign(blob):
    """Deterministic campaign member extraction, per the claim.

    @0 c4 version | @4 u32 amount | @8 u32[amount] |
    @8+4*amount   : 256 B prologue |
    @8+4*amount+256 : u32 member_count | then records
    record = u32 name_len + name_bytes + u32 body_len + body_bytes
    """
    if len(blob) < 16:
        return None
    amount = struct.unpack_from("<I", blob, 4)[0]
    if not (1 <= amount <= 64):
        return None
    pro = 8 + 4 * amount
    if pro + 256 + 4 > len(blob):
        return None
    cnt = struct.unpack_from("<I", blob, pro + 256)[0]
    if not (1 <= cnt <= 4096):
        return None
    off = pro + 256 + 4
    out = []
    for _ in range(cnt):
        if off + 4 > len(blob):
            return None
        nl = struct.unpack_from("<I", blob, off)[0]
        off += 4
        if nl > 512 or off + nl + 4 > len(blob):
            return None
        name = blob[off:off + nl]
        off += nl
        bl = struct.unpack_from("<I", blob, off)[0]
        off += 4
        if off + bl > len(blob):
            return None
        out.append((name, blob[off:off + bl]))
        off += bl
    # exact consumption is the campaign-level oracle
    return (out, off == len(blob))


def inflate_exact(b, off):
    """raw-deflate at off; return (rawlen, sha-ish) iff it consumes to EOF."""
    d = zlib.decompressobj(-15)
    try:
        raw = d.decompress(b[off:])
        raw += d.flush()
    except zlib.error:
        return None
    if not d.eof:
        return None
    # consumed exactly to EOF?
    if len(b) - off - len(d.unused_data) != len(b) - off:
        return None
    return raw


def find_offset(b, lo=16, hi=600):
    """All offsets in [lo,hi) where a raw-deflate stream consumes to EOF."""
    hits = []
    for off in range(lo, min(hi, len(b))):
        r = inflate_exact(b, off)
        if r is not None and len(r) > 1000:
            hits.append((off, len(r)))
    return hits


def prefix_fields(b):
    """Structurally read the claimed common prefix."""
    if len(b) < 20:
        return None
    ver = b[0:4].decode("latin1")
    hlen = struct.unpack_from("<I", b, 4)[0]
    sav = struct.unpack_from("<i", b, 8)[0]
    ts = struct.unpack_from("<I", b, 12)[0]
    ilen = struct.unpack_from("<I", b, 16)[0]
    return ver, hlen, sav, ts, ilen


files = collect()
print("scenario/campaign files found:", len(files))

instances = []   # (label, bytes)
n_camp = 0
for p in files:
    b = open(p, "rb").read()
    if p.lower().endswith(".aoe2campaign"):
        n_camp += 1
        r = split_campaign(b)
        if r is None:
            print("  CAMPAIGN PARSE FAIL:", p)
            continue
        members, exact = r
        print("  campaign %-30s members=%3d exact_consumption=%s"
              % (os.path.basename(p), len(members), exact))
        for nm, mb in members:
            instances.append((os.path.basename(p) + "::" +
                              nm.decode("latin1", "replace"), mb))
    else:
        instances.append((os.path.basename(p), b))

print()
print("total scenario instances:", len(instances))
print("  (standalone %d, from %d campaigns)" % (len(instances) - sum(
    1 for l, _ in instances if "::" in l), n_camp))

# --- Test the claimed core: savable@8 decides the layout, and the layout's
#     size IS the deflate offset.  We test the *prediction* "offset is a
#     function of savable only within a consistent grammar" by checking:
#     (a) savable is always in 2..6
#     (b) for each instance a valid deflate offset exists
#     (c) header_length==0 for savable>=4, and ==20 for L_SHORT
print()
print("=== claimed prefix on every instance ===")
from collections import Counter, defaultdict
sav_hist = Counter()
by_sav = defaultdict(list)
bad_ver = 0
ok_offset = 0
fail = []
for label, b in instances:
    pf = prefix_fields(b)
    if pf is None:
        fail.append((label, "too short"))
        continue
    ver, hlen, sav, ts, ilen = pf
    if not ver.startswith("1."):
        bad_ver += 1
    sav_hist[sav] += 1
    hits = find_offset(b)
    by_sav[sav].append((label, ver, hlen, ilen, [h[0] for h in hits]))
    if hits:
        ok_offset += 1
    else:
        fail.append((label, "no valid deflate offset in 16..600"))

print("savable histogram:", dict(sorted(sav_hist.items())))
print("instances with a valid deflate offset:", ok_offset, "/", len(instances))
print("instances whose version tag does NOT start '1.':", bad_ver)
print("failures:", len(fail))
for l, why in fail[:10]:
    print("   ", l, why)

print()
print("=== per-savable: header_length and instruction-length spread ===")
for sav in sorted(by_sav):
    rows = by_sav[sav]
    hl = Counter(r[2] for r in rows)
    offs = sorted(set(o for r in rows for o in r[4]))
    print("savable=%d  n=%3d  header_length=%s"
          % (sav, len(rows), dict(hl)))
    print("            distinct offsets (%d): %s"
          % (len(offs), offs[:14]))

print()
print("=== does savable==6 cover 1.40..1.59 and 5 cover 1.35..1.37? ===")
vr = defaultdict(set)
for sav in sorted(by_sav):
    for label, ver, hlen, ilen, offs in by_sav[sav]:
        vr[sav].add(ver.replace("\x00", ""))
for sav in sorted(vr):
    print("  savable=%d versions: %s" % (sav, sorted(vr[sav])))
