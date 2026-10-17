# -*- coding: utf-8 -*-
r"""Which tech actually turns unit 2550 on for the Incas, and why does copying
their row wholesale not reproduce it for the British?

v5/v6 wrote, for the British, a CivTechTrees row that is BYTE-FOR-BYTE the Incas
row (`Age ID 1`, `Building ID 12`, `Node Status ResearchedCompleted`,
`Trigger Tech ID 1350`), plus the panel entry, plus a `.dat` unit record that
already matched.  The button still waited for a Castle.

So the difference is NOT in the tree row and NOT in the unit record.  That
leaves the tech layer.  This probe asks the one static question that can separate
the candidates:

    does the civ's tech tree FILE carry a row for tech 1350 itself?

`CivTechTrees/<CIV>.json` holds `civ_techs_units` + `civ_techs_buildings`, and
the rows are `Use Type: Unit | Tech | Building`.  A `Use Type: Tech` row with
`Node ID: N` is a TECH entry (Node ID is the .dat tech index).  If the Meso civs
list 1350 and the British do not, then "make the unit available" is not one
recipe but two layers: the enable effect AND the tree's own tech row.

It also enumerates every type-2 (Enable/Disable Unit) command in the .dat and
where its tech is applied, so the anchor question ("what fires at game start")
is answered from data rather than from reasoning.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import aoe2mod.dat.parser as P                                # noqa: E402
from aoe2mod.game import civtechtrees as CT                   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")


def load_dat():
    raw, _how = P.load_dat(DAT)
    # A FULL parse: this probe reads techs and effects, which both sit AFTER the
    # TechTree stage.  `stop_after=9` (the trick that keeps stage_offsets[-1] from
    # overshooting) would leave the two tables this probe exists to read empty,
    # and an empty table prints exactly like "no such command exists".
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    return raw, pr


def main():
    print("=" * 78)
    print("1. Is tech 1350 itself a node in the civ trees?")
    print("=" * 78)
    trees = CT.load_trees(GAME)
    print("trees loaded: %d" % len(trees))
    hits = []
    for civ in sorted(trees):
        for use_type, key in (("Tech", CT.UNITS_KEY), ("Tech", CT.BUILDINGS_KEY)):
            for r in trees[civ].get(key) or []:
                if not isinstance(r, dict):
                    continue
                if r.get("Use Type") == "Tech" and r.get("Node ID") == 1350:
                    hits.append((civ, key, r.get("Node Status")))
    print("rows for tech 1350 across all trees: %d" % len(hits))
    for h in hits[:10]:
        print("   %s" % (h,))

    print()
    print("2. Which civs have a 2550 unit row, and what does it say?")
    for civ in ("INCAS", "MAYANS", "AZTECS", "MUISCA", "BRITONS"):
        t = trees.get(civ)
        if t is None:
            print("   %-10s <- no tree file" % civ)
            continue
        rows = [r for r in (t.get(CT.UNITS_KEY) or [])
                if isinstance(r, dict) and r.get("Node ID") == 2550]
        for r in rows:
            print("   %-10s status=%-18s age=%s bldg=%s trigger=%s"
                  % (civ, r.get("Node Status"), r.get("Age ID"),
                     r.get("Building ID"), r.get("Trigger Tech ID")))
        if not rows:
            print("   %-10s <- no 2550 row" % civ)

    print()
    print("3. Every type-2 (Enable/Disable Unit) command in the .dat")
    print("=" * 78)
    raw, pr = load_dat()
    stats = pr.stats
    techs = stats["techs"]
    effects = stats["effects"]

    def cmds(eff_id):
        if not (0 <= eff_id < len(effects)):
            return []
        out = []
        for c in effects[eff_id].get("commands") or []:
            if isinstance(c, dict):
                out.append(c)
            else:
                out.append({"type": c[0], "a": c[1], "b": c[2],
                            "c": c[3], "d": c[4]})
        return out

    found = []
    for i, t in enumerate(techs):
        if not isinstance(t, dict):
            continue
        eid = t.get("effect_id")
        for c in cmds(eid):
            if c["type"] != 2:
                continue
            found.append((i, t.get("name"), t.get("civ"),
                          c["a"], c["b"], t.get("research_locations")))
    print("type-2 commands total: %d" % len(found))
    print()
    print("  -- the ones that ENABLE unit 2550 (b != 0):")
    for f in found:
        if f[3] == 2550 and f[4] != 0:
            print("     tech %-5d %-32s civ=%-4s unit=%s b=%s locs=%s" % f)
    print()
    print("  -- every type-2 command whose tech has NO research location")
    print("     (those are the candidates for 'applied without being researched'):")
    n = 0
    for f in found:
        locs = f[5] or []
        if all((isinstance(l, dict) and l.get("building") in (None, -1))
               or (not isinstance(l, dict) and l[0] == -1) for l in locs) and locs:
            n += 1
            if n <= 25:
                print("     tech %-5d %-32s civ=%-4s unit=%-5s b=%s locs=%s"
                      % (f[0], (f[1] or "")[:32], f[2], f[3], f[4], f[5]))
    print("     ... total with no location: %d" % n)


if __name__ == "__main__":
    main()
