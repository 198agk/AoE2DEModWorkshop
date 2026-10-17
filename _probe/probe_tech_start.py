# -*- coding: utf-8 -*-
"""Confirm where the tech section starts, and that `locate()`'s tail is it.

The tech intent needs a starting offset.  Two candidates exist: the parser's
recorded stage offset for the techs stage, and the locator's returned `tail`
(the byte just past the last civ).  If they agree for every dataset, the
compiler can reuse the tail it already has and never needs the stage table.
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

for tag, path in TARGETS:
    if not os.path.exists(path):
        print("MISSING %s" % tag)
        continue
    data, how = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, cs, gv, tail = L.locate(data, parser=p)

    print("%-8s gv=%-3d  tail=0x%X" % (tag, gv, tail))
    for name, off in [(t[0], t[1]) for t in p.stage_offsets]:
        if "Tech" in name or "Civ" in name or "Effect" in name:
            print("     stage %-16s @0x%X  (tail - off = %d)"
                  % (name, off, tail - off))

    # A tech stage could be either "count then records" or "records then count".
    for probe_off in (tail, tail + 2):
        # Peek the first i16 and see whether it looks like a count.
        n_here = struct.unpack_from("<h", data, probe_off)[0]
        print("     i16 @tail%+d = %d" % (probe_off - tail, n_here))

    # Walk the declared count from tail+2 and see where we land.
    n = struct.unpack_from("<h", data, tail)[0]
    r = L.Orec(data, tail + 2, gv=gv)
    ok = True
    try:
        for _ in range(n):
            P.read_tech(r)
    except Exception as exc:
        ok = False
        print("     walk from tail+2 FAILED: %r" % (exc,))
    if ok:
        print("     walk %d techs from tail+2 -> 0x%X  (stream 0x%X, remaining %d)"
              % (n, r.o, len(data), len(data) - r.o))
