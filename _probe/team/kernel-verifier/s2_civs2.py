# -*- coding: utf-8 -*-
"""Reconstruct the 63 civ blocks from raw bytes only (no product parser).

A civ record begins with: u8 player_type, debug_string name,
i16 n_resources, i16 tech_tree_id, i16 team_bonus_id, f32[n_resources],
u8 icon_set, i16 n_unit_pointers, i32[n_unit_pointers], then that many unit
records.  We validate that prefix chain on every candidate name marker and
require exactly 63 survivors with a sane unit-pointer count.
"""
import io
import json
import struct
import zlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = GAME + r"\resources\_common\dat\empires2_x2_p1.dat"
MOD = (r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch"
       r"\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat")
CIVJSON = GAME + r"\resources\_common\dat\civilizations.json"
MARKER = 0x0A60


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


def markers(blob):
    """Every marker-shaped debug string: (marker_off, payload_off, payload)."""
    out = []
    b = MARKER.to_bytes(2, "little")
    i = blob.find(b)
    n = len(blob)
    while i != -1:
        if i + 4 <= n:
            ln = struct.unpack_from("<H", blob, i + 2)[0]
            if 0 < ln <= 64 and i + 4 + ln <= n:
                pay = blob[i + 4:i + 4 + ln]
                if all(32 <= c < 127 for c in pay):
                    out.append((i, i + 4, pay))
        i = blob.find(b, i + 1)
    return out


def try_civ_header(blob, poff, ln):
    """Return dict describing a validated civ header, or None."""
    p = poff + ln
    try:
        n = struct.unpack_from("<h", blob, p)[0]
        if not (0 < n <= 64):
            return None
        tt, tb = struct.unpack_from("<hh", blob, p + 2)
        if not (0 <= tt < 4000 and 0 <= tb < 4000):
            return None
        q = p + 6 + 4 * n
        icon = blob[q]
        m = struct.unpack_from("<h", blob, q + 1)[0]
        if not (50 <= m <= 4000):
            return None
        ptrs = struct.unpack_from("<%di" % m, blob, q + 3)
        if sum(1 for x in ptrs if x) < 10:
            return None
        return {"n_res": n, "tt": tt, "tb": tb, "icon": icon,
                "ptrs": m, "nonzero": sum(1 for x in ptrs if x),
                "units_off": q + 3 + 4 * m}
    except struct.error:
        return None


def main():
    blob = inflate(BASE)
    civ = json.load(io.open(CIVJSON, encoding="utf-8-sig"))["civilization_list"]
    tokens = set()
    for c in civ:
        for k in ("internal_name", "data_name", "tech_tree_name"):
            v = c.get(k)
            if v:
                tokens.add(v.encode("ascii", "ignore"))
    cands = []
    for moff, poff, pay in markers(blob):
        if pay not in tokens:
            continue
        h = try_civ_header(blob, poff, len(pay))
        if h:
            cands.append((moff, pay.decode(), h))
    print("validated civ headers:", len(cands))
    for i, (o, name, h) in enumerate(cands[:4]):
        print("  #%d @%d %-12s n_res=%d tt=%d tb=%d ptrs=%d nonzero=%d"
              % (i, o, name, h["n_res"], h["tt"], h["tb"], h["ptrs"],
                 h["nonzero"]))
    if len(cands) != 63:
        print("!! expected 63 civ headers")
        return

    # assign each changed primary to the civ block that contains it
    new = inflate(MOD)
    diffs = [i for i in range(len(blob)) if blob[i] != new[i]]
    prim = diffs[0::2]
    starts = [c[0] for c in cands]
    assign = []
    for a in prim:
        k = None
        for i, s in enumerate(starts):
            if s < a:
                k = i
        assign.append(k)
    print("primaries assigned to civ blocks:", len(assign))
    print("distinct civ blocks touched     :", len(set(assign)))
    print("exactly one primary per civ     :",
          sorted(assign) == list(range(63)))
    print("assignment:", assign)

    # each civ block must contain exactly one changed primary + one mirror
    bounds = starts + [len(blob)]
    per = []
    for i in range(63):
        lo, hi = bounds[i], bounds[i + 1]
        c = [o for o in diffs if lo <= o < hi]
        per.append(len(c))
    print("changed bytes per civ block     :", sorted(set(per)),
          "total", sum(per))
    print("blocks with exactly 2 changes   :", sum(1 for x in per if x == 2))

    # civ ordering vs. the game's own civilization_list order
    print("civ header order matches civilizations.json order:",
          [c[1] for c in cands] ==
          [c.get("data_name") or c.get("internal_name") for c in civ])
    print("names:", [c[1] for c in cands][:6], "...")


if __name__ == "__main__":
    main()
