# -*- coding: utf-8 -*-
"""Export `CivTechTrees/*.json` to `_golden/civ_trees.json`.

Why this file exists
--------------------
The tool used to answer "can this civilisation train this unit?" by reading the
`.dat`, and the answer came out wrong for Hand Cannoneer: 23 civilisations can
build it, 38 cannot, and the `.dat` has no per-civilisation field that says so.
`项目状态.md` §3 recorded that as an open question -- "does the shipped data
carry per-civ availability at all?"

It does, in a file the tool was not reading. Every civilisation has a
`resources/_common/dat/CivTechTrees/<CIV>.json`, and each entry carries a
`Node Status` of `ResearchedCompleted`, `ResearchRequired` or `NotAvailable`.
Measured over all 62 files:

    ResearchedCompleted  8642
    ResearchRequired      563
    NotAvailable         1537

Hand Cannoneer across 62 civilisations: 23 ResearchRequired, 38 NotAvailable,
1 ResearchedCompleted (Gaia's successor row) -- which is the number the `.dat`
could not produce.

The key is `(Use Type, Node ID, Building ID)`, NOT `(Use Type, Node ID)`. A unit
can be listed under several buildings: MAPUCHE has Skirmisher under building 87
and 2556, BULGARIANS has Petard under 82 and 1251. Keying on `(use, node)` drops
a row silently -- 8 such pairs exist on the shipped data, and 8 dropped rows is
a wrong answer about 8 units.

`Use Type` also decides which id space `Node ID` lives in: `Unit` -> unit ids,
`Tech` -> tech ids, `Building` -> building ids. A reader that ignores it will
match a unit id against a tech id and find a name for it -- `civ_techs_units`
contains both, and node 93 is Spearman (unit) in one row and Ballistics (tech)
in another.
"""
import glob
import io
import json
import os
import sys

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
SRC = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "_golden", "civ_trees.json")

# Status is stored as one character because it is repeated 10,742 times.
STATUS = {
    "ResearchedCompleted": "C",   # available from the start of the match
    "ResearchRequired": "R",      # available, but a tech gates it
    "NotAvailable": "N",          # this civilisation cannot have it
}
USE = {"Building": "b", "Unit": "u", "Tech": "t"}


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.json")))
    if not files:
        sys.exit("no CivTechTrees json under %s" % SRC)

    civs = {}
    conflicts = []
    for path in files:
        civ = os.path.basename(path)[:-5]
        doc = json.load(io.open(path, encoding="utf-8-sig"))
        table = {}
        for section in ("civ_techs_buildings", "civ_techs_units"):
            for x in doc.get(section) or []:
                node = x.get("Node ID")
                use = USE.get(x.get("Use Type") or "")
                if node is None or use is None:
                    continue
                status = STATUS.get(x.get("Node Status"))
                if status is None:
                    continue
                row = [x.get("Building ID"), status, x.get("Age ID")]
                bucket = table.setdefault(use, {}).setdefault(str(node), [])
                if row in bucket:
                    continue
                # Same (use, node, building) with a different status would mean
                # the file contradicts itself and one of the two rows is being
                # thrown away. Measured: 0 occurrences. Record it if that ever
                # changes, rather than letting "last wins" hide it.
                for old in bucket:
                    if old[0] == row[0] and old[1] != row[1]:
                        conflicts.append((civ, use, node, old, row))
                bucket.append(row)
        civs[civ] = table

    doc = {
        "$comment": "Exported from resources/_common/dat/CivTechTrees/*.json by "
                    "_probe/make_civ_trees.py. Status: C=available, "
                    "R=gated by a tech, N=not for this civilisation. "
                    "Key is (Use Type letter, Node ID); rows are "
                    "[building id, status, age id].",
        "source": "CivTechTrees/*.json",
        "status_legend": STATUS,
        "use_legend": USE,
        "civs": civs,
    }
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)

    rows = sum(len(v) for t in civs.values() for v in t.values())
    print("civs %d  keys %d  rows %d  bytes %d"
          % (len(civs), sum(len(t) for t in civs.values()), rows, len(text.encode("utf-8"))))
    print("conflicts %d" % len(conflicts))
    for c in conflicts[:5]:
        print("  ", c)

    # Self-check against the numbers this exporter was written from: the Hand
    # Cannoneer split is the observation that started the whole thing, so a
    # regenerated table that no longer reproduces it is a broken export.
    tally = {}
    for civ, table in civs.items():
        for row in table.get("u", {}).get("5", []):
            if row[0] == 87:                     # Barracks/Archery Range row
                tally[row[1]] = tally.get(row[1], 0) + 1
    print("Hand Cannoneer (u:5 @ b:87) status tally:", tally)
    ok = tally.get("R") == 23 and tally.get("N") == 38
    print("verification ok", ok)
    if not ok:
        sys.exit("the table no longer reproduces the measured split")


if __name__ == "__main__":
    main()
