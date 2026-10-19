# -*- coding: utf-8 -*-
"""Why did `pick_revoke_tech` find no carrier for the Incas when v17 used tech 508?

Read-only.  Prints the civilization's own free technologies, their age rank, and
what `_researched_in_building` says about each -- so the filter that dropped the
one carrier known to work can be named instead of guessed at.
"""
import contextlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L          # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.game import locations as G      # noqa: E402
from aoe2mod.intent import datgrant as DG    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550


def main():
    raw, _how = P.load_dat(G.dat_path(GAME))
    pr = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        pr.parse()
    civs, _cs, gv, tail = L.locate(raw, parser=pr)
    techs = L.locate_techs(raw, tail, gv)
    civ = next(i for i, c in enumerate(civs)
               if "inca" in (c.get("name") or "").lower())
    print("civ index %d  techs %d  effects %d"
          % (civ, len(techs), len(pr.stats["effects"])))

    ranks = DG._age_ranks(techs)
    own = [(i, t) for i, t in enumerate(techs) if t.get("civ") == civ]
    print("owned techs: %d" % len(own))
    print("\n  idx  rank  inBldg  req                 name")
    for i, t in own:
        req = t.get("required_techs")
        r = ranks.get(i, 0)
        print("  %4d  %4d  %-6s  %-18s  %s"
              % (i, r, DG._researched_in_building(t),
                 req if req is not None else "?", t.get("name")))

    print("\ntech 508 raw record:")
    t = techs[508]
    for k in ("civ", "name", "effect_id", "type", "required_techs",
              "research_locations", "research_resource_costs"):
        print("   %-24s %r" % (k, t.get(k)))

    print("\nenablers of %d: %s" % (UNIT, DG.enabling_techs(pr.stats, UNIT)))
    print("age ranks of the age techs: %r" % {k: ranks.get(k) for k in
                                              (104, 101, 102, 103)})
    print("\nREVOKE CANDIDATES: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
