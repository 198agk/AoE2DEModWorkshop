# -*- coding: utf-8 -*-
"""Pin what a TECH row's Node Status means, using known answers.

For a UNIT row, `ResearchedCompleted` plainly means "you can train it now" --
the unit is in your roster from the start.  For a TECH row the same word COULD
mean "already researched", which would be a completely different claim, and the
two readings predict opposite things about the shipped data:

  * "available to research"  -> Loom (id 22) is ResearchedCompleted for all 62
    civs, because every civ can research Loom.  Nobody starts with Loom done.
  * "already researched"     -> every civ would start with Loom, Wheelbarrow and
    its own unique tech already finished, which is false for all of them.

The independent cross-check is the .dat's own tech record: `Research.civ` names
the OWNING civilization for a unique/regional tech and is -1 for a global one.
That is a different file written by a different tool, so if the CivTechTrees rows
line up with it, the reading is established rather than assumed.

Also records the '+10000' name-id block measured separately: a tech row's
`Name String ID` equals the .dat record's LanguageDLLName + 10000 on 5081 of
5244 rows.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.dat import locate as L                              # noqa: E402
from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def tech_rows(tree):
    out = []
    for v in tree.values():
        if isinstance(v, list):
            for e in v:
                if isinstance(e, dict) and e.get("Use Type") == "Tech":
                    out.append(e)
    return out


def main():
    tk = A.open_toolkit()
    tk._ensure()
    tail, gv = tk._parsed[4], tk._parsed[3]
    techs = L.locate_techs(tk._raw, tail, gv)
    trees = CT.load_trees(GAME)
    civs = [c.get("name") for c in tk._civs]
    print("dat civs %d / tree files %d" % (len(civs), len(trees)))

    rows = [(c, e) for c, t in trees.items() for e in tech_rows(t)]

    # 1. the plain reading test: common techs
    print("\ncommon techs -- if ResearchedCompleted meant 'already researched',"
          " these could not be 62/62:")
    for nid, want in ((22, "Loom"), (249, "Hand Cart"), (8, "Town Watch"),
                      (213, "Wheelbarrow"), (14, "Horse Collar"), (101, "Feudal Age"),
                      (102, "Castle Age"), (103, "Imperial Age")):
        st = Counter(e.get("Node Status") for _, e in rows if e.get("Node ID") == nid)
        print("  id %-5d %-14s %s" % (nid, want, dict(st)))

    # 2. the decisive cross-check: .dat tech.civ vs the tree rows
    print("\n.dat tech.civ  vs  which civs carry a ResearchedCompleted row")
    owner_ok = owner_bad = 0
    bad = []
    for i, rec in enumerate(techs):
        oc = rec.get("civ")
        if oc is None or oc < 0:
            continue
        if oc >= len(civs):
            continue
        owner = CT.civ_file_stem(civs[oc])
        ready = sorted(civ for civ, e in rows
                       if e.get("Node ID") == i
                       and e.get("Node Status") == "ResearchedCompleted")
        listed = sorted(civ for civ, e in rows if e.get("Node ID") == i)
        if owner in ready:
            owner_ok += 1
        else:
            owner_bad += 1
            if len(bad) < 12:
                bad.append((i, rec.get("name"), owner, ready[:4], len(listed)))
    print("  techs with a named owner civ: %d" % (owner_ok + owner_bad))
    print("  owner has a ResearchedCompleted row: %d" % owner_ok)
    print("  owner does NOT: %d" % owner_bad)
    for b in bad:
        print("     id=%-5d %-34r owner=%-14s ready=%s listed=%d" % b)

    # 3. do non-owners ever carry the tech as ResearchedCompleted?
    print("\nunique/regional techs: how many civs carry them as ResearchedCompleted")
    spread = Counter()
    for i, rec in enumerate(techs):
        oc = rec.get("civ")
        if oc is None or oc < 0:
            continue
        ready = sorted(civ for civ, e in rows
                       if e.get("Node ID") == i
                       and e.get("Node Status") == "ResearchedCompleted")
        spread[len(ready)] += 1
    print("  ready-count histogram: %s" % dict(sorted(spread.items())))

    # 4. global techs (civ == -1): can they be NotAvailable for a civ?
    print("\nglobal techs whose row reads NotAvailable for at least one civ:")
    n_glob = 0
    n_with_na = 0
    for i, rec in enumerate(techs):
        if rec.get("civ") != -1:
            continue
        n_glob += 1
        st = {e.get("Node Status") for _, e in rows if e.get("Node ID") == i}
        if "NotAvailable" in st:
            n_with_na += 1
    print("  global techs: %d   some civ reads NotAvailable: %d"
          % (n_glob, n_with_na))

    # 5. the two ResearchRequired tech rows -- who are they?
    print("\ntech rows reading ResearchRequired:")
    for c, e in rows:
        if e.get("Node Status") == "ResearchRequired":
            print("   %-14s id=%-5d %r node_type=%s"
                  % (c, e.get("Node ID"), e.get("Name"), e.get("Node Type")))

    # 6. the 99 rows whose Name String ID is in neither block
    print("\ntech rows whose Node ID has no ResearchedCompleted row anywhere:")
    ids = {e.get("Node ID") for _, e in rows}
    orphan = []
    for nid in sorted(ids):
        ready = [c for c in trees
                 if CT.node_status(trees[c], nid) == "ResearchedCompleted"]
        # node_status is unit-filtered, so this is deliberately the WRONG reading;
        # it is printed to show the trap, not as a result.
        orphan.append((nid, len(ready)))
    blocked = [n for n, r in orphan if r == 0]
    print("  (via the unit-filtered node_status): %d ids look ownerless" % len(blocked))
    print("  -- that reading is the TRAP this probe exists to expose")


if __name__ == "__main__":
    sys.exit(main())
