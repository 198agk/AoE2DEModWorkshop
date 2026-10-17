# -*- coding: utf-8 -*-
r"""The shipped Incas recipe for a Dark-Age regional unit, field by field.

v5 put the enable command on `tech 263 'Longbow (make avail)'` and the button
appeared only after a Castle.  v6 removed `EnablingResearch` and it still did.
So the gate is whatever the engine uses to decide WHEN to research the tech the
enable command rides on.

The Incas can build the Champi Scout in the Dark Age.  The shipped data therefore
contains the correct recipe, and this probe reads it out:

  * the Incas' `.dat` train locations for unit 2550 (building, time, button)
  * the British record for the same unit, before and after v5/v6
  * `tech 1350 'Champi Scout (Make avail)'` -- the tech declared by the tree row's
    `Trigger Tech ID`, its civ, its research location, and its effect command
  * which of `1350`/`263` the engine would apply at game start

so v7 can copy the shipped route instead of attaching to a Castle-triggered tech.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
V6 = os.path.join(HERE, "out_dshtest_v6", "resources", "_common", "dat",
                  "empires2_x2_p1.dat")
TREES = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")

UNIT = 2550
CIVS = ("British", "Incas")


def records(path):
    data, _how = P.load_dat(path)
    pr = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        pr.parse()
    civs, _cs, _gv, _tail = L.locate(data, parser=pr)
    return data, pr, civs


def show(label, path):
    print("=" * 76)
    print(label)
    print("=" * 76)
    data, pr, civs = records(path)
    by = {c["name"]: c for c in civs}
    for cn in CIVS:
        c = by.get(cn)
        if c is None:
            print("  %s: NO SUCH CIV" % cn)
            continue
        units = [u for u in c["units"] if u.get("id") == UNIT]
        print("  %-9s unit %d : %d record(s)" % (cn, UNIT, len(units)))
        for u in units:
            tl = [{k: v for k, v in t.items() if not k.startswith("_off")}
                  for t in (u.get("train_locations") or [])]
            print("      type=%s  train_locations=%s" % (u.get("type"), tl))
            print("      keys=%s" % sorted(k for k in u
                                          if not k.startswith("_")))
    # unit 8 as the reference for what `EnablingResearch` looks like
    for cn in CIVS:
        c = by.get(cn)
        u8 = [u for u in c["units"] if u.get("id") == 8]
        if u8:
            print("  %-9s unit 8 (Longbowman) keys=%s"
                  % (cn, sorted(k for k in u8[0] if not k.startswith("_"))))
    print()


def techtree_connection(path, want_units):
    """Read the TechTree UnitConnection array the way the pin does."""
    data, pr, _civs = records(path)
    r = pr.r
    r.pos = pr.stage_offsets[-1][2] + 7 * 4
    # The TechTree section layout: read ages/buildings/research counts and then
    # the unit connections; mirror `test_enabling_research.py:74`.
    out = {}
    try:
        r.pos = pr.stage_offsets[-1][2] + 7 * 4
        ages = r.i32()
        buildings = [r.i32() for _ in range(pr.stats["tech_tree"]["buildings"])] \
            if isinstance(pr.stats.get("tech_tree"), dict) else None
    except Exception as e:                                  # noqa: BLE001
        return {"error": str(e)}
    return out


def main():
    show("SHIPPED", SHIPPED)
    show("V6 (what the user ran)", V6)

    print("=" * 76)
    print("the tree rows")
    print("=" * 76)
    for civ in CIVS:
        f = os.path.join(TREES, civ.upper() + ".json")
        if not os.path.exists(f):
            print("  %s: no tree file" % civ)
            continue
        o = json.loads(open(f, "rb").read().decode("utf-8"), strict=False)
        rows = [x for x in o.get("civ_techs_units", []) if x.get("Node ID") == UNIT]
        print("  %-9s %s" % (civ, json.dumps(rows, ensure_ascii=False,
                                             sort_keys=True)))
        techrows = [x for x in o.get("civ_techs_units", [])
                    if x.get("Use Type") == "Tech" and
                    x.get("Node ID") in (1350, 263)]
        print("             tech rows 1350/263: %s"
              % json.dumps(techrows, ensure_ascii=False, sort_keys=True))
    print()
    print("=" * 76)
    print("is tech 1350 / 263 a node anywhere in the trees?")
    print("=" * 76)
    for tid in (1350, 263, 8):
        holders = []
        for fn in sorted(os.listdir(TREES)):
            o = json.loads(open(os.path.join(TREES, fn), "rb").read()
                           .decode("utf-8"), strict=False)
            for x in o.get("civ_techs_units", []):
                if x.get("Use Type") == "Tech" and x.get("Node ID") == tid:
                    holders.append((fn[:-5], x.get("Node Status")))
        print("  tech %-5d in %d trees %s" % (tid, len(holders), holders[:6]))


if __name__ == "__main__":
    main()
