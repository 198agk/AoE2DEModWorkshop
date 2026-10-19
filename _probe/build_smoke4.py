# -*- coding: utf-8 -*-
"""Build the CONFOUND-FREE single-variable smoke mod.

The 2026-10-14 in-game test granted Hand Cannoneer (unit 5) to Britons and the
menu did not show it.  That test proved nothing: unit 5's panel entry carries
`RequiredAge: 4` (the Imperial Age) for every civ that can build it, so a game
opened in the Dark Age gates it no matter which file the menu reads.

This builds the replacement subject: **Champi Scout (unit 2550)** for Britons.

  * INCAS' tree row is `ResearchedCompleted`, `Age ID = 1` (Dark Age),
    `Building ID = 12` (Barracks) -- no age gate.
  * The shipped panel lists it for Incas / Mapuche / Muisca / Tupi under
    building 12, verbatim {'ID': 2550, 'Name': 'Champi Scout', 'RequiredAge': 1}.
  * BRITONS has NO row for 2550 at all, so the grant is a real state change.

It builds into `_probe\\out_smoke4\\` and does NOT touch the profile -- the
caller decides when to install.  Re-run `install_smoke4.py` for that.
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
from aoe2mod.game import locations as G                    # noqa: E402

OUT = os.path.join(HERE, "out_smoke4")
TITLE = "aoe2mod Smoke4 Britons Champi Scout"
UNIT = "Champi Scout"
UNIT_ID = 2550
CIV = "Britons"
BUILDING_ID = 12            # Barracks -- where the shipped entries sit

INTENT = {"intent": "unit.availability", "unit": UNIT, "civ": CIV,
          "action": "grant"}


def head(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


head("0  the subject is clean (checked against the GAME's own files)")
tk = A.open_toolkit()
trees = CT.load_trees(tk.game_root)
inca = trees["INCAS"]
row = CT.row_for(inca, UNIT_ID)
print("  INCAS row for %d: %r" % (UNIT_ID, row))
assert row is not None, "Champi Scout is not in the Inca tree?!"
print("  status      : %s" % CT.node_status(inca, UNIT_ID))
print("  Age ID      : %r   <- must be 1 (Dark Age) or the test is gated again"
      % row.get("Age ID"))
print("  Building ID : %r" % row.get("Building ID"))
assert CT.node_status(inca, UNIT_ID) == "ResearchedCompleted"
assert row.get("Age ID") == 1, "the subject carries an age gate -- pick another"

brit = trees["BRITONS"]
print("  BRITONS row : %r   <- must be None: the grant must change something"
      % CT.row_for(brit, UNIT_ID))
assert CT.row_for(brit, UNIT_ID) is None
assert not CT.can_build(brit, UNIT_ID)

print()
print("  the SHIPPED panel entries for this unit, by civ and building:")
_panels = BP.load_all(tk.game_root)
_found = BP.entries_of(_panels[BP.civ_key_for(_panels, "Incas")]["obj"],
                       UNIT_ID)
for _ck, _bld, _e in _found:
    print("    %-12s building %-4s %r" % (_ck, _bld, _e))
assert _found, "no shipped entry to copy from -- synth_entry would refuse"
assert all(_e.get("RequiredAge") == 1 for _c, _b, _e in _found), \
    "a shipped entry is age-gated; the copy would carry the gate"
# count_entries(obj, KEY, node_id, space) -- the second argument is the civ cache
# key, and `obj` must be the WHOLE file object.  Passing the civ subtree, or
# passing UNITS_KEY where the key belongs, makes it scan a civ that does not
# exist and return 0 -- which here would have "confirmed" the absence for the
# wrong reason and let a no-op test through.
_brit_key = BP.civ_key_for(_panels, "Britons")
assert BP.count_entries(_panels[_brit_key]["obj"], _brit_key,
                        UNIT_ID) == 0, \
    "Britons already lists it -- the test would be a no-op"

head("1  what the tool says it will do (plan, no bytes written)")
p = tk.plan(INTENT)
print(json.dumps(p, ensure_ascii=False, indent=2, default=str))

head("2  build")
man = tk.build(INTENT, OUT, title=TITLE, author="aoe2mod probe",
               description="Dark-Age subject, no age gate: Britons gets "
                           "Champi Scout at the Barracks.",
               overwrite=True)
print(json.dumps(man, ensure_ascii=False, indent=2, default=str)[:3000])

head("3  read the ARTIFACT back off disk (not the report)")
print("  mod dir: %s" % OUT)
for dirpath, _d, files in os.walk(OUT):
    for f in sorted(files):
        fp = os.path.join(dirpath, f)
        print("    %-58s %9d B" % (os.path.relpath(fp, OUT),
                                   os.path.getsize(fp)))

_fu = os.path.join(OUT, BP.PANEL_REL)
if os.path.isfile(_fu):
    _txt, _obj = BP.load_panel(_fu)
    # ASK which key this civ uses (`panel_path_for` looks at which file really
    # lists it).  Guessing the key from the tree stem would work for Britons by
    # luck and silently look up nothing for `Magyars` -> `MAGYAR`.
    _ck = BP.panel_path_for(OUT, "Britons")[1]
    print("  panel key for Britons: %r" % _ck)
    _n = BP.count_entries(_obj, _ck, UNIT_ID)
    _b, _e = BP.find_entry(_obj, _ck, UNIT_ID, BP.UNITS_KEY)
    print("  panel lists Champi Scout for Britons: %d  at building %r  %r"
          % (_n, _b, _e))
    print("  Barracks (12) entries now: %d" % len(BP.entries(
        _obj, _ck, BUILDING_ID, BP.UNITS_KEY)))
    assert _n == 1 and _e.get("RequiredAge") == 1, \
        "the synthesised entry is missing or age-gated: %r" % (_e,)
else:
    print("  !! NO PANEL FILE in the artifact -- the panel half did not ship")

_tree = os.path.join(OUT, CT.CIVTECHTREES_REL, "BRITONS.json")
if os.path.isfile(_tree):
    _t = CT.load_trees(OUT)["BRITONS"]
    print("  tree row after the grant: %r" % (CT.row_for(_t, UNIT_ID),))
    print("  tree says Britons can build it: %s" % CT.can_build(_t, UNIT_ID))
    assert CT.can_build(_t, UNIT_ID)
else:
    print("  !! NO TREE FILE in the artifact")

head("4  honesty boundary")
print("  PROVEN  : the artifact carries both halves; the panel entry copies a")
print("            shipped Dark-Age entry, so no age gate can disguise success.")
print("  NOT PROVEN at the time: that the running game reads EITHER half.")
print("  ANSWERED SINCE (2026-10-19): the `.dat` half IS what moves the build")
print("            menu (`type 2` enable/disable on a tech the civ owns -- v7")
print("            grant, v17 revoke); the CivTechTrees JSON half is READ by the")
print("            engine but does NOT move the build menu (v15).  This script")
print("            is a historical artifact and its `smoke5` mod was uninstalled")
print("            after the audit judged the experiment AMBIGUOUS.")
print()
print("INSTALL is a separate step -- run install_smoke4.py when you are ready.")
