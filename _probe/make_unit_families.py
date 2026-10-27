# -*- coding: utf-8 -*-
"""Export the variant FAMILIES so the native engine can report edit widths.

Why this table exists at all
----------------------------
`村民血量改成100` is ONE sentence but 1,701 byte writes: 27 records x 63 civs.
The 27 are the villager's variant family -- the male and female baskets, joined
by `objreplacement.json`'s `chance 50` row, plus the age variants of the
buildings.  Without the family a preview would say "1 处改动" and the build
would touch 1,701, which is the class of lie this project keeps fixing.

Why the family is EXPORTED rather than recomputed in Rust
--------------------------------------------------------
`aoe2mod/dat/families.py` joins four independent mechanisms (effect type 3
replacement edges, task-swap groups, `linkedUnits.json`, `objreplacement.json`)
with restrictions that took measurements to get right -- the nonzero-display-name
condition, the Sea Gate counter-example, the villager pair that no name rule
could join.  A second implementation in Rust that agreed with it would prove
nothing; the value of this project's two-sided checks comes from the two sides
reaching the same answer by DIFFERENT routes.  So: Python measures, Rust reads
the measurement, and the check is that the numbers on screen match the numbers
`/api/build` actually writes.

Output shape
------------
    {"groups": {"83": [83, 118, ...], ...},   # only ids that have a family
     "task_swap_groups": {"83": 1, ...},      # only nonzero
     "counts": {"families": 26, "ids": 134}}

An id with no family is absent from `groups`, which the reader must treat as the
one-member family `[id]` -- not as "unknown".
"""
import io
import json
import os
import sys
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.locate as L          # noqa: E402
import aoe2mod.dat.parser as P          # noqa: E402
import aoe2mod.dat.families as F        # noqa: E402

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "unit_families.json")

raw, _ = P.load_dat(DAT)
p = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs, _start, gv, _tail = L.locate(raw, parser=p)

# BOTH edge sets have to be loaded before the families are built, and `warm` is
# the only thing that loads both.  Filling `_EDGE_CACHE["declared"]` by hand was
# the first attempt and it silently produced 6 families / 41 ids instead of
# 26 / 134: the age variants come from the effect type-3 edges, which only
# `warm` collects.  The count is the check -- a villager-only table would still
# have given the right 27 for this one sentence while every building edit
# under-reported.
F.warm(p.stats, GAME)
if F._EDGE_CACHE.get("declared_why"):
    sys.exit("cannot read %s: %s"
             % (F._EDGE_CACHE.get("declared_path"), F._EDGE_CACHE["declared_why"]))

fam = F.build_families(civs)

groups = {str(uid): members for uid, members in fam.items()}
groups = dict(sorted(groups.items(), key=lambda kv: int(kv[0])))

# Task-swap groups, kept separately because the preview names them when a family
# spans more than one basket ("these swap at runtime"), which is a different
# fact from "these are the same object".
groups_by_id = {}
for civ in civs:
    for u in civ.get("units") or ():
        uid = u.get("id")
        tsg = u.get("task_swap_group") or 0
        if uid is not None and tsg:
            groups_by_id[str(uid)] = tsg
groups_by_id = dict(sorted(groups_by_id.items(), key=lambda kv: int(kv[0])))

doc = {"gv": gv, "groups": groups, "task_swap_groups": groups_by_id,
       "counts": {"families": len({tuple(v) for v in groups.values()}),
                  "ids": len(groups)}}

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(doc, fh, separators=(",", ":"))

print("wrote %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
print("families %d / ids %d / task swap groups %d"
      % (doc["counts"]["families"], doc["counts"]["ids"], len(groups_by_id)))

# Verification, not decoration: the villager family is the one every example in
# this project uses, and its size x 63 is the number on screen.
vg = fam.get(83) or [83]
print("villager family: %d members, x 63 civs = %d edits" % (len(vg), len(vg) * 63))
print("  members:", vg)
