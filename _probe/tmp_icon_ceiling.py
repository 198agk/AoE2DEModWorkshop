# -*- coding: utf-8 -*-
"""What actually limits a new unit's icon?

`unit.create`'s `what_it_cannot_do` says a clone has no icon of its own because
"`widgetui/icons.json`'s Units section is full (0..999 all taken)".  But
icons.json is NOT engine input -- 0 hits for its name inside AoE2DE_s.exe, while
`materials.json` IS named there.  So that sentence justifies a real behaviour
(the donor's icon is drawn) with a limit that may not exist.

Measure, in order:
  A. how wide the icon_id field in a unit record actually is (and so what the
     real ceiling is), plus the shipped maximum;
  B. how many icon materials exist, and how they are named;
  C. whether the icon -> material mapping is in the .dat or in a JSON file.
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from aoe2mod import api as A
from aoe2mod.dat import parser as P

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

tk = A.open_toolkit(GAME)
tk._ensure()

print("=== A. icon_id in the unit records")
ids = {}
for c in tk._civs:
    for u in c["units"]:
        if u.get("icon_id") is None:
            continue
        ids.setdefault(u["id"], u["icon_id"])
vals = sorted(ids.values())
print("unit ids with an icon_id     :", len(ids))
print("min / max icon_id            :", vals[0], "/", vals[-1])
print("negative icon_ids            :", sum(1 for v in vals if v < 0))
print("distinct icon_ids            :", len(set(vals)))
print("icon_ids above 999           :", len([v for v in vals if v > 999]))

print()
print("=== B. icon materials in materials.json")
icons = tk.icons
counts = icons.counts()
print("sections                     :", counts)
names = []
for sec in ("Units", "Buildings"):
    for key in range(0, 1100):
        nm = icons.material_name(sec, key)
        if nm:
            names.append((sec, key, nm))
print("Units+Buildings materials    :", len(names))
unit_mat = [n for n in names if n[0] == "Units"]
print("Units materials              :", len(unit_mat))
print("highest Units key present    :", max(k for (_s, k, _n) in unit_mat) if unit_mat else None)
gaps = [k for k in range(0, 1000) if not any(n[1] == k for n in unit_mat)]
print("Units keys missing in 0..999 :", len(gaps), gaps[:12])

print()
print("=== C. where the icon -> material mapping lives")
root = tk.game_root
for rel in (r"widgetui\icons.json",
            r"widgetui\materials.json",
            r"widgetui\morematerials.json"):
    p = os.path.join(root, rel)
    print("%-32s exists=%s bytes=%s" % (rel, os.path.isfile(p),
                                        os.path.getsize(p) if os.path.isfile(p) else "-"))

print()
print("=== D. how a material name is spelled for units")
sample = [n for n in unit_mat][:5]
for sec, key, nm in sample:
    print("  %-9s %-4d %s" % (sec, key, nm))
