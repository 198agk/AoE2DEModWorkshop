# -*- coding: utf-8 -*-
"""Export only what an editor needs: for each civ, `id -> absolute byte offset`
for each stat.  The first version wrote every offset of every record (38 MB)
which is 63x more than any edit needs and makes the file unreadable as data.

Absolute offsets (not record-relative) because `locate` measured them that way
and re-basing them here would be one more place to get an off-by-one wrong.
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

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "stat_offsets.json")

WANT = {
    "hit_points": "i16", "garrison_capacity": "u8", "sort_number": "u8",
    "line_of_sight": "f32", "movement_speed": "f32", "creation_time": "i16",
    "displayed_attack": "i16", "displayed_melee_armour": "i16",
    "displayed_pierce_armour": "i16", "displayed_range": "f32",
    "displayed_reload_time": "f32", "max_range": "f32", "min_range": "f32",
    "reload_time": "f32", "accuracy": "i16",
}

raw, _ = P.load_dat(DAT)
p = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs, _civs_start, gv, _tail = L.locate(raw, parser=p)

out = {"gv": gv, "types": WANT, "civs": []}
for c in civs:
    per_stat = {k: {} for k in WANT}
    for u in c["units"]:
        offs = u.get("_offs") or u.get("offsets") or {}
        for k in WANT:
            if k in offs:
                per_stat[k][str(u["id"])] = offs[k]
    # Gaia and British are what the tests use; keep every civ anyway so an
    # edit for any civ has an answer.
    out["civs"].append({"name": c["name"],
                        "count": len(c["units"]),
                        "stat_offsets": per_stat})

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(out, fh, separators=(",", ":"))

print("wrote %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1048576.0))
gaia = out["civs"][0]
print("civ0:", gaia["name"], "units", gaia["count"])
hp = gaia["stat_offsets"]["hit_points"]
print("hp entries:", len(hp), "| unit 83 offset:", hp.get("83"))
for k in sorted(WANT):
    print("  %-24s %d entries" % (k, len(gaia["stat_offsets"][k])))
