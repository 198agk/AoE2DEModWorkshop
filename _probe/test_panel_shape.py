# -*- coding: utf-8 -*-
r"""PIN: the panel's shape -- blocks are places, entries are what they produce.

An earlier suite (`test_panel_is_not_build_menu.py`) claimed:

    "each basic building appears in ZERO civs' panels"
    "the panel is a DIFFERENT model from the tree -- it omits buildings every
     civilization can certainly build"

**That is a misreading and this pin corrects it.**  Building 12 (Barracks) is in the
Britons panel -- as a **BLOCK with its own `Units` array**:

    BP.buildings(obj, "Britons") -> [(118,'Builder'), (13,'Fishing Ship'),
        (87,'Archery Range'), (12,'Barracks'), (101,'Stable'), ...]

What was measured is that 12 is absent from the **`Builder` (118) block's `Units`
list** -- because the Barracks is not something the *Builder* manufactures, it is
itself a *container*.  The panel has two kinds of building reference:

    a BLOCK  (an object with ID/Name/Units/Techs)   <- somewhere you can produce
    an ENTRY inside a block's `Units`               <- something produced there

Measured shape (62 civilizations):

  * **27-32 blocks per civilization**; every civ has the `Builder` (118) block.
  * The basics ARE there as their own blocks: **Barracks 62/62, House 62/62,
    Palisade Wall 62/62, Mill 58, Dock 56, Lumber Camp 56, Mining Camp 56**.
  * **434** (basic building x civ) pairs are absent from *every* `Units` list and
    still present as blocks.  That is why the two statements can both be printed:
    a `Units` array is "what this building produces"; a block is "a place you can
    produce".

Two honest complications, both measured rather than assumed:

  * **The `Builder` block's `Units` list is NOT always a subset of the tree's
    `Use Type: Building` rows.**  It breaks for **7 civilizations**, and the extras
    are tree **`Unit`** rows (2552 Champi Warrior for the five American civs, 104
    for ARMENIANS/GEORGIANS, who have no Temple *building* row).  So the tree
    references a place under more than one `Use Type`.
  * **The panel has 134 (civ, block) pairs whose block id is not a tree Building
    row**, and there are FOUR distinct reasons:
        `118`  in 62 civs -- a **pseudo-block**, the villager menu category
        `13`   in 62 civs -- the tree carries it as **Unit**/**Tech** rows
        `2171` in  6 civs -- absent from the tree entirely
        `104`  in  2 civs -- ARMENIANS/GEORGIANS: absent (their temple is 1806)
        `2414` in  1 civ  -- absent from the tree entirely
        `68`   in  1 civ  -- POLES: the tree carries it as a **Tech** row

    So "the panel has a block the tree's Building rows lack" is not one phenomenon.

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_panel_shape.py
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []
BUILDER = 118
BASICS = {12: "Barracks", 70: "House", 68: "Mill", 562: "Lumber Camp",
          584: "Mining Camp", 72: "Palisade Wall", 45: "Dock"}


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

civs = {}
seen = set()
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        stem = CT.civ_file_stem(disp)
        if stem in trees:
            civs[stem] = (disp, rec["obj"])

blk_counts = {s: {b.get("ID") for b in BP.buildings(o, d)}
              for s, (d, o) in civs.items()}
tbuild = {s: {r.get("Node ID") for r in CT.rows_of(trees[s])
              if r.get("Use Type") == "Building"} for s in civs}

check("the census covered the civilizations", len(civs) >= 60,
      "only %d" % len(civs))

print()
print("A  blocks per civilization")
cnt = Counter(len(v) for v in blk_counts.values())
print("     %s" % dict(cnt))
check("every civ has 25-35 building blocks",
      all(25 <= len(v) <= 35 for v in blk_counts.values()), "counts=%s" % dict(cnt))
check("every civ has a Builder (118) block",
      all(BUILDER in v for v in blk_counts.values()))

print()
print("B  the correction: the basics ARE in the panel, as their own blocks")
for bid, nm in sorted(BASICS.items()):
    have = sum(1 for v in blk_counts.values() if bid in v)
    print("     %-16s present as a BLOCK in %2d of %d civs"
          % (nm, have, len(civs)))
check("every basic building is a block in the great majority of civs",
      all(sum(1 for v in blk_counts.values() if b in v) >= 50 for b in BASICS),
      "counts=%s" % {b: sum(1 for v in blk_counts.values() if b in v)
                     for b in BASICS})
check("the Barracks is a block in EVERY civilization (the earlier claim was a "
      "misreading of its absence from Builder's Units)",
      all(12 in v for v in blk_counts.values()))

print()
print("C  what the earlier probe measured: absence from the Builder's Units list")
_missing = sum(1 for s, (d, o) in civs.items() for bid in BASICS
               if bid not in {e.get("ID") for b in BP.buildings(o, d)
                              for e in (b.get(BP.UNITS_KEY) or [])})
print("     (basic building x civ) pairs absent from every Units list: %d" % _missing)
check("that number is large, yet each of those buildings is present as a block",
      _missing > 300)
print("     => 'absent from a `Units` array' and 'absent from the panel' are")
print("        statements about DIFFERENT things.")

print()
print("D  honest complication 1: Builder's Units is not always a tree-Building subset")
bad = {}
for stem, (disp, obj) in civs.items():
    blk = next((b for b in BP.buildings(obj, disp) if b.get("ID") == BUILDER), None)
    us = {e.get("ID") for e in ((blk or {}).get(BP.UNITS_KEY) or [])}
    extra = us - tbuild[stem]
    if extra:
        bad[stem] = sorted(extra)
print("     civs whose Builder Units escape the tree's Building rows: %d" % len(bad))
_nother, _absent = 0, 0
for s, ex in sorted(bad.items()):
    kinds = {}
    for uid in ex:
        rows = [r for r in CT.rows_of(trees[s]) if r.get("Node ID") == uid]
        kinds[uid] = sorted({r.get("Use Type") for r in rows}) or ["ABSENT"]
    print("        %-13s %s" % (s, kinds))
    for uid in ex:
        if any(r.get("Node ID") == uid for r in CT.rows_of(trees[s])):
            _nother += 1
        else:
            _absent += 1
check("the extras are a MIX: carried under another Use Type, or absent entirely",
      _nother > 0 and _absent > 0,
      "another-use-type=%d absent=%d" % (_nother, _absent))
print("        -> %d are carried by the tree under a different Use Type, and %d"
      % (_nother, _absent))
print("           are not in the tree at all.  The Builder's Units list is")
print("           therefore NOT a subset of the tree's Building rows, in two")
print("           different ways.")

print()
print("E  honest complication 2: panel-only block ids have FOUR distinct reasons")
only = {}
for stem, (disp, obj) in civs.items():
    for b in BP.buildings(obj, disp):
        if b.get("ID") not in tbuild[stem]:
            only.setdefault(b.get("ID"), set()).add(stem)
for bid in sorted(only, key=lambda x: -len(only[x])):
    stems = sorted(only[bid])
    anyrow = any(r.get("Node ID") == bid for t in trees.values()
                 for r in CT.rows_of(t))
    print("     block %-6s in %2d civs   appears in some tree (any Use Type): %s"
          % (bid, len(stems), anyrow))
check("more than one reason exists for a panel-only block",
      len(only) >= 4, "ids=%s" % sorted(only))
check("the Builder (118) is among them -- it is a menu category, not a place",
      BUILDER in only and len(only[BUILDER]) >= 60)
check("at least one panel-only block id appears in no tree at all",
      any(not any(r.get("Node ID") == bid for t in trees.values()
                  for r in CT.rows_of(t)) for bid in only),
      "ids=%s" % sorted(only))

print()
print("F  the shape of the building-table overlap")
both = sum(len(tbuild[s] & blk_counts[s]) for s in civs)
ot = sum(len(tbuild[s] - blk_counts[s]) for s in civs)
op = sum(len(blk_counts[s] - tbuild[s]) for s in civs)
print("     (civ, building) pairs in BOTH : %d" % both)
print("     tree only                     : %d" % ot)
print("     panel only                    : %d" % op)
check("the panel's blocks are overwhelmingly the tree's building rows",
      both > 10 * max(ot, op), "both=%d tree=%d panel=%d" % (both, ot, op))

print()
print("PANEL SHAPE: a block is a place you can produce; an entry inside it is what")
print("  it produces.  Building 12 is a block, so 'not in Builder's Units' says")
print("  nothing about whether the panel knows the Barracks exists.")
print("  And 'panel-only block' has four different causes -- do not treat it as one.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
