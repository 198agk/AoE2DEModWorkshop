# -*- coding: utf-8 -*-
r"""Black-box check of the INSTALLED smoke5 mod, read off the real profile.

Verifies the three claims the experiment rests on, from the files the game will
actually read (not from the build report):

  1. the .dat really raises Villager HP to 1000 (the positive control)
  2. the tree file really grants Champi Scout (2550) to BRITONS
  3. the panel file really has Britons' Militia (74) removed, and no other civ's
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

TITLE = "aoe2mod Smoke5 TreeVsPanel"
ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
MOD = os.path.join(ACC, "mods", "local", TITLE)

print("installed mod: %s" % MOD)
print("exists       : %s" % os.path.isdir(MOD))
assert os.path.isdir(MOD), "the mod is not in the profile"
print()
for root, _d, files in os.walk(MOD):
    for f in sorted(files):
        p = os.path.join(root, f)
        print("   %-56s %10d B" % (os.path.relpath(p, MOD), os.path.getsize(p)))

# 1 --------------------------------------------------------------- the control
print()
print("1  the .dat control (Villager 25 -> 1000)")
# `hit_points` is a field of the unit record itself (parser.py:772), NOT of
# `type50`.  Reading `type50.hit_points` yields None, and that None flows into
# the assertion and reports the .dat as broken -- a probe bug, not a product bug.
from aoe2mod.dat import parser as P                         # noqa: E402
_d = os.path.join(MOD, "resources", "_common", "dat", "empires2_x2_p1.dat")
_raw, _how = P.load_dat(_d)
_stats = P.Parser(_raw).parse()
_hp = set()
for _civ in _stats["civs"]:
    for _u in _civ["units"]:
        if _u.get("id") == 83:
            _hp.add(_u.get("hit_points"))
print("   Villager (id 83) hit points across all civs: %s" % sorted(_hp))
assert _hp == {1000}, "the control is not in the dat: %s" % sorted(_hp)


# 2 ------------------------------------------------------------- the tree half
print()
print("2  the tree half, read from the mod")
_t = CT.load_trees(MOD)["BRITONS"]
print("   can build 2550 (Champi Scout): %s" % CT.can_build(_t, 2550))
print("   still has 74 (Militia)       : %s"
      % (CT.row_for(_t, 74) is not None))
assert CT.can_build(_t, 2550)
assert CT.row_for(_t, 74) is not None, "the tree lost Militia -- it should not"

# 3 ------------------------------------------------------------ the panel half
print()
print("3  the panel half, read from the mod")
tk = A.open_toolkit()
_pt, _po = BP.load_panel(os.path.join(MOD, BP.PANEL_REL))
_pk_edit = BP.panel_path_for(MOD, "Britons")[1]      # the key the panel uses
_b, _e = BP.find_entry(_po, "Britons", 74, BP.UNITS_KEY)
print("   Britons Militia (74)   : %r" % (_e,))
print("   Britons Champi (2550)  : %r"
      % (BP.find_entry(_po, "Britons", 2550, BP.UNITS_KEY)[1],))
assert _e is None, "Britons still lists Militia -- the panel edit did not land"
assert BP.find_entry(_po, "Britons", 2550, BP.UNITS_KEY)[1] is None, \
    "the panel lists Champi Scout, so a hit could not be attributed to the tree"

_panels_game = BP.load_all(tk.game_root)
_n = 0
for _c in sorted(_po):
    if not isinstance(_c, str):
        continue
    if _c == _pk_edit:
        # Britons is the civ we deliberately edited; it must differ.  Including
        # it here would assert that the edit did NOT happen.
        continue
    _gb = BP.find_entry(_panels_game[BP.panel_path_for(tk.game_root, _c)[1]]["obj"],
                        _c, 74, BP.UNITS_KEY)[1]
    _mb = BP.find_entry(_po, _c, 74, BP.UNITS_KEY)[1]
    if _gb is not None:
        _n += 1
        assert _mb is not None, "%s lost its Militia -- the edit leaked" % _c
print("   civs that ship Militia and still have it: %d" % _n)

print()
print("SMOKE5 INSTALLED AND VERIFIED.")
print("  the .dat control is present, the tree grants a Dark-Age unit,")
print("  the panel lost Britons' Militia and nobody else's.")
