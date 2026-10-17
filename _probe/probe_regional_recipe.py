# -*- coding: utf-8 -*-
r"""How does a Dark-Age REGIONAL unit get enabled?  The Eagle Scout is the model.

Unit 2550 (Champi Scout) is available to 4 civs from the Dark Age.  Its shipped
`EnablingResearch` is tech 1350 `Champi Scout (Make avail)`, whose research
location is `(12, 0, 6, 18230)` -- building 12 (Barracks), cost 0, time 0.  That
is the recipe: a ZERO-COST BARRACKS TECH THE ENGINE APPLIES AUTOMATICALLY.

The Eagle Scout (751/752/753) is the same shape and has been in the game for 25
years, so it is the safest model to copy.  This probe prints, for each of:

    751 Eagle Scout      (Mesopotamian/American regional unit, Dark Age)
    2550 Champi Scout    (South-American regional unit, Dark Age)
    8   Longbowman       (British UNIQUE unit, Castle)

  * the `EnablingResearch` / `RequiredResearch` from the dat's TechTree
    `UnitConnection` array
  * the enabling tech's name, civ, research locations, and effect commands
  * whether that tech appears in the trees at all (it should NOT: the gate is the
    dat-side connection, not a tree node)

so v7 can point the British at the SAME kind of anchor instead of tech 263.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
V6 = os.path.join(HERE, "out_dshtest_v6", "resources", "_common", "dat",
                  "empires2_x2_p1.dat")
WANT = (751, 752, 753, 2550, 2552, 2554, 2588, 8, 41, 5)


def connections(data, gv):
    """`{unit_id: {...}}` from the TechTree UnitConnection array."""
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            # ★ `stop_after=9` on purpose: `stage_offsets[-1]` must be the TECHS
            # stage.  After a full parse it is the Tail+TechTree stage, and
            # `+7*4` then lands 28 bytes PAST the end of the file
            # (`EOFError: read of 1 byte(s) at offset 93268180`).
            p.parse(stop_after=9)
        except SystemExit:
            pass
    r = P.Reader(data, gv=gv)
    r.pos = p.stage_offsets[-1][2] + 7 * 4
    n_ages, n_bldg = r.u8(), r.u8()
    n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
    n_res = r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(n_ages):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(n_bldg):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    conn = {}
    for _ in range(n_units):
        uid = r.i32()
        status = r.u8()
        ub = r.i32()
        lia = r.i32()
        r.i32_array(10); r.i32_array(10)
        rr = r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32()
        lm = r.i32()
        r.i32()
        en = r.i32()
        conn[uid] = {"status": status, "upper_building": ub,
                     "location_in_age": lia, "required_research": rr,
                     "line_mode": lm, "enabling_research": en}
    return conn, p


def main():
    data, _how = P.load_dat(SHIPPED)
    with contextlib.redirect_stdout(io.StringIO()):
        probe = P.Parser(data)
        probe.parse()
    gv = probe.r.gv
    conn, p = connections(data, gv)
    techs = p.stats["techs"]
    effects = p.stats["effects"]

    def cmds(ef):
        if not isinstance(ef, int) or ef < 0 or ef >= len(effects):
            return []
        out = []
        for c in effects[ef]["commands"]:
            out.append(c if isinstance(c, dict) else
                       {"type": c[0], "a": c[1], "b": c[2], "c": c[3], "d": c[4]})
        return out

    v6data, _h2 = P.load_dat(V6)
    with contextlib.redirect_stdout(io.StringIO()):
        p6 = P.Parser(v6data)
        p6.parse()
    conn6, _p6 = connections(v6data, gv)

    print("=" * 78)
    print("SHIPPED TechTree UnitConnection")
    print("=" * 78)
    for uid in WANT:
        c = conn.get(uid)
        if c is None:
            print("  unit %-5d  (no connection)" % uid)
            continue
        en, rr = c["enabling_research"], c["required_research"]
        print("  unit %-5d EnablingResearch=%-6s RequiredResearch=%-6s "
              "UpperBuilding=%-5s LocationInAge=%-3s Status=%s"
              % (uid, en, rr, c["upper_building"], c["location_in_age"],
                 c["status"]))
        for lbl, tid in (("enabling", en), ("required", rr)):
            if not isinstance(tid, int) or tid < 0 or tid >= len(techs):
                continue
            t = techs[tid]
            print("        %-9s tech %-5d %-30r civ=%-4s locs=%s"
                  % (lbl, tid, t.get("name"), t.get("civ"),
                     t.get("research_locations")))
            for cc in cmds(t.get("effect_id")):
                if cc.get("type") == 2 and cc.get("a") in WANT:
                    print("             -> enable cmd %s" % cc)

    print()
    print("=" * 78)
    print("V6 TechTree UnitConnection (2550 only)")
    print("=" * 78)
    c = conn6.get(2550)
    print("  unit 2550 v6: %s" % c)
    print("  tech 263 v6 effect commands:")
    for cc in cmds(techs[263].get("effect_id")):
        print("        %s" % cc)

    print()
    print("=" * 78)
    print("every tech whose effect carries a type-2 ENABLE for 2550")
    print("=" * 78)
    for ti, t in enumerate(techs):
        for cc in cmds(t.get("effect_id")):
            if cc.get("type") == 2 and cc.get("a") == 2550:
                print("  tech %-5d %-32r civ=%-4s locs=%-24s b=%s"
                      % (ti, t.get("name"), t.get("civ"),
                         str(t.get("research_locations"))[:24], cc.get("b")))

    print()
    print("=" * 78)
    print("British game-start techs (civ=1, no research location)")
    print("=" * 78)
    for ti, t in enumerate(techs):
        if t.get("civ") != 1:
            continue
        locs = t.get("research_locations") or []
        flat = [l if isinstance(l, (list, tuple)) else () for l in locs]
        free = (not locs) or all((x[0] if x else -1) == -1 for x in flat)
        if not free:
            continue
        types = sorted({c.get("type") for c in cmds(t.get("effect_id"))})
        print("  tech %-5d %-34r eff=%-5s types=%s"
              % (ti, t.get("name"), t.get("effect_id"), types))


if __name__ == "__main__":
    main()
