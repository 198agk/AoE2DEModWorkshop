# -*- coding: utf-8 -*-
r"""THE MECHANISM CANDIDATE: `TechTree.UnitConnection.EnablingResearch`.

An earlier round found, by walking the `.dat` TechTree section by hand:

    unit connections total 266 / enabling research global 26 / civ-owned 47
    -> 46 of those 47 have an owner that is exactly the civilization the tree says
       can build the unit

That is a **per-civilization** mechanism living in the `.dat`, dropped by the parser
(`read_tech_tree` only returns counts).  If unit 2550's connection carries an
`EnablingResearch` resolved per civ, that is the gate the smoke6 write could not
change -- and it would explain the user's result exactly:

    Incas   CAN build 2550   (whatever the .dat says for civ 21)
    Britons CANNOT           (whatever the .dat says for civ 1)
    ...because the .dat, not the tree, decides.

Dump every connection whose unit is in the American regional set, and read 2550's
connection plus its neighbours in full.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, civs_start, gv, tail, how = tk._parsed
idx = sem_index()

# The TechTree section is the last of the seven tail i32s before the civs block,
# per the authoritative offset table: TechTree sits AFTER civs/techs in the file,
# and `read_tech_tree` is called last.  Walk it the documented way: 5 counts then
# the connections.
import aoe2mod.dat.parser as P                              # noqa: E402

# Re-derive the TechTree offset exactly as the parser does.
r = P.Reader(data, gv=gv)
r.pos = civs_start
n_civ = r.i16()
for _ in range(n_civ):
    r.debug_string()
    r.i16()                     # TechTreeID
    # Resources array width equals the largest resource id seen + 1 (parser logic);
    # reuse the parser's own Civ reader instead of guessing.
    raise SystemExit("use the parser accessor below")

