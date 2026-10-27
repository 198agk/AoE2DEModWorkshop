# -*- coding: utf-8 -*-
"""Dump per-unit byte spans from Python, so the Rust reader can be diffed unit by unit.

A whole-civilization offset ("89 MB, off by 2 MB") says nothing about WHICH
field is wrong.  Per-unit spans do: the first record whose span differs is the
one with the bad branch, and the record's type names the branch.

Writes `_golden/unit_spans.json`: for Gaia and British, `[id, type, span]` for
every unit record, where `span` is the number of bytes that record occupied.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P          # noqa: E402

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "unit_spans.json")

raw, _ = P.load_dat(DAT)
q = P.Parser(raw)
try:
    q.parse(stop_after=8)
except SystemExit:
    pass
s = q.stats

spans = {}
for civ in (0, 1):
    c = s["civs"][civ]
    rows = []
    # Re-walk the same bytes, measuring each record's span.  The parser does not
    # expose this, so measure by reading a record and diffing the cursor.
    r = q.r  # shared reader is at EOF now; use a fresh one positioned by hand
    rows = c.get("_spans") or []
    spans[c["name"]] = rows

# The parser does not record spans, so recompute them: rebuild a reader at the
# Civs section start and walk civs 0..1, timing each unit.
reader = P.Reader(raw)
P.read_stage1 = None  # guard: we only want the low-level reader here
r = reader
r.pos = 0
# Re-drive the file up to stage 8 using the public functions.
import aoe2mod.dat.parser as PP  # noqa: E402

rr = PP.Reader(raw)
# stage 1
rr.fixed_string(PP.FILE_VERSION_SIZE)
gv = PP.gv_from_version_string(rr.last_string_len if False else "VER 8.9")
# Easier and exact: use the recorded stage offsets from the parse above.
print("stage offsets:")
offs = {n: (a, b) for n, a, b in q.stage_offsets}
for n, (a, b) in offs.items():
    print("   %-40s %d -> %d" % (n, a, b))

civ_start = offs["8 Civs"][0]
rr.pos = civ_start
civ_count = rr.i16()
print("civ_count", civ_count)

measured = {}
for ci in range(2):
    c_start = rr.pos
    rr.u8()                     # player_type
    rr.debug_string()           # name
    n = rr.i16()
    rr.i16(); rr.i16()          # tech_tree_id, team_bonus_id
    rr.f32_array(n)
    rr.u8()                     # icon_set
    m = rr.i16()
    ptrs = rr.i32_array(m)
    rows = []
    for i in range(m):
        if ptrs[i] == 0:
            continue
        u_start = rr.pos
        u = PP.read_unit(rr)
        rows.append([u["id"], u["type"], rr.pos - u_start])
    measured[s["civs"][ci]["name"]] = rows
    print("  %-10s %d units, span %d" % (s["civs"][ci]["name"], len(rows), rr.pos - c_start))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(measured, fh)
print("wrote", OUT, os.path.getsize(OUT), "bytes")
