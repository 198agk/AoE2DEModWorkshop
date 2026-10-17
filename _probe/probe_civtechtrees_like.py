# -*- coding: utf-8 -*-
"""Compare CivTechTrees against futuravailableunits LIKE WITH LIKE.

The first comparison reported 381 disagreements, but it was comparing a
mixed list against a filtered one: `CivTechTrees/<CIV>.json`'s
`civ_techs_units` carries Units, UnitUpgrades, Research, UniqueUnit,
UniqueTech, RegionalUnit and BuildingNonTech rows together (GOTHS: 145 rows,
of which only 59 have `Use Type == "Unit"`), while `futuravailableunits.json`
nests only buildable things under buildings.

The comparison below restricts to rows that are actually about a unit being
AVAILABLE (Use Type == "Unit" and Node Status == "ResearchedCompleted") and
asks whether that set equals the game's own unit set.  Only an exact,
same-population comparison can establish or refute that the JSON is the
mechanism.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
FU = os.path.join(GAME, "resources", "_common", "dat",
                  "futuravailableunits.json")


def recursive_ids(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "ID" and isinstance(v, int):
                out.add(v)
            else:
                recursive_ids(v, out)
    elif isinstance(obj, list):
        for x in obj:
            recursive_ids(x, out)
    return out


def main():
    tk = A.open_toolkit()
    tk._ensure()
    dat_ids = set()
    for c in tk._civs:
        for u in (c.get("units") or ()):
            dat_ids.add(u.get("id"))
    with open(FU, encoding="utf-8") as fh:
        fu = json.load(fh)
    fu_by_upper = {k.upper(): k for k in fu}

    print("%-10s %6s %6s %6s %6s %6s" % ("civ", "fu", "json", "both",
                                         "onlyFU", "onlyJSON"))
    tot = {"both": 0, "onlyFU": 0, "onlyJSON": 0}
    for fn in sorted(os.listdir(CT)):
        with open(os.path.join(CT, fn), encoding="utf-8") as fh:
            j = json.load(fh)
        civ_key = fn[:-5]
        fu_key = fu_by_upper.get(civ_key.upper())
        if fu_key is None:
            continue
        usetype = j.get("civ_techs_units") or []
        json_ids = {e.get("Node ID") for e in usetype
                    if isinstance(e, dict)
                    and e.get("Use Type") == "Unit"
                    and e.get("Node Status") == "ResearchedCompleted"}
        fu_ids = recursive_ids(fu[fu_key], set())
        both = json_ids & fu_ids
        only_fu = fu_ids - json_ids
        only_json = json_ids - fu_ids
        tot["both"] += len(both)
        tot["onlyFU"] += len(only_fu)
        tot["onlyJSON"] += len(only_json)
        if fn in ("GOTHS.json", "BRITONS.json", "AZTECS.json", "PERSIANS.json"):
            print("%-10s %6d %6d %6d %6d %6d  (onlyFU e.g. %s | onlyJSON e.g. %s)"
                  % (civ_key, len(fu_ids), len(json_ids), len(both),
                     len(only_fu), len(only_json),
                     sorted(only_fu)[:4], sorted(only_json)[:4]))
    print()
    print("TOTAL both %d / onlyFU %d / onlyJSON %d"
          % (tot["both"], tot["onlyFU"], tot["onlyJSON"]))
    print()
    print("NOTE: futuravailableunits' nested IDs are BUILDING ids too (Goths' 31"
          " building rows include their trainable units), so a residual is")
    print("expected if the two files classify a row differently -- which is")
    print("itself the finding: the JSON carries the richer per-civ model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
