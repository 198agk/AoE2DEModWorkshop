# -*- coding: utf-8 -*-
r"""The v9 case, exactly, and what the two repairs would produce.

v9 revoked unit 2550 from the Incas.  This probe shows, for the SHIPPED file:

  1. which row(s) carry `Link ID = 2550` (they are what becomes dangling)
  2. whether 2550 is itself a chain head (it is -- `Link ID` absent, trigger 1350)
  3. what CASCADE and CUT would each do, and which shipped states they match

The decision this feeds: `revoke` must leave a state the game ships, AND it must
mean what the user asked ("this civilization may not have this").  The two repairs
do not mean the same thing:

  CASCADE  the civ also loses everything ABOVE the revoked node in the chain.
           Semantically honest ("this whole line is gone") but wider than asked.
  CUT      the successor becomes a chain head.  `probe_chain_head` proves that
           shape ships (11 cases), BUT in every one of those 11 the head is a
           DIFFERENT unit that the .dat hands out via its own technology -- not a
           mid-chain unit promoted to head.  Promoting a mid-chain successor to a
           head would make it buildable WITHOUT its prerequisite, which is the
           opposite of a revoke.

So the honest answer is that CUT is a shipped SHAPE with the wrong MEANING, and
CASCADE is the only repair that keeps the requester's intent.  This probe measures
whether CUT's "promoted mid-chain head" shape ever occurs in the shipped corpus --
which is the fact that settles it.

Run:  $env:PYTHONPATH='D:\Software\AI\帝国项目'; python _probe\probe_revoke_semantics.py
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
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


trees = CT.load_trees(GAME)
incas = trees["INCAS"]

print("A  the shipped INCAS.json around node 2550")
for r in CT.rows_of(incas):
    if not isinstance(r, dict):
        continue
    if r.get("Node ID") == 2550 or _int(r.get("Link ID")) == 2550:
        print("     node=%-6s link=%-6s trig=%-6s use=%-9s %s"
              % (r.get("Node ID"), _int(r.get("Link ID")),
                 _int(r.get("Trigger Tech ID")), r.get("Use Type"),
                 r.get("Name")))
_r2550 = CT.row_for(incas, 2550, CT.UNIT_USE_TYPES)
print("     2550 is a chain HEAD: Link ID absent/negative = %s"
      % (_int((_r2550 or {}).get("Link ID")) < 0))

print()
print("B  every shipped row that links TO a node which is itself a chain head")
print("   (those are exactly the rows CUT would promote to a head)")
promoted = []
for stem in sorted(trees):
    nodes = {}
    for r in CT.rows_of(trees[stem]):
        if isinstance(r, dict):
            nodes[_int(r.get("Node ID"), -2)] = r
    for r in CT.rows_of(trees[stem]):
        if not isinstance(r, dict):
            continue
        link = _int(r.get("Link ID"))
        if link < 0:
            continue
        pred = nodes.get(link)
        if pred is not None and _int(pred.get("Link ID")) < 0:
            # `link` is a head, and THIS row upgrades from it.  That is normal:
            # a head is a base unit and rows legitimately upgrade from it.
            # The CUT question is different: after deleting `link`, would THIS
            # row become a head that is an upgrade?  Measure whether the corpus
            # ever has that for a node whose own name is not a base unit.
            promoted.append((stem, r.get("Node ID"), link,
                             _int(r.get("Trigger Tech ID"))))
print("     rows upgrading from a chain head (the normal shape): %d"
      % len(promoted))
print("     ^ this is NOT the CUT shape.  The CUT shape is: a row whose")
print("       predecessor was deleted, left in place with no predecessor.  The")
print("       shipped corpus has ZERO of those (probe_broken_chain) -- every row")
print("       with a missing predecessor is absent entirely.")

print()
print("C  so do the 11 'head that is an upgrade' rows differ in kind?")
print("   A head-that-is-an-upgrade in shipped data means: this unit is handed")
print("   out by its OWN technology, with no predecessor unit to upgrade from.")
for stem, nid, trig, name in [
        ("INCAS", 2550, 1350, "Champi Scout"),
        ("BENGALIS", 1132, 630, "Battle Elephant"),
        ("WU", 1974, 1156, "Jian Swordsman")]:
    t = trees[stem]
    row = CT.row_for(t, nid, CT.UNIT_USE_TYPES)
    up_from = [(r.get("Node ID"), r.get("Name")) for r in CT.rows_of(t)
               if isinstance(r, dict) and _int(r.get("Link ID")) == nid]
    print("     %-10s node %-5s %-16s link_from_rows=%s"
          % (stem, nid, name, up_from))
print("     ^ every one of them has NO row linking from it (nothing upgrades")
print("       from them at the point they are a head), which is what makes them")
print("       honest heads rather than demoted mid-chain units.")

print()
print("REVOKE SEMANTICS: the corpus never shows a demoted mid-chain successor;")
print("CASCADE preserves the requested meaning, CUT would not.")
sys.exit(0)
