# -*- coding: utf-8 -*-
r"""v7 target check: what exactly does British tech 383 do, and can we hijack it?

## Why tech 383

`RequiredTechs` on a civ-owned, location-less tech IS the age gate.  Measured
functionally (the effects are the real in-game Britons bonuses):

    tech 381 'C-Bonus, 1/2 TCs'          [102]        TCs half price from CASTLE  ok
    tech 382 'C-Bonus, +1 Archer range'  [102]        archers +1 range in CASTLE   ok
    tech 383 'C-Bonus, +25% Shepherd'    []           shepherds faster FROM 0:00   ok
    tech 403 'C-Bonus, archer range +1'  [103]        +1 more at IMPERIAL          ok
    tech 263 'Longbow (make avail)'      [102, 266]   Longbowman at CASTLE         ok
    tech 1350 'Champi Scout (Make avail)' [104]       what actually works          ok

So `[]` means "satisfied before the game starts" and tech 383 is the only British
anchor that fires at 0:00 -- which is what v7 needs, because v5/v6 hung the enable
on tech 263 (+Castle) and the button therefore waited for a Castle.

This probe prints the command list we must PRESERVE when we repoint tech 383 at a
new effect, plus the field offsets v7 has to patch.
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
from aoe2mod.dat import locate as L                           # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
WANT_TECH = (263, 381, 382, 383, 403, 1350)
UNIT = 2550


def cmds(eff):
    out = []
    for c in (eff.get("commands") or []):
        if isinstance(c, dict):
            out.append((c["type"], c["a"], c["b"], c["c"], c["d"]))
        else:
            out.append(tuple(c))
    return out


def main():
    raw, how = P.load_dat(DAT)
    print("loaded %d bytes, how=%s" % (len(raw), how))
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    st = pr.stats
    techs, effects = st["techs"], st["effects"]
    print("techs %d  effects %d" % (len(techs), len(effects)))
    print()

    print("=" * 78)
    print("1  the effects we would have to PRESERVE")
    print("=" * 78)
    for t in WANT_TECH:
        rec = techs[t]
        eid = rec.get("effect_id")
        cs = cmds(effects[eid]) if 0 <= eid < len(effects) else []
        print("  tech %-5d %-32s civ=%-4s effect %-5d  %d commands"
              % (t, (rec.get("name") or "")[:32], rec.get("civ"), eid, len(cs)))
        for c in cs:
            print("        %s" % (c,))
    print()

    print("=" * 78)
    print("2  who else points at those effects (must not disturb them)")
    print("=" * 78)
    by_eff = {}
    for i, rec in enumerate(techs):
        by_eff.setdefault(rec.get("effect_id"), []).append(i)
    for t in WANT_TECH:
        eid = techs[t].get("effect_id")
        others = [j for j in by_eff.get(eid, []) if j != t]
        print("  effect %-5s referenced by %d techs %s"
              % (eid, len(others), others[:10]))
    print()

    print("=" * 78)
    print("3  the British 2550 record: button byte, civ field, EnablingResearch")
    print("=" * 78)
    civs, _cs, gv, _tail = L.locate(raw, parser=pr)
    brit = next(c for c in civs if c["name"] == "British")
    incas = next(c for c in civs if c["name"] == "Incas")
    for civ in (brit, incas):
        u = next((x for x in civ["units"] if x["id"] == UNIT), None)
        if u is None:
            print("  %-8s has NO record for %d" % (civ["name"], UNIT))
            continue
        tl = u["train_locations"][0]
        off = tl["_off_train_time"]
        print("  %-8s record for %d: train_locations=%s"
              % (civ["name"], UNIT, u["train_locations"]))
        print("           button byte at offset %d = %d"
              % (off + 4, raw[off + 4]))
    print()

    print("=" * 78)
    print("4  v5 output payload (the JSON halves we reuse)")
    print("=" * 78)
    v5 = os.path.join(HERE, "out_dshtest_v5")
    for root, _d, fs in os.walk(v5):
        for f in sorted(fs):
            fp = os.path.join(root, f)
            print("  %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, v5)))
    print()

    print("=" * 78)
    print("5  does the SHIPPED dat already have an effect 1500?")
    print("=" * 78)
    print("  len(effects) = %d ; effects[1500] = %s"
          % (len(effects), (effects[1500].get("name") if len(effects) > 1500
                            else "ABSENT")))
    print("  tech 383 (British, RequiredTechs=[]) command count: %d"
          % len(cmds(effects[techs[383]["effect_id"]])))
    print()
    print("PROBE OK")


if __name__ == "__main__":
    main()
