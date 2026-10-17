"""Find a build-panel question that can be answered IN GAME WITH NO MOD AT ALL.

The smoke test needs the user to install something and look at a panel.  There
is a strictly better experiment available if the two candidate files disagree
on something the game already ships: then the user just plays a normal game and
looks at a normal panel.

This script joins the two files that already exist on disk:

  * ``CivTechTrees/<CIV>.json``      -- the tree layer, which ``unit.availability``
                                        writes (and whose write did NOT take
                                        effect in the 2026-10-14 test)
  * ``futuravailableunits.json``     -- the command-panel sibling (the same file
                                        the second smoke mod edits)

and prints every (civ, unit) pair where they disagree, with everything the user
would need to SEE the difference:

  * is the unit in the civ's own barracks/range/etc. at all
  * what the tree says (``ResearchedCompleted`` / ``ResearchRequired`` /
    ``NotAvailable`` / absent)
  * what the panel file lists

Scope note: only the 55 civs that HAVE a panel entry can be compared -- the 6
Chronicles civs and MAGYAR have no entry at all, and counting those as
"disagreement" produced 353 phantom mismatches in an earlier probe.  That is
why the scope is a parameter here and not an afterthought.

Run:  python _probe/probe_shipped_disagreement.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.semantic import index as SI  # noqa: E402

FU_REL = os.path.join("resources", "_common", "dat", "futuravailableunits.json")


def panel_units(fu, civ):
    """{building_id: [unit_id, ...]} for one civ, from the panel file."""
    out = {}
    for bl in (fu.get(civ) or {}).get("Buildings", []):
        out[bl.get("ID")] = [u.get("ID") for u in bl.get("Units", [])]
    return out


def main():
    tk = A.open_toolkit()
    game = tk.game_root
    trees = CT.load_trees(game)
    fu = json.loads(open(os.path.join(game, FU_REL), "rb").read().decode("utf-8-sig"))
    sem = SI.index()

    def name(uid):
        e = sem.units.get(uid)
        return (e.en if e and e.en else e.zh if e else "?") or "?"

    # The panel file keys civs by DISPLAY name ("Britons") while the tree keys
    # them by FILE stem ("BRITONS"), so a naive `c in fu` match finds nothing.
    # Upper-casing the panel key resolves all but the file-stem oddities
    # (Magyars -> MAGYAR, Hindustanis -> INDIANS), which CIV_FILE_OVERRIDES
    # already knows about -- so go through it rather than re-guessing.
    by_tree = {}
    for k in fu:
        cand = CT.civ_file_stem(k)
        if cand in trees:
            by_tree[cand] = k
        elif k.upper() in trees:
            by_tree[k.upper()] = k

    covered = sorted(by_tree)
    print("tree civs %d / panel civs %d / comparable %d"
          % (len(trees), len(fu), len(covered)))
    unmapped = [k for k in fu if k not in by_tree.values()]
    if unmapped:
        print("panel civs with no tree file: %s" % unmapped)
    print()
    # Restrict to ids the tree layer tracks as units AT ALL.  The panel file
    # also lists BUILDINGS (under a build-menu entry, building 118), and those
    # ids have no unit row anywhere -- counting them produced 1082 "conflicts"
    # that are a scope error, not a disagreement.  The comparable set is the
    # unit space the tree actually models.
    node_ids = set()
    for civ in trees:
        for row in CT.unit_rows(trees[civ]):
            node_ids.add(row.get("Node ID"))
    print("unit ids the tree models anywhere: %d" % len(node_ids))
    print()

    # Every unit the panel lists anywhere, per civ, plus which building lists it.
    rows = []
    for civ in covered:
        where = {}
        for bid, ids in panel_units(fu, by_tree[civ]).items():
            for uid in ids:
                if uid in node_ids:
                    where.setdefault(uid, []).append(bid)
        for uid in sorted(where):
            st = CT.node_status(trees[civ], uid)
            if CT.can_build(trees[civ], uid):
                continue  # both sides agree it is buildable; not informative
            rows.append((civ, uid, st, where[uid]))

    print("panel lists a unit the TREE says cannot be built: %d pairs" % len(rows))
    print()
    if rows:
        print("%-14s %-6s %-20s %-28s %s"
              % ("civ", "unit", "name", "tree says", "panel lists it under building"))
        for civ, uid, st, bids in rows:
            print("%-14s %-6d %-20s %-28s %s"
                  % (civ, uid, name(uid)[:20], st if st is not None else "(absent)",
                     ",".join(str(b) for b in bids)))
        print()

    # The reverse direction: the tree says buildable, the panel omits it.
    miss = []
    for civ in covered:
        listed = set()
        for ids in panel_units(fu, by_tree[civ]).values():
            listed.update(ids)
        for row in CT.unit_rows(trees[civ]):
            uid = row.get("Node ID")
            if not CT.can_build(trees[civ], uid):
                continue
            if uid not in listed:
                miss.append((civ, uid, CT.node_status(trees[civ], uid)))
    print("TREE says buildable but the panel omits it: %d pairs" % len(miss))
    for civ, uid, st in miss[:40]:
        print("  %-14s %-6d %-20s %s" % (civ, uid, name(uid)[:20], st))
    print()

    print("=" * 72)
    print("WHAT THIS MEANS")
    print("  The two shipped files disagree on exactly %d pairs, and they" % (len(rows) + len(miss)))
    print("  disagree in a SYSTEMATIC way:")
    print("   * the panel file omits units the tree calls ResearchRequired")
    print("     (Goths Huskarl / Huns Tarkan at the Barracks/Stable -- both")
    print("     really ARE trainable, but only after a unique tech) and two it")
    print("     calls ResearchedCompleted (Georgians/Sicilians Siege Onager).")
    print("   * it lists units the tree calls NotAvailable (Jurchens Long")
    print("     Swordsman line, Muisca Halberdier, Wu Heavy Cav Archer, ...).")
    print()
    print("  So the panel file is NOT a per-civ availability model the way the")
    print("  tree is: it has no place to say 'gated behind a research'.")
    print("  Which one the running game obeys on the %d inclusion pairs is a" % len(rows))
    print("  question only a running game can answer -- but every one of those")
    print("  pairs needs NO MOD to observe, which is a cheaper experiment than")
    print("  the smoke test.")
    print()
    print("ASSERTIONS")
    fails = []
    if len(rows) != 11:
        fails.append("tree-says-no/panel-says-yes is %d, expected 11" % len(rows))
    if len(miss) != 7:
        fails.append("tree-says-yes/panel-omits is %d, expected 7" % len(miss))
    if len(covered) != 56:
        fails.append("comparable civs %d, expected 56" % len(covered))
    if node_ids and len(node_ids) != 287:
        fails.append("tree unit ids %d, expected 287" % len(node_ids))
    # Every inclusion pair must be one the tree calls NotAvailable, and every
    # omission must be one the tree calls available -- otherwise this is not the
    # systematic disagreement the note above describes.
    bad_inc = [(c, u) for c, u, st, _b in rows if st != "NotAvailable"]
    if bad_inc:
        fails.append("inclusions the tree does not call NotAvailable: %s" % bad_inc)
    bad_om = [(c, u, st) for c, u, st in miss if st not in
              ("ResearchRequired", "ResearchedCompleted")]
    if bad_om:
        fails.append("omissions with an unexpected status: %s" % bad_om)
    for f in fails:
        print("  [FAIL] %s" % f)
    if fails:
        print("SHIPPED DISAGREEMENT: FAILED")
        return 1
    print("  [PASS] the disagreement between the two shipped files is exactly")
    print("         the two systematic kinds above -- nothing unexplained")
    print("SHIPPED DISAGREEMENT: the two files disagree on 18 pairs, all of")
    print("them systematic, none of them requiring a mod to observe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
