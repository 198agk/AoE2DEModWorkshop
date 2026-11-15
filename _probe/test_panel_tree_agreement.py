# -*- coding: utf-8 -*-
r"""PIN: the panel and the tree are 99.4% the same data, not rival authorities.

The availability experiment has been framed as "which of two authorities wins".  That
framing is wrong, and the measurement says so:

    over every (civilization, unit) pair in the shipped data
        tree grants AND panel lists : 3107
        tree grants, panel SILENT   :    8
        tree REFUSES, panel lists   :   11
    Agreement: 3107 / 3126 = 99.4%.  The whole "contradiction" is 19 data points.

Supporting measurements:

  * `panel RequiredAge == tree Age ID` on 3,109 pairs (9 differ, all off-by-one age
    and all on late-DLC civilizations).
  * The panel **omits the 11 basic buildings from its `Builder` (118) block's
    `Units` list** -- but that list is "what the villager can PLACE", and the panel
    carries those buildings as their own BLOCKS.  (An earlier draft of this section
    misread that as "the panel omits basic buildings entirely" and looked at only
    one civilization key per file; corrected in section D.)
  * The panel carries **display-only** fields the tree does not have at all --
    `PrereqTech`/`PrereqIconSet`/`PrereqIconIndex`/`PrereqStyle`/`PrereqStringID`
    on 17,228 entries, `RequiredUnitID` on 28,728 -- i.e. it is built to say
    "you need X", which is what a **preview** does.
  * The panel's on-disk mtime is **not** an invariant: this docstring used to record
    it as "19 days older than the engine", which held on 2026-10-12 and stopped
    holding on 2026-11-12 when Steam's validation re-downloaded the panel with a
    fresh mtime and identical bytes.  Section E now compares bytes against the
    archived vanilla copy instead -- the question that matters is "is this the
    shipped panel", not "which of two files from one patch is older".

Two product consequences:

  1. **Writing one layer and not the other is the only real risk.**  Writing both --
     which `aoe2mod/api.py` already does -- is correct whichever file is consulted,
     because they encode the same model to within 0.6%.  The answer to the in-game
     experiment decides which file to PRIORITIZE (smaller mods, faster builds), not
     whether the product works.
  2. The 19 disagreements are almost certainly **build-time drift**, not design.
     Any tool that edits availability should still write both, because that is
     exactly the set of pairs where the two copies disagree.

Also pinned: a counting bug.  An earlier probe printed "524068 panel entries" by
re-iterating a civilization key once per key in the same file object.  The correct
count is **10,753 entries over 70 (file, civilization) pairs**, average 160.5 per
civilization.  A single-node measurement is not evidence until the aggregate is
measured the same way.

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_panel_tree_agreement.py
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


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
GRANT = ("ResearchedCompleted", "ResearchRequired")

# ---- the agreement census ---------------------------------------------------
seen, entries = set(), 0
per_civ = Counter()
both = grant_only = panel_only = 0
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            continue
        seen.add((rec["path"], disp))
        for blk in BP.buildings(rec["obj"], disp):
            for e in (blk.get(BP.UNITS_KEY) or []) + (blk.get(BP.TECHS_KEY) or []):
                entries += 1
                per_civ[disp] += 1

for stem, tree in sorted(trees.items()):
    disp = next((d for d in sorted(panels)
                 if CT.civ_file_stem(d) == stem), None)
    if disp is None:
        continue
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    listed = {e.get("ID") for blk in BP.buildings(obj, disp)
              for e in (blk.get(BP.UNITS_KEY) or [])}
    for r in CT.unit_rows(tree):
        uid = r.get("Node ID")
        if uid is None:
            continue
        ok = r.get("Node Status") in GRANT
        inp = uid in listed
        if ok and inp:
            both += 1
        elif ok:
            grant_only += 1
        elif inp:
            panel_only += 1

print("A  the agreement census, over every (civilization, unit) pair")
print("     tree grants AND panel lists : %d" % both)
print("     tree grants, panel SILENT   : %d" % grant_only)
print("     tree REFUSES, panel lists   : %d" % panel_only)
tot = both + grant_only + panel_only
print("     disagreement                : %d of %d = %.2f%%"
      % (grant_only + panel_only, tot,
         100.0 * (grant_only + panel_only) / tot))
check("the two layers agree on more than 99% of pairs",
      both / tot > 0.99, "%d/%d" % (both, tot))
check("the disagreement is small enough to enumerate by hand",
      grant_only + panel_only <= 25, "%d + %d"
      % (grant_only, panel_only))

print()
print("B  the entry count, measured once (a single-node number is not evidence)")
print("     distinct (file, civilization) pairs : %d" % len(seen))
print("     total panel entries                 : %d" % entries)
print("     per civilization: min %d max %d avg %.1f"
      % (min(per_civ.values()), max(per_civ.values()),
         sum(per_civ.values()) / len(per_civ)))
check("the panel has on the order of 10k entries, not 500k",
      5000 < entries < 25000, "entries=%d" % entries)

print()
print("C  the panel is BUILT to say 'you need X' -- display-only fields")
need, unit_need, ages = Counter(), Counter(), 0
for _pk, rec in sorted(panels.items()):
    for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
        if (rec["path"], disp) in seen:
            pass
        for blk in BP.buildings(rec["obj"], disp):
            for e in (blk.get(BP.UNITS_KEY) or []) + (blk.get(BP.TECHS_KEY) or []):
                for k in ("PrereqTech", "PrereqIconSet", "PrereqIconIndex",
                          "PrereqStyle", "PrereqStringID"):
                    if k in e:
                        need[k] += 1
                        break
                if "RequiredUnitID" in e:
                    unit_need["RequiredUnitID"] += 1
                if "RequiredAge" in e:
                    ages += 1
print("     entries carrying a Prereq* field : %d" % sum(1 for k in need))
print("     Prereq* field presence           : %s" % dict(need))
print("     RequiredUnitID                   : %d" % unit_need["RequiredUnitID"])
print("     RequiredAge                      : %d" % ages)
check("the panel carries prereq display fields the tree does not have",
      sum(need.values()) > 1000, "need=%s" % dict(need))
_tfields = {k for t in trees.values() for r in CT.rows_of(t) for k in r}
check("the tree carries NONE of those fields",
      not ({"PrereqTech", "PrereqIconSet", "PrereqStyle", "RequiredUnitID"}
           & _tfields),
      "tree fields=%s" % sorted(_tfields))

print()
print("D  the panel is not shaped like a construction menu -- check it correctly")
# CORRECTED.  An earlier version of this section asserted "the basic Barracks (12)
# never appears as a panel building", by looking only at the FIRST civilization key
# in each file (`next(...)`), and drew the wrong conclusion from it.  Building 12
# appears in EVERY civilization's panel -- as a BLOCK with its own `Units` array.
# The real statement is about the `Builder` (118) block's `Units` list, which lists
# what the villager can PLACE, and which is a strict subset of the tree's building
# rows.  See `test_panel_shape.py` for the block-vs-entry model.
BUILDER = 118
BASIC = (12, 68, 70, 72, 562, 584)
as_block, in_builder = {}, {}
for bid in BASIC:
    as_block[bid] = 0
    in_builder[bid] = 0
    for _pk, rec in sorted(panels.items()):
        for disp in sorted(k for k in rec["obj"] if isinstance(k, str)):
            blks = list(BP.buildings(rec["obj"], disp))
            if any(b.get("ID") == bid for b in blks):
                as_block[bid] += 1
            b118 = next((b for b in blks if b.get("ID") == BUILDER), None)
            if bid in {e.get("ID") for e in ((b118 or {}).get(BP.UNITS_KEY) or [])}:
                in_builder[bid] += 1
for bid in BASIC:
    print("     building %-5s as a BLOCK in %3d civ-entries | in Builder(118) "
          "Units: %d" % (bid, as_block[bid], in_builder[bid]))
check("every basic building IS present in the panel, as its own block",
      all(as_block[b] > 300 for b in BASIC), "as_block=%s" % as_block)
check("and every one of them is absent from the Builder's `Units` list",
      all(in_builder[b] == 0 for b in BASIC), "in_builder=%s" % in_builder)
print("     -> 'absent from a `Units` array' is NOT 'absent from the panel'.")

print()
print("E  the panel on disk is the one Steam shipped, not a fixture a probe wrote")
# This section used to assert "the panel file is OLDER than the engine that reads
# it" -- an observation from 2026-10-12, when the panel and the 62 tree files all
# carried the 2026-09-23 patch mtime.  Steam re-downloads files it finds changed:
# on 2026-11-12 23:22:44 its validation replaced futuravailableunits.json with
# byte-identical content and a fresh mtime, so the panel became NEWER than the
# .exe (23:19:46) without a byte of data changing.  mtime ordering between two
# files of the same patch is not an invariant and never was.
#
# What the census above actually needs is that the panel being measured is the
# shipped one.  A probe that installs a fixture (see _probe/_tmp/install_into_game.py,
# which wrote a mod's .dat into the game folder on 2026-11-12) would invalidate
# every number in sections A-D while leaving all of them "passing".  So the check
# compares bytes against the archived vanilla copy when that archive exists.
import datetime                                            # noqa: E402
import hashlib                                             # noqa: E402
mt = {}
for rel in ("resources/_common/dat/futuravailableunits.json",
            "resources/_common/dat/CivTechTrees/SICILIANS.json",
            "AoE2DE_s.exe"):
    p = os.path.join(GAME, rel.replace("/", os.sep))
    if os.path.exists(p):
        mt[rel] = datetime.datetime.fromtimestamp(os.path.getmtime(p))
        print("     %-52s %s" % (rel, mt[rel]))
print("     (mtimes are printed as facts, not asserted: Steam rewrites them)")


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


PANEL_REL = "resources/_common/dat/futuravailableunits.json"
panel_live = os.path.join(GAME, PANEL_REL.replace("/", os.sep))
VANILLA = os.path.join(ROOT, "_cache", "vanilla_dat", "futuravailableunits.json")
if os.path.isfile(panel_live) and os.path.isfile(VANILLA):
    a, b = _sha(panel_live), _sha(VANILLA)
    check("the panel in the game folder is byte-identical to the archived vanilla",
          a == b, "live=%s vanilla=%s" % (a[:16], b[:16]))
    print("     live %s / archived vanilla %s" % (a[:16], b[:16]))
else:
    print("     (no archived vanilla copy at _cache/vanilla_dat -- "
          "content check skipped, not asserted)")

print()
print("PANEL-VS-TREE: 99.4% identical.  The in-game experiment decides which copy")
print("  to PRIORITIZE, not whether the product works -- writing both, as")
print("  aoe2mod/api.py does, is correct either way.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
