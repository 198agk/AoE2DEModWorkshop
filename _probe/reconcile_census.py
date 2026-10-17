# -*- coding: utf-8 -*-
"""Reconcile `locate()`'s unit census against the authoritative reader's.

The locator exists to point at records the authoritative parser already walked,
so both must agree on how many physical unit records exist.  A mismatch means
one side skips or double-counts.

We count with `parser.read_civ()` (the authoritative walker) rather than
`Parser.stats`, because the parser deliberately does not retain the per-civ
record list -- it only records counts.
"""
import contextlib
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.dat import parser as P
from aoe2mod.dat import locate as L

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SUB = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
TARGETS = [
    ("BASE", os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")),
    ("550749", os.path.join(SUB, "550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48",
                            "resources", "_common", "dat", "empires2_x2_p1.dat")),
    ("423821", os.path.join(SUB, "423821_四月-juntuanzhangtianfumozu军团长天赋模组",
                            "resources", "_common", "dat", "empires2_x2_p1.dat")),
    ("297820", os.path.join(SUB, "297820_10 倍资源文明联盟3倍科技",
                            "resources", "_common", "dat", "empires2_x2_p1.dat")),
]


def authoritative_count(data, p):
    """Walk every civ with the authoritative reader; return (records, ptrs)."""
    stage8 = next(t for t in p.stage_offsets if t[0].startswith("8 Civs"))
    n_civ = struct.unpack_from("<h", data, stage8[1])[0]
    start = stage8[1] + 2
    r = P.Reader(data)
    r.pos = start
    r.gv = p.r.gv
    recs = 0
    ptrs = 0
    with contextlib.redirect_stdout(io.StringIO()):
        for _ in range(n_civ):
            c = P.read_civ(r)
            ptrs += c.get("unit_pointers_total", 0)
            recs += len(c.get("units", []))
    return recs, ptrs, r.pos


for tag, path in TARGETS:
    if not os.path.exists(path):
        print("MISSING %s" % tag)
        continue
    data, how = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()

    a_recs, a_ptrs, a_end = authoritative_count(data, p)
    civs, cs, gv, tail = L.locate(data, parser=p)
    l_recs = sum(len(c["units"]) for c in civs)
    l_ptrs = sum(c["unit_pointers_total"] for c in civs)

    ok = (a_recs == l_recs) and (a_ptrs == l_ptrs)
    print("%-8s gv=%-3d civs=%-3d  %s" % (tag, gv, len(civs), "MATCH" if ok else "MISMATCH"))
    print("   authoritative read_civ : ptrs=%-8d records=%-8d end=0x%X" % (a_ptrs, a_recs, a_end))
    print("   locate.walk_civ        : ptrs=%-8d records=%-8d tail=0x%X" % (l_ptrs, l_recs, tail))
