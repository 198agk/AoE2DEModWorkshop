# -*- coding: utf-8 -*-
"""smoke5: the DISCRIMINATING experiment -- tree and panel moved OPPOSITE ways.

Every earlier in-game test moved both halves in the same direction, so a hit
could not be attributed to either file and a miss could be explained away by the
age gate.  This one puts TWO buttons on the SAME Dark-Age screen (Britons'
Barracks, id 12) and changes the two layers in opposite directions:

  A  Champi Scout (unit 2550): added to the TREE, NOT added to the panel
     -> a new button proves the menu comes from the tree file.

  B  Militia (unit 74): removed from the PANEL, left alone in the TREE
     -> a missing button proves the menu comes from the panel file.

  C  Villager 1000 HP in the .dat: the positive control.  It proves the mod
     loaded at all -- without it, "nothing appeared" is indistinguishable from
     "the mod never loaded".

Reading (one Dark-Age Britons game is enough):

  Champi present + Militia present  -> the menu is driven by the TREE
  Champi absent  + Militia absent   -> the menu is driven by the PANEL
  Champi present + Militia absent   -> both layers are consulted
  Champi absent  + Militia present  -> neither file drives the menu, or the mod
                                       did not load -- check the Villager HP first

Writes only into `_probe\\out_smoke5\\`.  Installing is a separate step.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

OUT = os.path.join(HERE, "out_smoke5")
TITLE = "aoe2mod Smoke5 TreeVsPanel"
CIV = "Britons"
STEM = "BRITONS"
BLD = 12                     # Barracks
TREE_ONLY = 2550             # Champi Scout -- tree gets it, panel must not
PANEL_ONLY = 74              # Militia      -- panel loses it, tree must not

CONTROL = {"intent": "unit.stat", "unit": "Villager",
           "stat": "hit_points", "value": 1000}
DESC = ("Tests which file drives the build menu. Barracks should show Champi "
        "Scout if the tree file is read; Militia should be MISSING if the panel "
        "file is read. Villager HP 1000 is the control that the mod loaded.")


def head(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


head("0  the subjects are clean, measured against the GAME's own files")
tk = A.open_toolkit()
trees = CT.load_trees(tk.game_root)
brit = trees[STEM]
panels = BP.load_all(tk.game_root)
pkey = BP.panel_path_for(tk.game_root, CIV)[1]
pobj = panels[pkey]["obj"]
kb = BP.civ_key_for(panels, CIV)
print("  tree stem %s / panel file key %r / civ cache key %r" % (STEM, pkey, kb))

# --- subject A: a tree grant the panel will NOT be told about ---------------
donor_civ, dro = CT.donor_row(trees, TREE_ONLY, CT.UNIT_USE_TYPES)
print()
print("  A tree-only  : unit %d, donor %s, row %r" % (TREE_ONLY, donor_civ, dro))
assert dro.get("Age ID") == 1, "subject A carries an age gate: %r" % dro
assert dro.get("Building ID") == BLD, "subject A is not a barracks unit"
assert CT.row_for(brit, TREE_ONLY) is None, "Britons already has it (no change)"
_br, _be = BP.find_entry(pobj, kb, TREE_ONLY, BP.UNITS_KEY)
assert _be is None, "the panel already lists it -- the claim gets muddy: %r" % _be

# --- subject B: a panel removal the tree will NOT be told about -------------
_b74, _e74 = BP.find_entry(pobj, kb, PANEL_ONLY, BP.UNITS_KEY)
print("  B panel-only : unit %d, panel entry at building %r: %r"
      % (PANEL_ONLY, _b74, _e74))
assert _e74 is not None, "the panel does not list Militia for Britons?"
assert _b74 == BLD, "subject B is not in the barracks array we expect"
assert _e74.get("RequiredAge") == 1, "subject B is age-gated in the panel"
assert CT.node_status(brit, PANEL_ONLY, CT.UNIT_USE_TYPES) == "ResearchedCompleted", \
    "the tree does not say Britons can build it -- then the pair does not isolate"

head("1  the .dat half (the positive control), through the public API")
man = tk.build(CONTROL, OUT, title=TITLE, author="aoe2mod probe",
               description=DESC, overwrite=True)
print("  dat: %d B" % os.path.getsize(
    os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")))

head("2  the tree half: grant %d, panel untouched" % TREE_ONLY)
_edited = json.loads(json.dumps(brit, ensure_ascii=False))
_edited.pop("path", None)
_row, _warn = CT.grant(_edited, TREE_ONLY, dro)
_tree_rel = os.path.join(CT.CIVTECHTREES_REL, "%s.json" % STEM)
_tree_abs = os.path.join(OUT, _tree_rel)
os.makedirs(os.path.dirname(_tree_abs), exist_ok=True)
with open(_tree_abs, "wb") as fh:
    fh.write(CT.serialize(_edited))
print("  wrote %s  (%d B)" % (_tree_rel, os.path.getsize(_tree_abs)))
print("  row after grant: %r" % (CT.row_for(_edited, TREE_ONLY),))
if _warn:
    print("  warnings: %d" % len(_warn))

head("3  the panel half: remove %d, tree untouched" % PANEL_ONLY)
_ptext = os.path.join(tk.game_root, BP.PANEL_REL)
with open(_ptext, "rb") as fh:
    _raw = fh.read()
_txt = _raw.decode("utf-8-sig")
_new, _removed = BP.remove_entry(_txt, kb, PANEL_ONLY, BP.UNITS_KEY)
print("  entries removed: %d" % _removed)
assert _removed >= 1, "nothing was removed -- the panel edit is a no-op"
_panel_abs = os.path.join(OUT, BP.PANEL_REL)
os.makedirs(os.path.dirname(_panel_abs), exist_ok=True)
with open(_panel_abs, "wb") as fh:
    fh.write(BP.serialize_bytes(_new))
print("  wrote %s  (%d B, was %d B)"
      % (BP.PANEL_REL, os.path.getsize(_panel_abs), len(_raw)))

head("4  read the artifact back off disk -- not the report")
for dirpath, _d, files in os.walk(OUT):
    for f in sorted(files):
        fp = os.path.join(dirpath, f)
        print("    %-58s %10d B" % (os.path.relpath(fp, OUT),
                                    os.path.getsize(fp)))

_t = CT.load_trees(OUT)[STEM]
print()
print("  TREE  says Britons can build %d : %s"
      % (TREE_ONLY, CT.can_build(_t, TREE_ONLY)))
print("  TREE  still has %d               : %s"
      % (PANEL_ONLY, CT.row_for(_t, PANEL_ONLY) is not None))
assert CT.can_build(_t, TREE_ONLY) and CT.row_for(_t, PANEL_ONLY) is not None

_pt, _po = BP.load_panel(_panel_abs)
_pk = BP.panel_path_for(OUT, CIV)[1]
print("  PANEL lists %d                   : %s"
      % (TREE_ONLY, BP.find_entry(_po, _pk, TREE_ONLY, BP.UNITS_KEY)[1] is not None))
print("  PANEL lists %d                   : %s"
      % (PANEL_ONLY, BP.find_entry(_po, _pk, PANEL_ONLY, BP.UNITS_KEY)[1] is not None))
print("  PANEL barracks entries: %d  (shipped had %d)"
      % (len(BP.entries(_po, _pk, BLD, BP.UNITS_KEY)),
         len(BP.entries(pobj, kb, BLD, BP.UNITS_KEY))))
assert BP.find_entry(_po, _pk, TREE_ONLY, BP.UNITS_KEY)[1] is None
assert BP.find_entry(_po, _pk, PANEL_ONLY, BP.UNITS_KEY)[1] is None
# The other civs must not have been disturbed.  WHICH civs to check is measured,
# not assumed: Incas is Mesoamerican and never listed Militia in the first place,
# so asserting on it by hand tests the panel for a row it never had and calls the
# product broken for a reason that does not exist.
_controls = []
for _c in sorted(panels[pkey]["obj"]):
    if _c == kb or not isinstance(_c, str):
        continue
    _k = BP.panel_path_for(OUT, _c)[1]
    if BP.find_entry(pobj, _c, PANEL_ONLY, BP.UNITS_KEY)[1] is not None:
        _controls.append((_c, _k))
print("  civs that shipped a Militia row (measured): %d  e.g. %s"
      % (len(_controls), [c for c, _ in _controls[:4]]))
assert _controls, "no civ in the shipped panel lists Militia?!"
for _c, _k in _controls:
    assert BP.find_entry(_po, _k, PANEL_ONLY, BP.UNITS_KEY)[1] is not None, \
        "%s lost its Militia -- the edit leaked across civs" % _c
print("  all %d of them still list %d : True" % (len(_controls), PANEL_ONLY))

head("5  what the user must look at")
print("  one Britons game, Dark Age, the Barracks (id %d):" % BLD)
print("    - a '%s' button?     -> the TREE file drives the menu"
      % dro.get("Name", "Champi Scout"))
print("    - a Militia button?          -> the PANEL file drives the menu")
print("  control: Villager HP must read 1000, or the mod did not load.")
print()
print("SMOKE5 BUILT (both halves in one mod, moved in opposite directions).")
