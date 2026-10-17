# -*- coding: utf-8 -*-
"""Why did the cross-civ check claim Incas lost its Militia?

Is it the edit leaking, or my lookup asking the wrong file?  Answer from the
shipped files first, then the artifact.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402

tk = A.open_toolkit()
GAME = tk.game_root
OUT = os.path.join(HERE, "out_smoke5")

for label, root in (("GAME", GAME), ("MOD ", OUT)):
    panels = BP.load_all(root)
    print("=== %s ===" % label)
    for civ in ("Britons", "Incas", "Turks", "Goths"):
        path, key = BP.panel_path_for(root, civ)
        obj = panels[key]["obj"]
        b, e = BP.find_entry(obj, key, 74, BP.UNITS_KEY)
        b2, e2 = BP.find_entry(obj, key, 2550, BP.UNITS_KEY)
        print("  %-9s file=%-30s key=%-9s militia=(%r,%r) champi=(%r,%r)"
              % (civ, os.path.basename(path), key, b, e, b2, e2))
    print()


print("=== does the key 'Britons' appear inside other civs' text? ===")
with open(os.path.join(GAME, BP.PANEL_REL), "rb") as fh:
    t = fh.read().decode("utf-8-sig")
with open(os.path.join(OUT, BP.PANEL_REL), "rb") as fh:
    t2 = fh.read().decode("utf-8-sig")
print("  shipped occurrences of '\"Britons\"': %d" % t.count('"Britons"'))
print("  mod     occurrences of '\"Britons\"': %d" % t2.count('"Britons"'))
print("  shipped occurrences of '\"Incas\"':   %d" % t.count('"Incas"'))
print("  mod     occurrences of '\"Incas\"':   %d" % t2.count('"Incas"'))
print()
print("  shipped Militia entry text (74) count: %d" % t.count('{"ID": 74'))
print("  mod     Militia entry text (74) count: %d" % t2.count('{"ID": 74'))
