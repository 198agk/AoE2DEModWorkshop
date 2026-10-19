# -*- coding: utf-8 -*-
r"""Is a TREE-ONLY experiment on unit 2550 (Champi Scout) clean?

The open question this settles: does a mod's `CivTechTrees/<CIV>.json` file
actually get read by the running game?  Every previous attempt was confounded --
one test edited the `.dat` at the same time, and `dsh test v9` deleted the tree
row while leaving a dangling `Link ID` (so the file was not even well formed)
AND deleted the panel entry, which made the reading unattributable.

The clean experiment ships ONE tree file and a byte-identical `.dat` carrier, so
any change on screen can only have come from the tree layer.

For that to be interpretable, the `.dat` must ALREADY allow the unit in both
directions, otherwise "no button" means ".dat refused it", not "the tree write
was ignored".  This probe measures exactly that:

  A  the shipped tree state for both civs (the baseline the reading compares to)
  B  is unit 2550 present in each civ's own `.dat` unit array?
  C  the two global effects that turn 2550 on and off, and whether each civ can
     ever research them -- i.e. whether the `.dat` gate is open for that civ
  D  what the CASCADE removes when the row is revoked

Run:  python _probe/probe_tree_only_subject.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from aoe2mod.dat import parser as P                    # noqa: E402
from aoe2mod.game import civtechtrees as CT            # noqa: E402
from aoe2mod.game import locations as G                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
CIVS = ("INCAS", "BRITONS")


def tree(key):
    path = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees",
                        "%s.json" % key)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    fails = []

    def check(name, ok, detail=""):
        print("  %-66s %s%s" % (name[:66], "PASS" if ok else "FAIL",
                                ("  " + str(detail)) if detail else ""))
        if not ok:
            fails.append(name)

    raw, how = P.load_dat(G.dat_path(GAME))
    st = P.Parser(raw)
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        st.parse()
    print("dat: %s, %d bytes (%s), %d civs, %d techs\n"
          % (os.path.basename(G.dat_path(GAME)), len(raw), how,
             len(st.stats["civs"]), len(st.stats["techs"])))

    print("A  the shipped tree baseline")
    trees = {k: tree(k) for k in CIVS}
    stat_incas = CT.node_status(trees["INCAS"], UNIT, CT.UNIT_USE_TYPES)
    stat_brit = CT.node_status(trees["BRITONS"], UNIT, CT.UNIT_USE_TYPES)
    print("   INCAS   : %s" % stat_incas)
    print("   BRITONS : %s" % stat_brit)
    check("Incas ships the unit (the revoke is a real change)",
          stat_incas == "ResearchedCompleted", stat_incas)
    check("Britons does NOT ship it (the grant is a real change)",
          stat_brit in (None, "NotAvailable"), stat_brit)

    print()
    print("B  is the unit in each civ's own .dat unit array?")
    civ_index = {c["name"]: i for i, c in enumerate(st.stats["civs"])}
    present = {}
    for key, disp in (("INCAS", "Incas"), ("BRITONS", "British")):
        i = civ_index.get(disp)
        ids = {u["id"] for u in st.stats["civs"][i]["units"]} if i is not None else set()
        present[key] = UNIT in ids
        print("   %-8s civ index %-3s unit array %d ids -> 2550 present: %s"
              % (key, i, len(ids), UNIT in ids))
    check("the unit is in the .dat array for BOTH civs",
          all(present.values()), present)

    print()
    print("C  the two global effects that toggle 2550, and who can reach them")
    enables, disables = [], []
    for ti, t in enumerate(st.stats["techs"]):
        eff = st.stats["effects"][t.get("effect_id") or 0] \
            if t.get("effect_id") is not None else None
        if not eff:
            continue
        for c in eff.get("commands") or []:
            cmd, a, b = c[0], c[1], c[2]
            if cmd != 2 or a != UNIT:
                continue
            (enables if b else disables).append((ti, t.get("civ"), t.get("name")))
            break
    print("   enable  commands: %s" % enables)
    print("   disable commands: %s" % disables)
    check("2550 is toggled by a global enable and a global disable",
          len(enables) >= 1 and len(disables) >= 1,
          "%d / %d" % (len(enables), len(disables)))

    # Who can reach the ANCHOR technology (the one that carries the enable)?
    # If the civ cannot research it, the .dat gate is closed and the tree write
    # would be read against a closed door -- an uninterpretable experiment.
    for key, disp in (("INCAS", "Incas"), ("BRITONS", "British")):
        reach = []
        for ti, civ, name in enables:
            row = None
            for r in CT.rows_of(trees[key]):
                if r.get("Use Type") == "Tech" and \
                        _num(r.get("Node ID")) == ti:
                    row = r
                    break
            reach.append((ti, name, civ, (row or {}).get("Node Status")))
        print("   %-8s anchor tech rows: %s" % (key, reach))

    print()
    print("D  what CASCADE removes on revoke")
    closed = CT.chain_closure(trees["INCAS"], UNIT, use_types=CT.UNIT_USE_TYPES)
    print("   chain_closure(INCAS, %d) = %s" % (UNIT, sorted(closed)))
    for uid in sorted(closed):
        row = CT.row_for(trees["INCAS"], uid, CT.UNIT_USE_TYPES)
        if row:
            print("     %-5s %-22s link=%s trig=%s"
                  % (uid, row.get("Name"), row.get("Link ID"),
                     row.get("Trigger Tech ID")))
    check("the closure removes the unit itself", UNIT in closed, sorted(closed))

    print()
    print("TREE-ONLY SUBJECT: %s"
          % ("READY" if not fails else "NOT READY -> %s" % fails))
    return 0 if not fails else 1


def _num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    sys.exit(main())
