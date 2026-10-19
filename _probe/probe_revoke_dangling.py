# -*- coding: utf-8 -*-
r"""Does `revoke` leave a dangling reference behind?  (v9's fatal flaw, quantified)

`dsh test v9` revoked unit 2550 from the Incas by deleting its `Node ID 2550` row,
and the file was left carrying a row whose `Link ID` still said 2550.  Every one of
the 62 shipped tree files has ZERO dangling link ids, so the game was handed a state
it never ships -- which is why the v9 observation is marked PROVISIONAL instead of
being the answer to "does the menu read the tree".

This probe answers two questions with numbers:

  A. Shipped baseline: how many rows carry a `Link ID`, and is any of them dangling?
  B. Current `revoke`: after revoking a node that other rows link to, how many
     dangling link ids does the result carry?

If B is non-zero, `revoke` is a defect in the product, not just in an experiment:
`unit.availability` with action "revoke" would ship the same unreachable state.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_revoke_dangling.py
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def link_ids(tree):
    """{row_index: Link ID} for every row that carries one."""
    out = {}
    for i, r in enumerate(CT.rows_of(tree)):
        if isinstance(r, dict) and r.get("Link ID") not in (None, -1):
            out[i] = r.get("Link ID")
    return out


def node_ids(tree):
    return {r.get("Node ID") for r in CT.rows_of(tree)
            if isinstance(r, dict) and r.get("Node ID") not in (None, -1)}


def dangling(tree):
    ids = node_ids(tree)
    return {i: v for i, v in link_ids(tree).items() if v not in ids}


trees = CT.load_trees(GAME)
print("A  the shipped baseline -- what the game actually ships")
_total_links = 0
_dangling_civs = []
for stem in sorted(trees):
    t = trees[stem]
    n = len(link_ids(t))
    total_links = n
    _total_links += n
    d = dangling(t)
    if d:
        _dangling_civs.append((stem, d))
print("     civs: %d ; rows carrying a Link ID: %d" % (len(trees), _total_links))
check("no shipped tree file carries a dangling Link ID",
      not _dangling_civs,
      "civs with dangling links: %s" % (_dangling_civs[:3],))

print()
print("B  current revoke() -- does it clean up the links that pointed at the node?")
# Pick a node that is actually linked to by another row: use the whole corpus and
# take the first (civ, node) pair where node is BOTH a row and a Link ID target.
_target = None
for stem in sorted(trees):
    t = trees[stem]
    ids = node_ids(t)
    for i, v in link_ids(t).items():
        if v in ids:
            _target = (stem, v, i)
            break
    if _target:
        break
print("     subject: civ=%s node=%s (row #%s links to it)"
      % (_target[0], _target[1], _target[2]))
_stem, _node, _ri = _target
_probe = copy.deepcopy(trees[_stem])
_before_links = len(link_ids(_probe))
_removed = CT.revoke(_probe, _node)
_after = dangling(_probe)
print("     removed rows: %s ; links before: %s ; DANGLING after: %s"
      % (_removed, _before_links, _after))
check("revoke() removes a row", _removed >= 1, "removed=%r" % (_removed,))
check("revoke() leaves NO dangling Link ID  <- the v9 failure mode",
      not _after,
      "dangling=%s  (this is why v9 was provisional)" % (_after,))

print()
print("REVOKE DANGLING: baseline clean=%s ; revoke clean=%s"
      % (not _dangling_civs, not _after))
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
