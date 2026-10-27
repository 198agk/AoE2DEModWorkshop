# -*- coding: utf-8 -*-
"""Compare the Rust stage-1 reader against the Python original, number by number.

Why not just "it printed 145742, looks right"
---------------------------------------------
Because 145742 is one number, and a parser can reach the right offset with every
field inside wrong: two errors that cancel are the standard way this project has
been fooled (a version guard read unconditionally over-ran by 1,465,059 bytes
while the *first* stage still landed exactly).

So this compares the whole stage-1 record: counts, the pointer arrays, every
terrain restriction's multiplier table and pass table, and all 16 colour rows.

Usage:  py -X utf8 _probe/compare_rust_stage1.py
Exit 0 = the two implementations agree on stage 1.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P          # noqa: E402

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
RUST_EXE = os.path.join(ROOT, "desktop", "aoe2mod-dat", "target", "release",
                        "aoe2mod-dat.exe")


def py_stage1():
    raw, _how = P.load_dat(DAT)
    q = P.Parser(raw)
    q.parse(stop_after=1)
    s = q.stats
    return {
        "end_pos": q.r.pos,
        "file_version": s["file_version"].rstrip("\x00"),
        "game_version": s["game_version"],
        "terrain_restriction_count": s["terrain_restriction_count"],
        "terrains_used1": s["terrains_used1"],
        "float_ptr": list(s["float_ptr_terrain_tables"]),
        "pass_ptr": list(s["terrain_pass_graphic_pointers"]),
        "restrictions": [
            {"mult": [round(float(x), 6) for x in r["mult"]],
             "pass": [[int(a), int(b), int(c), round(float(f), 6)]
                      for (a, b, c, f) in r["pass"]]}
            for r in s["terrain_restrictions"]
        ],
        "player_colour_count": s["player_colour_count"],
        "player_colours": [list(c) for c in s["player_colours"]],
    }


def rust_stage1():
    """Ask the Rust binary for a JSON dump; it writes one when given --json."""
    if not os.path.isfile(RUST_EXE):
        raise SystemExit("REFUSING: build the crate first (%s missing)" % RUST_EXE)
    r = subprocess.run([RUST_EXE, DAT, "--json"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode != 0:
        raise SystemExit("rust reader failed: %s" % (r.stderr or r.stdout))
    return json.loads(r.stdout)


def main():
    a = py_stage1()
    b = rust_stage1()
    bad = []

    def eq(name, x, y):
        ok = x == y
        if not ok:
            bad.append(name)
        print("%-30s %s" % (name, "ok" if ok else "FAIL"))
        if not ok:
            xs, ys = repr(x), repr(y)
            print("    py   : %s" % (xs[:160] + ("..." if len(xs) > 160 else "")))
            print("    rust : %s" % (ys[:160] + ("..." if len(ys) > 160 else "")))

    eq("end position", a["end_pos"], b["end_pos"])
    eq("file version", a["file_version"], b["file_version"])
    eq("game version", a["game_version"], b["game_version"])
    eq("terrain_restriction_count", a["terrain_restriction_count"],
       b["terrain_restriction_count"])
    eq("terrains_used1", a["terrains_used1"], b["terrains_used1"])
    eq("float pointer array", a["float_ptr"], b["float_ptr"])
    eq("pass pointer array", a["pass_ptr"], b["pass_ptr"])
    eq("player_colour_count", a["player_colour_count"], b["player_colour_count"])
    eq("player colours", a["player_colours"], b["player_colours"])
    eq("terrain restrictions (all)", a["restrictions"], b["restrictions"])

    print()
    if bad:
        print("STAGE 1: %d FIELD(S) DIFFER -> %s" % (len(bad), bad))
        return 1
    print("STAGE 1: Python and Rust agree on every field (%d restrictions, %d colours)"
          % (a["terrain_restriction_count"], a["player_colour_count"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
