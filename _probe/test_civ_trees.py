# -*- coding: utf-8 -*-
"""Read the shipped `civ_trees.json` and answer the questions the `.dat` could not.

This is a gate, not a demo: each block states a claim the tool makes to a player
and checks it against the game's own files, read independently of the exporter.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "_golden")
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
TREES = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
CARDS = os.path.join(GOLDEN, "command_cards.json")
NAMES = os.path.join(GOLDEN, "entity_names.json")

fails = []


def check(name, got, want):
    ok = got == want
    if not ok:
        fails.append("%s: got %r want %r" % (name, got, want))
    print("  %-52s %-6s %s" % (name, "ok" if ok else "FAIL", got if ok else "%r != %r" % (got, want)))


def load(p):
    return json.load(io.open(p, encoding="utf-8-sig"))


def status_of(table, use, node, building=None):
    rows = (table.get(use) or {}).get(str(node)) or []
    if building is not None:
        rows = [r for r in rows if r[0] == building]
    if not rows:
        return "unknown"
    for r in rows:
        if r[1] == "C":
            return "available"
    return "gated" if any(r[1] == "R" for r in rows) else "unavailable"


def main():
    doc = load(os.path.join(GOLDEN, "civ_trees.json"))
    civs = doc["civs"]
    names = load(NAMES)

    print("== 1. the question that started this: Hand Cannoneer, per civilisation")
    tally = {}
    for civ, table in civs.items():
        tally.setdefault(status_of(table, "u", 5), []).append(civ)
    check("23 can research it", len(tally.get("gated", [])), 23)
    check("38 do not have it", len(tally.get("unavailable", [])), 38)
    check("Britons", status_of(civs["BRITONS"], "u", 5), "unavailable")
    check("Franks", status_of(civs["FRANKS"], "u", 5), "gated")
    check("Turks", status_of(civs["TURKS"], "u", 5), "gated")

    print("\n== 2. it agrees with the game file it came from, row for row")
    # Independent read: the exporter compresses rows, so a mismatch in the
    # compressed form would be invisible without going back to the source.
    rebuilt = 0
    for civ in sorted(os.listdir(TREES))[:62]:
        path = os.path.join(TREES, civ)
        raw = load(path)
        flat = {}
        for sec in ("civ_techs_buildings", "civ_techs_units"):
            for x in raw.get(sec) or []:
                nid, use = x.get("Node ID"), x.get("Use Type")
                if nid is None or use is None:
                    continue
                letter = {"Building": "b", "Unit": "u", "Tech": "t"}[use]
                status = {"ResearchedCompleted": "C", "ResearchRequired": "R",
                          "NotAvailable": "N"}[x["Node Status"]]
                flat.setdefault(letter, {}).setdefault(str(nid), []).append(
                    [x.get("Building ID"), status, x.get("Age ID")])
        mine = civs[civ[:-5]]
        for use, nodes in flat.items():
            for nid, rows in nodes.items():
                got = (mine.get(use) or {}).get(nid) or []
                if got != rows:
                    fails.append("row mismatch %s %s:%s" % (civ, use, nid))
                    rebuilt += 1
    check("all 62 civilisations round-trip row for row", rebuilt, 0)
    check("total rows", sum(len(v) for t in civs.values() for v in t.values()), 10734)

    print("\n== 3. a node number is not a global id space")
    # Britons node 4 is Archer (a unit). Node 4 must not be answered as a tech.
    check("BRITONS unit 4 (Archer)", status_of(civs["BRITONS"], "u", 4), "available")
    check("BRITONS tech 4 has no row", status_of(civs["BRITONS"], "t", 4), "unknown")
    # MAPUCHE node 93 is Spearman (unit) AND Ballistics (tech). Both must answer.
    check("MAPUCHE unit 93 (Spearman)", status_of(civs["MAPUCHE"], "u", 93), "available")
    check("MAPUCHE tech 93 (Ballistics)", status_of(civs["MAPUCHE"], "t", 93), "available")
    check("MAPUCHE unit 93 name", names["units"]["93"][0], "长矛兵")
    check("MAPUCHE tech 93 name", names["techs"]["93"][0], "弹道学")

    print("\n== 4. one unit, several buildings -- both rows survive")
    rows = civs["MAPUCHE"]["u"]["7"]
    check("MAPUCHE Skirmisher buildings", sorted(r[0] for r in rows), [87, 2556])
    rows = civs["BULGARIANS"]["u"]["440"]
    check("BULGARIANS Petard buildings", sorted(r[0] for r in rows), [82, 1251])

    print("\n== 5. the narrowing actually narrows: .dat card vs this civilisation")
    cards = load(CARDS)["cards"]
    dat_barracks = {e["unit"] for e in cards.get("12") or []}
    tree_barracks = {int(k) for k in civs["BRITONS"].get("u") or {}
                     if any(r[0] == 12 for r in civs["BRITONS"]["u"][k])}
    check("Barracks: .dat lists 49 units", len(dat_barracks), 49)
    check("Barracks: Britons tree lists 8", len(tree_barracks), 8)
    check("every tree unit is in the .dat card", sorted(dat_barracks & tree_barracks) == sorted(tree_barracks), True)
    check("tree has nothing the .dat lacks", len(tree_barracks - dat_barracks), 0)

    print("\n== 6. 'not in the file' is not 'not available'")
    check("GAIA has no tree file", "GAIA" in civs, False)
    check("unknown civ reads as unknown", status_of({}, "u", 5), "unknown")
    check("a node with no row reads as unknown", status_of(civs["BRITONS"], "u", 99999), "unknown")

    print("\n== 7. every named row resolves to a name")
    missing = []
    for civ, table in civs.items():
        for use, nodes in table.items():
            table_names = {"u": names["units"], "t": names["techs"], "b": names["units"]}[use]
            for nid in nodes:
                if nid not in table_names:
                    missing.append("%s %s:%s" % (civ, use, nid))
    check("rows without a name", len(missing), 0)
    for m in missing[:5]:
        print("   ", m)

    print("\nVERDICT")
    if fails:
        print("  FAILURES: %d" % len(fails))
        for f in fails:
            print("   -", f)
        sys.exit(1)
    print("  ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
