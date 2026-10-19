# -*- coding: utf-8 -*-
r"""What does the SHIPPED corpus do when an upgrade chain is broken?

The question that decides how `revoke` must behave: when a civilization does NOT
have node N, what do the shipped tree files do with the row whose `Link ID` is N?

`Link ID` is the upgrade chain's predecessor, established by the JSON-layer report
(`75 -> 74`, `77 -> 75`, `473 -> 77`, `567 -> 473`, `358 -> 93`, `359 -> 358`,
`24 -> 4`, `492 -> 24`) and by 78 `.dat` UnitConnection `group` chains.

There are only three possible answers, and they need different fixes:

  1. the row is ABSENT too   -> revoke must cascade down the chain
  2. the row is present with `Link ID = -1`  -> revoke must cut the link
  3. the row is present with `Link ID = <other>`  -> revoke must re-point it

Measured over the 62 shipped files, so the fix copies what the game ships instead
of inventing a state.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_broken_chain.py
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

trees = CT.load_trees(GAME)

cases = collections.Counter()
examples = collections.defaultdict(list)

for stem in sorted(trees):
    t = trees[stem]
    nodes = {}
    for r in CT.rows_of(t):
        if not isinstance(r, dict):
            continue
        try:
            nodes[int(r.get("Node ID"))] = r
        except (TypeError, ValueError):
            pass
    for nid, r in nodes.items():
        try:
            link = int(r.get("Link ID"))
        except (TypeError, ValueError):
            continue
        if link < 0 or link in nodes:
            continue
        # `nid` links to `link`, and `link` is NOT in this file.
        cases["present_with_dangling"] += 1
        if len(examples["present_with_dangling"]) < 6:
            examples["present_with_dangling"].append((stem, nid, link))

print("A  shipped corpus: rows whose Link ID names a node the same file lacks")
print("     count: %d" % cases["present_with_dangling"])
for e in examples["present_with_dangling"]:
    print("        %-11s node %-6s -> link %-6s (missing)" % e)

print()
print("B  the reverse question, which is the one revoke has to answer")
print("   For every (civ, node) where node is a row and is ALSO some row's Link ID:")
print("   look at what the SAME civ does with the rows that link UP to node, when")
print("   node itself is absent from a DIFFERENT civ.  Counted the clean way --")
print("   compare, per civ, the pair (node present?, linked-from rows present?)")
pairs = collections.Counter()
for stem in sorted(trees):
    have = set()
    links = {}
    for r in CT.rows_of(trees[stem]):
        if not isinstance(r, dict):
            continue
        try:
            have.add(int(r.get("Node ID")))
        except (TypeError, ValueError):
            pass
        try:
            links[int(r.get("Node ID"))] = int(r.get("Link ID"))
        except (TypeError, ValueError):
            pass
    for nid, link in links.items():
        if link < 0 or nid not in have:
            continue
        # this civ HAS the successor but does it have the predecessor?
        pairs[("succ present", "pred present" if link in have else "pred ABSENT")] += 1

for k in sorted(pairs):
    print("     %-34s %d" % (" ; ".join(k), pairs[k]))
print()
print("   A pair of the form ('succ present', 'pred ABSENT') would mean the shipped")
print("   data DOES contain a successor without its predecessor.  If that count is 0,")
print("   the shipped corpus is strictly chain-closed and the cascade is the right fix.")

print()
print("C  the direct measurement: for each civ, does any row link to a MISSING node?")
_bad = [(s, e) for s, e in examples["present_with_dangling"]]
print("     civs with a dangling link: %d of %d"
      % (len({s for s, _n, _l in _bad}), len(trees)))
print()

print("BROKEN CHAIN: dangling rows in shipped corpus = %d ; "
      "successor-without-predecessor pairs = %d"
      % (cases["present_with_dangling"],
         pairs[("succ present", "pred ABSENT")]))
sys.exit(0)
