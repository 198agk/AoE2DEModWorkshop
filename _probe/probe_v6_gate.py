# -*- coding: utf-8 -*-
r"""Why does the Barracks button still wait for a Castle?

v6 removed layer 5 (the `TechTree` `UnitConnection.EnablingResearch` = 263) and the
user reports the button STILL only appears after a Castle is built.  So the Castle
gate is not the connection field -- the remaining suspect is layer 3, the NEW
effect attached to `tech 263`.

`tech 263` is `Longbow (make avail)`, which the engine researches automatically
when a British player builds a Castle.  Attaching the enable command there makes
the unit available exactly when the Castle goes up, whatever else is set.

This probe reads the shipped `.dat` and the built v6 `.dat` and prints, for unit
2550 and tech 263:

  * every effect command that mentions unit 2550, with its owning tech
  * tech 263's owner civ and its commands
  * the TechTree UnitConnection for 2550 (EnablingResearch / RequiredResearch)
  * the British unit 2550 record's train locations and button ids

so v7 can be aimed at the one field that carries the gate.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod.dat import locate as L                       # noqa: E402
from aoe2mod.dat import parser as P                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
V6 = os.path.join(HERE, "out_dshtest_v6", "resources", "_common", "dat",
                  "empires2_x2_p1.dat")

UNIT = 2550
TECH = 263


def load(path):
    data, how = P.load_dat(path)
    p = P.Parser(data)
    p.parse()
    return data, p


def report(label, path):
    print("=" * 74)
    print("%s   %s" % (label, path))
    print("=" * 74)
    data, p = load(path)
    civs = p.stats["civs"]
    gv = p.r.gv

    # --- the TechTree unit connection for 2550
    conn = L.locate_connections(data) if hasattr(L, "locate_connections") else None
    print("\n-- TechTree UnitConnection for unit %d" % UNIT)
    try:
        recs = L.locate_tech_tree_units(data, p.stats.get("tech_tree_off"),
                                        p.stats)
    except Exception as e:                                 # noqa: BLE001
        recs = None
        print("   (locate_tech_tree_units unavailable: %s)" % e)
    for r in (recs or []):
        if r.get("unit_id") == UNIT:
            print("   %s" % {k: v for k, v in r.items() if not k.startswith("_")})

    # --- every effect command naming unit 2550
    records, start = L.locate_effects(data)
    print("\n-- effect commands naming unit %d" % UNIT)
    owners = {}
    for ef in records:
        for ci, c in enumerate(ef["commands"]):
            vals = [c.get("a"), c.get("b"), c.get("c"), c.get("d")]
            if UNIT in (c.get("a"), c.get("d")) or float(UNIT) in [float(x) for x in vals if isinstance(x, (int, float))]:
                owners.setdefault(ef["index"], []).append(
                    {"i": ci, "type": c.get("type"), "a": c.get("a"),
                     "b": c.get("b"), "c": c.get("c"), "d": c.get("d")})
    if not owners:
        print("   (none)")
    for ix, cmds in sorted(owners.items()):
        users = [i for i, t in enumerate(p.stats["techs"]) if t.get("effect_id") == ix]
        print("   effect %-5d used by techs %s" % (ix, users))
        for c in cmds:
            print("        %s" % c)

    # --- tech 263 and the Champi Scout's own make-avail tech
    for tn in (TECH, 1350, 1351):
        print("\n-- tech %d" % tn)
        t = p.stats["techs"][tn]
        print("   name=%r civ=%s effect_id=%s"
              % (t.get("name"), t.get("civ"), t.get("effect_id")))
        print("   required_techs=%s" % (t.get("required_techs"),))
        for c in (t.get("commands") or []):
            print("      %s" % {k: v for k, v in c.items() if not k.startswith("_")})
        print("   research_locations=%s" % [
            rl if isinstance(rl, dict) else str(rl)
            for rl in (t.get("research_locations") or [])])

    # --- the British/Turkish/Incan unit records for 2550
    print("\n-- per-civ unit records for %d" % UNIT)
    for ci in range(len(civs)):
        civ = civs[ci]
        rec = None
        for u in civ["units"]:
            if u.get("id") == UNIT:
                rec = u
                break
        if rec is None:
            continue
        # only show the ones that matter: the home civs and the target
        if civ["name"] not in ("British", "Incas", "Mapuche", "Muisca", "Tupi",
                               "Gaia"):
            continue
        tl = [{k: v for k, v in x.items() if not k.startswith("_")}
              for x in (rec.get("train_locations") or [])]
        t50 = rec.get("type50") or {}
        print("   %-10s type=%-3s hp=%-5s enabled=%s disabled=%s  train=%s"
              % (civ["name"], rec.get("type"), (t50.get("hit_points")),
                 rec.get("enabled"), rec.get("disabled"), tl))
    print()


report("SHIPPED", SHIPPED)
report("V6 (the mod the user ran)", V6)
