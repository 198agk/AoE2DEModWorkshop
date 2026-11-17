# -*- coding: utf-8 -*-
r"""PIN: `revoke` must leave a chain-closed tree, and the corpus says what closes it.

## The defect this pin guards

`dsh test v9` revoked unit 2550 from the Incas.  `CT.revoke` deleted the row and
left the file with a row whose `Link ID` still said 2550 -- a state NO shipped tree
file contains.  That single fact is why the v9 in-game observation is marked
PROVISIONAL instead of being the answer to "does the build menu read the tree":
the game may have rejected the tree and fallen back to the `.dat` default tree.

It is a PRODUCT defect too, not just a broken experiment: `unit.availability` with
action `revoke` ships exactly that state.

## What the corpus says (measured, `_probe/probe_broken_chain.py` / `probe_chain_head.py`)

  * 62 shipped files, 3,686 unit rows, 1,917 with a predecessor:
    0 dangling `Link ID`s, 0 "successor present while predecessor absent" pairs.
    The corpus is strictly chain-closed.
  * 11 rows are chain HEADS that are nevertheless upgrades (INCAS 2550 Champi
    Scout, BENGALIS 1132 Battle Elephant, WU 1974 Jian Swordsman ...), so a head IS
    allowed to be an upgrade.  That rules out "a head that is an upgrade never
    ships" as the reason to reject CUT.
  * The reason CUT is still wrong is different and stronger: **every one of the 62
    shipped files is closed, so a successor with a MISSING predecessor never occurs
    at all.**  Promoting a successor to a head would hand the game a row that
    upgrades from nothing -- a row the corpus has no instance of -- and, worse, it
    would make the successor obtainable WITHOUT the thing the caller asked to
    revoke.  CASCADE is the only repair that preserves the request's meaning.

## The fix this pin demands

`revoke(tree, node_id)` deletes the row AND every row whose chain reaches the
deleted node, until closed.  It returns the number of rows removed, as before, and
a new `revoked_ids` is available to callers that must report what went.

Run:  python _probe\test_revoke_chain_closed.py
"""
import copy
import _gamepaths as GP
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def _int(v, default=-1):
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def dangling(tree):
    """Delegates to the module so the pin tests the shipped invariant, not a copy."""
    return CT.dangling_links(tree)


print("A  the shipped baseline is chain-closed (the state revoke must reproduce)")
_clean = 0
for stem in sorted(CT.load_trees(GAME)):
    pass
trees = CT.load_trees(GAME)
for stem in sorted(trees):
    if not dangling(trees[stem]):
        _clean += 1
check("all 62 shipped files carry ZERO dangling Link ID",
      _clean == len(trees), "%d of %d clean" % (_clean, len(trees)))

print()
print("B  revoke is chain-closed -- the v9 failure mode cannot come back")
_incas = copy.deepcopy(trees["INCAS"])
assert CT.row_for(_incas, 2550, CT.UNIT_USE_TYPES) is not None
assert CT.row_for(_incas, 2588, CT.UNIT_USE_TYPES) is not None, \
    "expected the Champi Runner to be present before the revoke"
_removed = CT.revoke(_incas, 2550)
check("revoking INCAS 2550 also removes its successor 2588",
      CT.row_for(_incas, 2588, CT.UNIT_USE_TYPES) is None,
      "2588 still present -- the successor was promoted, not removed")
check("the result has NO dangling Link ID",
      not dangling(_incas), dangling(_incas)[:3])
check("revoke reports how many rows it removed", _removed >= 2,
      "removed=%r" % (_removed,))
check("a second revoke of the same node removes nothing more",
      CT.revoke(_incas, 2550) == 0)

print()
print("C  every (civ, revocable node) in the corpus, revoke and re-close")
_worst = []
_checked = 0
for stem in sorted(trees):
    t = copy.deepcopy(trees[stem])
    nodes = [_int(r.get("Node ID")) for r in CT.rows_of(t)
             if isinstance(r, dict) and r.get("Use Type") in CT.UNIT_USE_TYPES
             and _int(r.get("Node ID")) >= 0]
    for nid in nodes:
        if CT.row_for(t, nid, CT.UNIT_USE_TYPES) is None:
            continue
        CT.revoke(t, nid)
        _checked += 1
        d = dangling(t)
        if d:
            _worst.append((stem, nid, d[:2]))
check("revoking ANY unit node from ANY civ leaves the file chain-closed",
      not _worst,
      "%d failures, e.g. %s" % (len(_worst), _worst[:3]))
print("     (%d revocations tested)" % _checked)

print()
print("D  revoke must not touch rows it was not asked about")
_b = copy.deepcopy(trees["BRITONS"])
_before = {_int(r.get("Node ID")) for r in CT.rows_of(_b) if isinstance(r, dict)}
CT.revoke(_b, 41)             # a unit the Britons have
_after = {_int(r.get("Node ID")) for r in CT.rows_of(_b) if isinstance(r, dict)}
check("a revoke only ever removes rows, never adds one",
      _after <= _before, "added=%s" % (_after - _before))
check("the revoked node itself is gone", 41 not in _after)

print()
print("REVOKE CHAIN CLOSED: %d revocations over %d files, %d failures"
      % (_checked, len(trees), len(_worst)))
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
