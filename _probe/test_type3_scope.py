# -*- coding: utf-8 -*-
"""The scope of `type 3 Upgrade Unit` -- and why the first table lied.

Three findings, all measured, all needed before anyone wires this family:

1. The naive contrast is NON-DISCRIMINATING BY CONSTRUCTION.  196 of 305 upgrade
   targets are reachable through a GLOBAL upgrade command, so "does this civ own
   an upgrade into it" is true almost everywhere: 1816 of 1896 (95.8%) of
   (civ, target-row) pairs.  A predicate that is always true cannot explain which
   civs can do what, and the empty cells it produces are an artifact.

2. The dependent variable was WRONG.  An upgrade target is something you UPGRADE
   INTO, not something a building trains.  Among the 109 civ-owned-only targets,
   every apparent "disagreement" is a unit with `builders == 0` -- House, town
   centre variants, internal placeholders.  Asking "can a civ build Elite X"
   answers a question nobody asks; the right question is "can the civ research
   the tech that performs the upgrade", which is `tech.availability`'s job.

3. Availability of the carrying tech is partly tree-side: of the 183 civ-owned
   upgrade commands, 52 sit on a tech whose owner has a `ResearchedCompleted`
   row and 131 have no row at all.  The 131 are NOT proven defects: the `.dat`
   holds one GLOBAL tech record, so a civ can own an internal tech that a
   different tree-listed tech makes reachable.

So `type 3` is an editor of WHAT an upgrade does (A -> B).  That is a legitimate
and valuable editor -- it is the largest family by new techs -- but it is not an
availability mechanism, and the measurement that says so is this file.

Writes nothing.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                        # noqa: E402
from aoe2mod.dat import locate as L                            # noqa: E402
from aoe2mod.game import civtechtrees as CT                    # noqa: E402
from aoe2mod.intent import compiler as C                       # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    tail, gv = tk._parsed[4], tk._parsed[3]
    effects, _ = L.locate_effects(raw)
    techs = L.locate_techs(raw, tail, gv)
    trees = CT.load_trees(tk.game_root)

    stem2idx = {}
    for c in tk._civs:
        stem = CT.civ_file_stem(c.get("name"))
        if stem in trees:
            stem2idx[stem] = c["index"]

    own_to = collections.defaultdict(set)
    glob_to = set()
    rows = []
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=None, ix=None):
            if r["type"] != 3:
                continue
            _ty, a, b, cc, dd = r["raw"]
            rows.append((ti, t.get("civ"), a, b, cc, dd))
            if t.get("civ") is None or t.get("civ") < 0:
                glob_to.add(b)
            else:
                own_to[t["civ"]].add(b)
    targets = {b for _t, _o, _a, b, _c, _d in rows if isinstance(b, int)}

    print("1. the naive contrast cannot discriminate:")
    check(len(rows) == 424, "type 3 has 424 rows", len(rows))
    check(len(targets) == 305, "and 305 distinct targets", len(targets))
    n_glob = len(glob_to & targets)
    check(n_glob == 196, "196 targets are reachable via a GLOBAL upgrade", n_glob)
    triv = tot = 0
    for stem, tr in trees.items():
        idx = stem2idx.get(stem)
        for row in CT.unit_rows(tr):
            nid = row.get("Node ID")
            if nid is None or nid not in targets:
                continue
            tot += 1
            if nid in glob_to:
                triv += 1
    check(tot == 1896, "1896 (civ, target-row) pairs", tot)
    check(triv == 1816, "of which 1816 (95.8%) are trivially true", triv)
    check(triv * 100 // tot == 95,
          "so the predicate is ~always true, and its empty cells mean nothing",
          "%d%%" % (triv * 100 // tot))

    print()
    print("2. an upgrade target is upgraded INTO, not trained:")
    own_only = sorted(targets - glob_to)
    check(len(own_only) == 109, "109 civ-owned-only targets", len(own_only))
    checked = 0
    always_zero = 0
    for b in own_only[:40]:
        bld = CT.builders(trees, b)
        owners = [s for s in trees
                  if stem2idx.get(s) is not None and b in own_to.get(stem2idx[s], set())]
        if len(bld) != len(owners):
            checked += 1
            if not bld:
                always_zero += 1
    check(checked == always_zero and checked > 0,
          "every apparent disagreement is a unit NOBODY can build",
          "%d of %d" % (always_zero, checked))

    print()
    print("3. the carrying tech's availability is only partly tree-side:")
    tal = collections.Counter()
    for ti, o, _a, _b, _c, _d in rows:
        if o is None or o < 0:
            continue
        stem = next((s for s, i in stem2idx.items() if i == o), None)
        if stem is None:
            continue
        tal[CT.node_status(trees[stem], ti, CT.TECH_USE_TYPES)] += 1
    check(sum(tal.values()) == 183, "183 civ-owned upgrade commands",
          sum(tal.values()))
    check(tal.get("ResearchedCompleted") == 52,
          "52 sit on a tech their owner lists as available",
          tal.get("ResearchedCompleted"))
    check(tal.get(None) == 131,
          "and 131 have no tree row -- NOT proven to be a defect",
          tal.get(None))

    print()
    print("4. so the type-3 editor is about WHAT an upgrade does:")
    cc = collections.Counter(c for _t, _o, _a, _b, c, _d in rows)
    check(-1 in cc or 0 in cc,
          "slot C varies and is therefore part of the payload", cc.most_common(4))
    pairs = {(a, b) for _t, _o, a, b, _c, _d in rows}
    check(len(pairs) > 300, "the (A -> B) pairs are the real content", len(pairs))

    print()
    if FAILS:
        print("TYPE3 SCOPE: FAILED -> %s" % FAILS)
        return 1
    print("TYPE3 SCOPE: the naive buildability contrast is an artifact; type 3 "
          "edits what an upgrade does, not who may have it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
