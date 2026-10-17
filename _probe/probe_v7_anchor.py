# -*- coding: utf-8 -*-
r"""Pick the anchor that makes unit 2550 appear for the British WITHOUT a Castle.

What we know (all measured):

  * shipped Incas get the Champi Scout in the Dark Age;
  * their `CivTechTrees/INCAS.json` row for 2550 says
    `Age ID 1 / Building ID 12 / Node Status ResearchedCompleted /
     Trigger Tech ID 1350`;
  * v5/v6 wrote a BYTE-IDENTICAL row for BRITONS (same Trigger Tech ID 1350)
    plus the panel entry plus the unit record -- and the button still waited for
    a Castle, because v5/v6 hung the `type 2` enable command on
    `tech 263 'Longbow (make avail)'`, which the engine researches WHEN A CASTLE
    IS BUILT.

So the row was never the gate; the TECH carrying the enable command was.  The
gate is "when is that tech applied".

`tech 1350` itself has `research_locations = [(12, 0, 6, 18230)]` -- building 12
(Barracks), cost 0, time 0 -- i.e. it is researched at the Barracks.  The other
shape, used by 182 type-2 commands, is `research_locations = [(-1, 0, 0, -1)]`:
NO location, which is the "make avail" pattern that every civ gets from the
first frame (`tech 151 Archer (make avail)`, `tech 87 Spearman (make avail)`).

This probe lists, for the British (`civ == 1`), every tech that
  (a) is civ-owned by the British, and
  (b) has NO research location,
and for each one reports its effect and whether that effect is shared with any
other tech.  A civ-owned, location-less tech with an effect nobody else uses is a
free anchor: appending one command to it enables the unit from the start.
"""
import contextlib
import io
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import aoe2mod.dat.parser as P                                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
UNIT = 2550
BRITISH = 1


def load(path):
    raw, _how = P.load_dat(path)
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    return raw, pr.stats


def cmds_of(effects, eff_id):
    if not (0 <= eff_id < len(effects)):
        return []
    out = []
    for c in effects[eff_id].get("commands") or []:
        if isinstance(c, dict):
            out.append(c)
        else:
            out.append({"type": c[0], "a": c[1], "b": c[2], "c": c[3], "d": c[4]})
    return out


def locs_of(t):
    locs = t.get("research_locations")
    if not locs:
        return []
    out = []
    for l in locs:
        if isinstance(l, dict):
            out.append(l.get("location_id", l.get("building", None)))
        else:
            out.append(l[0] if isinstance(l, (list, tuple)) else l)
    return out


def is_locationless(t):
    l = locs_of(t)
    return len(l) == 0 or all(x in (-1, None) for x in l)


def main():
    raw, st = load(DAT)
    techs = st["techs"]
    effects = st["effects"]
    print("techs=%d effects=%d" % (len(techs), len(effects)))

    # how many techs point at each effect?
    eff_users = Counter()
    for t in techs:
        if isinstance(t, dict):
            eff_users[t.get("effect_id")] += 1

    print()
    print("=" * 76)
    print("A. British-owned (civ==1) techs with NO research location")
    print("=" * 76)
    rows = []
    for i, t in enumerate(techs):
        if not isinstance(t, dict):
            continue
        if t.get("civ") != BRITISH:
            continue
        if not is_locationless(t):
            continue
        rows.append((i, t))
    print("count: %d" % len(rows))
    for i, t in rows:
        eid = t.get("effect_id")
        cs = cmds_of(effects, eid)
        types = sorted({c["type"] for c in cs})
        users = eff_users.get(eid, 0)
        print("  tech %-5d %-34s eff=%-5d users=%-3d cmds=%-2d types=%s"
              % (i, (t.get("name") or "")[:34], eid, users, len(cs), types))

    print()
    print("=" * 76)
    print("B. Is unit %d mentioned by any tech at all, and how?" % UNIT)
    print("=" * 76)
    for i, t in enumerate(techs):
        if not isinstance(t, dict):
            continue
        for c in cmds_of(effects, t.get("effect_id")):
            # type 2 is Enable/Disable Unit; type 3 is Upgrade Unit
            if c["type"] in (2, 3) and c["a"] == UNIT:
                print("  tech %-5d %-34s civ=%-4s eff=%-5s cmd=%s locs=%s"
                      % (i, (t.get("name") or "")[:34], t.get("civ"),
                         t.get("effect_id"), c, locs_of(t)))

    print()
    print("=" * 76)
    print("C. Which tech does the British tree row name as TRIGGER for 2550?")
    print("=" * 76)
    from aoe2mod.game import civtechtrees as CT
    trees = CT.load_trees(GAME)
    for stem in ("BRITONS", "INCAS"):
        t = trees.get(stem)
        if t is None:
            print("  %s: no tree" % stem)
            continue
        for r in (t.get(CT.UNITS_KEY) or []):
            if isinstance(r, dict) and r.get("Node ID") == UNIT:
                print("  %-8s trigger=%-6s status=%-18s age=%s bldg=%s"
                      % (stem, r.get("Trigger Tech ID"), r.get("Node Status"),
                         r.get("Age ID"), r.get("Building ID")))
                tr = r.get("Trigger Tech ID")
                if isinstance(tr, int) and 0 <= tr < len(techs):
                    tt = techs[tr]
                    print("           tech %d: name=%r civ=%s eff=%s locs=%s"
                          % (tr, tt.get("name"), tt.get("civ"),
                             tt.get("effect_id"), locs_of(tt)))
                    print("           effect cmds: %s" % cmds_of(effects, tt.get("effect_id")))

    print()
    print("=" * 76)
    print("D. Every civ-owned tech that enables a unit and has no location,")
    print("   i.e. the shape we would be copying")
    print("=" * 76)
    n = 0
    for i, t in enumerate(techs):
        if not isinstance(t, dict):
            continue
        cs = cmds_of(effects, t.get("effect_id"))
        en = [c for c in cs if c["type"] == 2 and c["b"] != 0]
        if not en:
            continue
        if not is_locationless(t):
            continue
        n += 1
        if n <= 30:
            print("  tech %-5d %-30s civ=%-4s enables=%s"
                  % (i, (t.get("name") or "")[:30], t.get("civ"),
                     [c["a"] for c in en]))
    print("  total: %d" % n)


if __name__ == "__main__":
    main()
