# -*- coding: utf-8 -*-
r"""Which tech does the engine actually research at game start?

v6 proved the Castle gate is not `EnablingResearch` (that was set to -1 and the
button still waited for a Castle): it is the **effect attachment**.  v5 attached
`effect 1500 = [(2, 8, 1, -1, 0.0), (2, 2550, 1, -1, 0.0)]` to `tech 263`,
`Longbow (make avail)` -- and the engine researches that tech when a Castle goes
up, so the unit appeared exactly then.

For a Dark Age unit the enable command must ride a tech the engine researches at
GAME START for the target civilization.  The game ships such techs: a civ bonus is
a `tech` with `civ == <civ index>`, no research location, and an effect that
modifies resources.  This probe finds them, so v7 can copy the real mechanism
instead of guessing a different global "make avail" tech.

Reports, for British (and Incas as the control):

  * every tech whose `civ` is that civ, with name / effect / commands / locations
  * which of those have NO research location (=> researched at game start)
  * the commands of effect 1350 and 1500 for comparison
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod.dat import parser as P                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

WANT = {"British": 1, "Incas": 21}


def main():
    data, how = P.load_dat(SHIPPED)
    p = P.Parser(data)
    p.parse()
    techs = p.stats["techs"]
    effects = p.stats["effects"]

    def cmds(ef_id):
        """Effect commands, normalised to dicts.

        `p.stats["effects"]` stores each command as a TUPLE (type, a, b, c, d),
        while `locate.locate_effects` yields dicts and `L.locate_effects` yields
        dicts too.  Normalising here keeps this probe readable either way.
        """
        if not isinstance(ef_id, int) or ef_id < 0 or ef_id >= len(effects):
            return []
        out = []
        for c in effects[ef_id]["commands"]:
            if isinstance(c, dict):
                out.append(c)
            else:
                out.append({"type": c[0], "a": c[1], "b": c[2],
                            "c": c[3], "d": c[4]})
        return out

    for civ_name, ci in WANT.items():
        print("=" * 74)
        print("civ %d = %s" % (ci, civ_name))
        print("=" * 74)
        owned = [(ti, t) for ti, t in enumerate(techs) if t.get("civ") == ci]
        print("techs owned by this civ: %d" % len(owned))
        free = []
        for ti, t in owned:
            locs = t.get("research_locations") or []
            eff = t.get("effect_id")
            cs = cmds(eff)
            kinds = sorted({c.get("type") for c in cs})
            is_free = (not locs) or all(
                (l[0] if isinstance(l, (tuple, list)) else -1) == -1 for l in locs)
            tag = "FREE@START" if is_free else "research"
            print("  tech %-5d %-34s eff=%-5s locs=%-28s types=%s  %s"
                  % (ti, repr(t.get("name"))[:34], eff, str(locs)[:28], kinds, tag))
            if is_free:
                free.append((ti, t, eff, cs))
        print()
        print("  => %d techs with no research location (candidates for a "
              "game-start anchor):" % len(free))
        for ti, t, eff, cs in free:
            print("     tech %-5d %r" % (ti, t.get("name")))
            for c in cs:
                print("        %s" % {k: v for k, v in c.items()
                                      if not k.startswith("_")})
        print()

    print("=" * 74)
    print("reference effects")
    print("=" * 74)
    for eid in (1350, 1500, 251):
        print("  effect %d used by techs %s: %s"
              % (eid, [i for i, t in enumerate(techs) if t.get("effect_id") == eid],
                 [tuple(c) for c in cmds(eid)][:6]))
    print()
    print("  tech 263 name=%r civ=%s" % (techs[263].get("name"),
                                         techs[263].get("civ")))
    print("  tech 1350 name=%r civ=%s locs=%s"
          % (techs[1350].get("name"), techs[1350].get("civ"),
             techs[1350].get("research_locations")))
    print()
    print("  how many civs' techs mention unit 2550 in a type-2 command?")
    n = 0
    for ti, t in enumerate(techs):
        for c in cmds(t.get("effect_id")):
            if c.get("type") == 2 and c.get("a") == 2550:
                print("     tech %-5d civ=%-4s %r  b=%s" % (ti, t.get("civ"),
                                                            t.get("name"),
                                                            c.get("b")))
                n += 1
    print("     total %d" % n)


if __name__ == "__main__":
    main()
