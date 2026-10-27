# -*- coding: utf-8 -*-
"""Compare Rust stage 1 against Python, printing only the verdict lines."""
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
EXE = os.path.join(ROOT, "desktop", "aoe2mod-dat", "target", "release",
                   "aoe2mod-dat.exe")
OUT = os.path.join(HERE, "_stage1_compare.txt")


def main():
    lines = []
    raw, _ = P.load_dat(DAT)
    q = P.Parser(raw)
    # `parse(stop_after=1)` CALLS sys.exit() when it reaches the boundary rather
    # than returning, so the comparison has to survive SystemExit or it never
    # prints anything.  (First run of this file died exactly there.)
    try:
        q.parse(stop_after=1)
    except SystemExit:
        pass
    s = q.stats
    py = {
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

    r = subprocess.run([EXE, DAT, "--json"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    if r.returncode != 0:
        lines.append("RUST FAILED: " + (r.stderr or "")[:300])
    else:
        rs = json.loads(r.stdout)
        bad = []
        for k in ("end_pos", "file_version", "game_version",
                  "terrain_restriction_count", "terrains_used1",
                  "player_colour_count"):
            if py[k] != rs[k]:
                bad.append("%s py=%r rust=%r" % (k, py[k], rs[k]))
        for k in ("float_ptr", "pass_ptr", "player_colours", "restrictions"):
            if py[k] != rs[k]:
                bad.append("%s differs" % k)
        if bad:
            lines.append("STAGE1 FAIL %d" % len(bad))
            lines.extend("  " + b for b in bad)
        else:
            lines.append("STAGE1 AGREE pos=%d restr=%d colours=%d"
                         % (py["end_pos"], py["terrain_restriction_count"],
                            py["player_colour_count"]))
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    for ln in lines:
        print(ln)
    return 0 if "AGREE" in " ".join(lines) else 1


if __name__ == "__main__":
    sys.exit(main())
