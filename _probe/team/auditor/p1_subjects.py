# -*- coding: utf-8 -*-
"""Audit probe 1: the two subjects, read straight from the shipped game files."""
import os, sys, json
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import aoe2mod.api as A
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CIV = "Britons"
STEM = "BRITONS"
HDR = "=" * 78


def p(*a):
    print(*a)


tk = A.open_toolkit()
trees = CT.load_trees(GAME)
brit = trees[STEM]
panels = BP.load_all(GAME)
pkey = BP.panel_path_for(GAME, CIV)[1]
pobj = panels[pkey]["obj"]
kb = BP.civ_key_for(panels, CIV)
p(HDR); p("0. identity"); p(HDR)
p("  game_root toolkit : %r" % tk.game_root)
p("  panel file key    : %r   civ cache key : %r" % (pkey, kb))
p("  panel file path   : %s" % panels[pkey]["path"])
p("  panel civ keys    : %d" % len(pobj))
p()

for U in (2550, 74):
    donor, dro = CT.donor_row(trees, U, CT.UNIT_USE_TYPES)
    p(HDR); p("unit %d" % U); p(HDR)
    p("  tree donor civ    : %r" % donor)
    p("  tree donor row    : %s" % json.dumps(dro, ensure_ascii=False, sort_keys=True))
    p("  brit has row      : %r" % (CT.row_for(brit, U) is not None))
    p("  brit node_status  : %r" % CT.node_status(brit, U, CT.UNIT_USE_TYPES))
    p("  brit can_build    : %r" % CT.can_build(brit, U, CT.UNIT_USE_TYPES))
    # panel side: where ANY civ lists it
    ents = BP.entries_of(pobj, U, BP.UNITS_KEY)
    p("  panel civs listing it (main file): %d" % len(ents))
    for c, b, e in ents[:6]:
        p("      civ=%-14s bldg=%-5s entry=%s" % (c, b, json.dumps(e, ensure_ascii=False)))
    b74, e74 = BP.find_entry(pobj, kb, U, BP.UNITS_KEY)
    p("  panel entry for %s: bldg=%r entry=%s"
      % (kb, b74, json.dumps(e74, ensure_ascii=False) if e74 else None))
    p()

p(HDR); p("1. Britons' Barracks (12) across ALL THREE panel/space sources"); p(HDR)
for space in (BP.UNITS_KEY, BP.TECHS_KEY):
    blds = BP.buildings(pobj, kb)
    p("  %s: civ block has %d building objects; ids=%s"
      % (space, len(blds), sorted(b.get("ID") for b in blds)))
b12 = BP.building_block(pobj, kb, 12)
p("  barracks block keys: %s" % sorted(b12.keys()) if b12 else "  NONE")
u12 = BP.entries(pobj, kb, 12, BP.UNITS_KEY)
p("  barracks UNIT entries: %d" % len(u12))
for e in u12:
    p("      %s" % json.dumps(e, ensure_ascii=False))
p("  barracks TECH entries: %d" % len(BP.entries(pobj, kb, 12, BP.TECHS_KEY)))
p()

p(HDR); p("2. the panel pair: does paphos also carry a Britons key?"); p(HDR)
mp, pp = BP.panel_paths(GAME)
p("  main   : %s" % os.path.basename(mp))
p("  paphos : %s" % os.path.basename(pp))
_t, po = BP.load_panel(pp)
p("  paphos has 'Britons': %r" % ("Britons" in po))
p("  paphos civ keys (%d): %s" % (len(po), sorted(po)[:80]))
p()

p(HDR); p("3. other per-civ availability files"); p(HDR)
dd = os.path.join(GAME, "resources", "_common", "dat")
for name in ("civilizations.json", "linkedUnits.json", "unitlines.json",
             "linkedTechs.json", "sharedbuildings.json", "unitcategories.json"):
    fp = os.path.join(dd, name)
    if os.path.isfile(fp):
        j = json.load(open(fp, encoding="utf-8-sig"))
        top = list(j)[:12] if isinstance(j, dict) else "list[%d]" % len(j)
        p("  %-24s %8d B  top-level: %s" % (name, os.path.getsize(fp), top))
