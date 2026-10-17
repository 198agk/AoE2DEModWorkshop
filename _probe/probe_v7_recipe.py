# -*- coding: utf-8 -*-
r"""The complete 2550 recipe, side by side: SHIPPED / v5 / v6.

Seven places can carry a piece of "the British may train a Champi Scout in the
Dark Age":

  1. the civ's UNIT RECORD for 2550 (train_locations[].button_id, costs, ...)
  2. the UNIT RECORD's per-civ copy existing at all (membership)
  3. the TechTree UnitConnection for 2550 (enabling_research / required_research /
     upper_building / location_in_age)
  4. the TECH that carries the `type 2` enable command (here: 1350) and its
     `research_locations` -- a location of `(-1,0,0,-1)` means "applied without
     being researched", which is how `tech 151 Archer (make avail)` gives every
     civ Archers in the Dark Age
  5. the effect cmds on that tech
  6. the CivTechTrees row (Node Status / Age ID / Building ID / Trigger Tech ID)
  7. the futuravailableunits panel entry

v5 changed 3, 6, 7 and (for the button) 1, but hung the enable command on tech
263 -- Castle-triggered.  v6 reverted 3 and lost 7.  This probe prints all seven
for both civs so v7 can be built from a diff rather than from a guess.
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
from aoe2mod.game import buildpanel as BP                     # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
UNIT = 2550
BUILDING = 12


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


def connections(raw, gv_, tree_start):
    """TechTree UnitConnection array, mirroring test_enabling_research.py.

    `tree_start` is the offset found from a FULL parse's own stage table
    (stage "10 Tail+TechTree").  The usual trick is `parse(stop_after=9)` and
    then taking `stage_offsets[-1][2]`, but that raises `SystemExit(0)` by
    design, so it cannot be called a second time inside a probe that already
    parsed the file once for its techs and effects.
    """
    r = P.Reader(raw, gv=gv_)
    r.pos = tree_start + 7 * 4
    na, nb = r.u8(), r.u8()
    nu = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(na):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(nb):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    out = {}
    for _ in range(nu):
        uid = r.i32(); status = r.u8()
        ub = r.i32(); lia = r.i32()
        r.i32_array(10); r.i32_array(10)
        req = r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        i32 = r.i32()
        lm = r.i32()
        r.i32()
        en = r.i32()
        out[uid] = {
            "status": status, "upper_building": ub, "location_in_age": lia,
            "required_research": req, "line_mode": lm,
            "enabling_research": en, "extra": i32,
        }
    return out


def dat_state(path_or_bytes, label):
    if isinstance(path_or_bytes, bytes):
        raw = path_or_bytes
    else:
        raw, _how = P.load_dat(path_or_bytes)
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    st = pr.stats
    print("--- %s ---" % label)
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    conn = connections(raw, pr.r.gv, stage[1])
    c = conn.get(UNIT)
    print(" 3. UnitConnection[%d] = %s" % (UNIT, c))
    for ti in (1350, 263, 151):
        t = st["techs"][ti] if ti < len(st["techs"]) else None
        if not isinstance(t, dict):
            print(" 4. tech %d -> missing" % ti)
            continue
        eid = t.get("effect_id")
        cs = cmds_of(st["effects"], eid)
        touch = [x for x in cs if x["type"] == 2 and x["a"] == UNIT]
        print(" 4. tech %-4d %-32s civ=%-4s eff=%-5s locs=%s"
              % (ti, (t.get("name") or "")[:32], t.get("civ"), eid,
                 t.get("research_locations")))
        print("      effect commands: %d | touching 2550: %s"
              % (len(cs), touch if touch else "none"))
    # unit record for British and Incas
    for ci, cname in ((1, "British"), (21, "Incas")):
        civ = st["civs"][ci]
        print("    (civ[%d] name=%r units=%d)"
              % (ci, civ.get("name"), len(civ.get("units") or [])))
        rec = None
        for u in civ.get("units") or []:
            if u.get("id") == UNIT:
                rec = u
                break
        if rec is None:
            print(" 1. %s unit %d -> NOT IN ARRAY" % (cname, UNIT))
        else:
            print(" 1. %s unit %d train_locations=%s"
                  % (cname, UNIT, rec.get("train_locations")))
    return raw


def tree_state(label, game_root, stems=("BRITONS", "INCAS")):
    print("--- %s ---" % label)
    trees = CT.load_trees(game_root)
    print("    trees loaded: %d" % len(trees))
    for stem in stems:
        t = trees.get(stem)
        if t is None:
            print(" 6. %s -> no tree file" % stem)
            continue
        rows = [r for r in (t.get(CT.UNITS_KEY) or [])
                if isinstance(r, dict) and r.get("Node ID") == UNIT]
        if rows:
            for r in rows:
                print(" 6. %-8s status=%-18s age=%s bldg=%s trigger=%s"
                      % (stem, r.get("Node Status"), r.get("Age ID"),
                         r.get("Building ID"), r.get("Trigger Tech ID")))
        else:
            print(" 6. %-8s 2550 row: none" % stem)


def panel_state(label, panel_path, civs=("Britons", "Incas")):
    print("--- %s ---" % label)
    text, obj = BP.load_panel(panel_path)
    for civ in civs:
        blocks = BP.buildings(obj, civ)
        found = []
        for blk in blocks:
            bid = blk.get("ID")
            for e in BP.entries(obj, civ, bid, BP.UNITS_KEY):
                if e.get("ID") == UNIT:
                    found.append((bid, e))
        print(" 7. %-8s panel 2550: %s" % (civ, found if found else "none"))


def main():
    print("=" * 78)
    print("SHIPPED")
    print("=" * 78)
    dat_state(DAT, "shipped .dat")
    tree_state("shipped tree", GAME)
    panel_state("shipped panel",
                os.path.join(GAME, "resources", "_common", "dat",
                             "futuravailableunits.json"))

    for v in ("v5", "v6"):
        d = os.path.join(HERE, "out_dshtest_%s" % v)
        if not os.path.isdir(d):
            continue
        print()
        print("=" * 78)
        print(v.upper() + "  " + d)
        print("=" * 78)
        dat_state(os.path.join(d, "resources", "_common", "dat",
                               "empires2_x2_p1.dat"), "%s .dat" % v)
        tree_state("%s tree" % v, d)
        panel_state("%s panel" % v,
                    os.path.join(d, "resources", "_common", "dat",
                                 "futuravailableunits.json"))


if __name__ == "__main__":
    import traceback
    try:
        main()
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        raise
