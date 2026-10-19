# -*- coding: utf-8 -*-
"""Read what v17 actually hung its disable on, and what enables unit 2550.

Read-only.  Two things are being checked before any product code claims them:

  * which technologies carry the global "make 2550 available" command, and what
    each of them requires -- the ordering rule says the LAST one to fire wins;
  * the exact identity of the two carriers `dsh test v17` used (tech 495 and
    tech 508), because a docstring that names them must be quoting measurement
    rather than memory.

Section D prints the age rank of every technology the Incas own and can fire
without research, which is the candidate set `pick_revoke_tech` will draw from.
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
    dat = G.dat_path(GAME)
    raw, how = P.load_dat(dat)
    print("dat %s (%s)" % (len(raw), how))
    pr = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        pr.parse()
    civs, _cs, gv, tail = L.locate(raw, parser=pr)
    techs = L.locate_techs(raw, tail, gv)
    print("techs: %d" % len(techs))

    incas = next(i for i, c in enumerate(civs)
                 if "inca" in (c.get("name") or "").lower())
    print("\nIncas = civ index %d (%r)" % (incas, civs[incas].get("name")))

    print("\nA. every technology whose effect enables unit %d" % UNIT)
    for i, cmd in DG.enabling_techs(pr.stats, UNIT):
        t = techs[i]
        print("   tech %-5d %-34r civ=%-3s req=%-12s loc=%s   cmd=%s"
              % (i, t.get("name"), t.get("civ"), t.get("required_techs"),
                 bool(t.get("research_locations")), tuple(cmd)))

    print("\nB. the two technologies v17 patched")
    for i in (495, 508):
        t = techs[i]
        print("   tech %-5d %-34r civ=%-3s req=%-12s loc=%-5s eff=%s"
              % (i, t.get("name"), t.get("civ"), t.get("required_techs"),
                 bool(t.get("research_locations")), t.get("effect_id")))

    print("\nC. age ranks as the product computes them")
    ranks = DG._age_ranks(techs)
    for i in (104, 101, 102, 103, 1350, 495, 508):
        print("   tech %-5d rank=%d (%s)  req=%s"
              % (i, ranks.get(i, 0),
                 DG._AGE_NAMES.get(ranks.get(i, 0), "?"),
                 techs[i].get("required_techs")))

    print("\nD. what pick_revoke_tech answers for the Incas right now")
    en = DG.enabling_techs(pr.stats, UNIT)
    floor_tech = max(en, key=lambda it: ranks.get(it[0], 0))[0] if en else None
    print("   floor tech = %r (rank %s)"
          % (floor_tech, ranks.get(floor_tech, 0)))
    i, t, why = DG.pick_revoke_tech(techs, incas, enable_tech_index=floor_tech)
    if i is None:
        print("   REFUSED: %s" % why)
    else:
        print("   picks tech %d %r  rank=%s (%s)  req=%s"
              % (i, t.get("name"), ranks.get(i, 0), why, t.get("required_techs")))

    print("\nE. every Incas-owned tech that fires without research, by rank")
    for j, tt in enumerate(techs):
        if tt.get("civ") != incas or DG._researched_in_building(tt):
            continue
        print("   tech %-5d rank=%d %-34r req=%s"
              % (j, ranks.get(j, 0), tt.get("name"), tt.get("required_techs")))

    print("\nF. pick_tech (the GRANT anchor) -- with the shipped predicate and with")
    print("   the corrected one, because the two can choose different anchors")
    print("   and the shipped choice is the one confirmed in game (dsh test v7).")
    i, t, why = DG.pick_tech(techs, incas)
    print("   shipped predicate -> tech %s %r  %s"
          % (i, (t or {}).get("name"), why))

    _real = DG._researched_in_building
    DG._researched_in_building = lambda tech: bool(tech.get("research_locations"))
    try:
        j2, t2, why2 = DG.pick_tech(techs, incas)
    finally:
        DG._researched_in_building = _real
    print("   old truthiness   -> tech %s %r  %s"
          % (j2, (t2 or {}).get("name"), why2))
    print("   => %s" % ("SAME anchor, the predicate does not change the grant"
                        if i == j2 else
                        "DIFFERENT anchor -- fixing it would move a recipe that "
                        "was confirmed in game"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
