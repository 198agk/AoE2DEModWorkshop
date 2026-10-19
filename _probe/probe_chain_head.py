# -*- coding: utf-8 -*-
r"""Which repair does the shipped corpus permit -- cascade, or cut the link?

`revoke(N)` can leave the file consistent in two ways:

  CASCADE  delete every row whose chain reaches N (so a civ never has a successor
           without its predecessor -- the state the shipped corpus is in).
  CUT      set the successor's `Link ID` so the successor becomes a chain HEAD.

Both are valid JSON; only one is a state the game ships.  The discriminator:

  A unit row that is a chain HEAD has NO usable `Link ID` (the key is often absent
  entirely, not -1 -- probe_chain_head caught its own first version making that
  mistake).  If some of those heads ARE upgrades (they carry a `Trigger Tech ID`,
  i.e. a technology turns a predecessor into them), then CUT produces a shape the
  game already ships.  If every head is a base unit, CUT invents a state and
  CASCADE is the only corpus-faithful repair.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_chain_head.py
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


def _int(v, default=-1):
    """None/absent/bad -> default.  `int(None)` raising is what made v1 of this
    probe skip every chain head and report 'no heads at all'."""
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)

kinds = collections.Counter()
head_upgrades = []
for stem in sorted(trees):
    for r in CT.rows_of(trees[stem]):
        if not isinstance(r, dict):
            continue
        if r.get("Use Type") not in CT.UNIT_USE_TYPES:
            continue
        link = _int(r.get("Link ID"))
        trig = _int(r.get("Trigger Tech ID"))
        if link < 0:
            if trig >= 0:
                kinds["CHAIN HEAD that IS an upgrade (trig >= 0)"] += 1
                if len(head_upgrades) < 12:
                    head_upgrades.append((stem, r.get("Node ID"), trig,
                                         r.get("Name")))
            else:
                kinds["chain head, base unit (trig < 0)"] += 1
        else:
            kinds["has a predecessor (link >= 0)"] += 1

print("A  how the shipped corpus shapes a UNIT row (Link ID absent counts as head)")
for k in sorted(kinds):
    print("     %-46s %d" % (k, kinds[k]))
print("     total unit rows: %d" % sum(kinds.values()))

print()
print("B  chain heads that ARE upgrades -- do they exist at all?")
if head_upgrades:
    print("     YES, %d of them.  CUT (cut the link) is a shipped shape."
          % kinds["CHAIN HEAD that IS an upgrade (trig >= 0)"])
    for e in head_upgrades:
        print("        %-11s node %-6s trigger %-6s %s" % e)
else:
    print("     NONE.  Every chain head in the shipped corpus is a base unit, so a")
    print("     head that is an upgrade never occurs -> CUT would invent a state, and")
    print("     CASCADE is the only corpus-faithful repair.")

print()
print("C  is `Trigger Tech ID` per-civ?  (it decides whether CUT could ever be sent)")
trig_by_node = collections.defaultdict(set)
for stem in sorted(trees):
    for r in CT.rows_of(trees[stem]):
        if isinstance(r, dict) and r.get("Use Type") in CT.UNIT_USE_TYPES:
            nid = r.get("Node ID")
            if nid is not None:
                trig_by_node[nid].add(_int(r.get("Trigger Tech ID")))
_same = sum(1 for v in trig_by_node.values() if len(v) == 1)
_differ = sum(1 for v in trig_by_node.values() if len(v) > 1)
print("     identical across every civ that has the node: %d" % _same)
print("     DIFFERS per civ:                              %d" % _differ)
print("     ^ a per-civ Trigger Tech ID means the upgrade cost/tech is per civ,")
print("       so a repair that re-points a link must not assume global identity.")

print()
print("CHAIN HEAD: heads-that-are-upgrades = %d ; CASCADE is %s"
      % (kinds["CHAIN HEAD that IS an upgrade (trig >= 0)"],
         "NOT forced" if head_upgrades else "the only corpus-faithful repair"))
sys.exit(0)
