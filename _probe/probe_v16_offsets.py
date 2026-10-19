# -*- coding: utf-8 -*-
r"""Locate the two bytes v16 needs: British 2550's button slot, Incas 2550's gate.

Read-only.  Prints the offsets and re-reads them back so the builder can patch
exactly two bytes and assert it changed exactly two.
"""
import contextlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.locate as L                            # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
GATE_OFFSET = 56

raw, how = P.load_dat(G.dat_path(GAME))
print("dat : %d raw bytes (%s)" % (len(raw), how))
pr = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    pr.parse()
civs, cs, gv, tail = L.locate(raw, parser=pr)
print("civs: %d ; clean EOF: %s" % (len(civs), pr.r.pos == len(raw)))

for name in ("British", "Incas"):
    civ = next(c for c in civs if c["name"] == name)
    u = next(x for x in civ["units"] if x["id"] == UNIT)
    tl = u["train_locations"][0]
    off = tl["_off_train_time"]
    tt, uid = struct.unpack_from("<hh", raw, off)
    print()
    print("%s unit %d" % (name, UNIT))
    print("   record start        : %d" % u.get("_creatable_start", -1))
    print("   train_location @%d : TrainTime=%d UnitID=%d ButtonID=%d"
          % (off, tt, uid, raw[off + 4]))
    print("   gate @%d            : Enabled=%d Disabled=%d"
          % (u["_creatable_start"] + GATE_OFFSET,
             raw[u["_creatable_start"] + GATE_OFFSET],
             raw[u["_creatable_start"] + GATE_OFFSET + 1]))

print()
print("PLAN")
brit = next(c for c in civs if c["name"] == "British")
incas = next(c for c in civs if c["name"] == "Incas")
_b = next(x for x in brit["units"] if x["id"] == UNIT)
_i = next(x for x in incas["units"] if x["id"] == UNIT)
_b_off = _b["train_locations"][0]["_off_train_time"] + 4
_i_off = _i["_creatable_start"] + GATE_OFFSET + 1        # Disabled
print("   British 2550 ButtonID @%d : %d -> 4   (slot that v5 proved works)"
      % (_b_off, raw[_b_off]))
print("   Incas   2550 Disabled @%d : %d -> 1   (hide it for the Incas only)"
      % (_i_off, raw[_i_off]))
print("   both in the same file, two bytes total, every other byte untouched")
