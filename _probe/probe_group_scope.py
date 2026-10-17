# -*- coding: utf-8 -*-
"""Two questions, one probe:

A. Are the label-rule collisions two DIFFERENT units sharing a stem name?
B. Does art() hand back files that belong to a different unit?
"""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mod.api as A
from aoe2mod.game import sprites as S

tk = A.open_toolkit(); tk._ensure()
g = tk._stats["graphics"]; civs = tk._parsed[1]
idx = S.art_index(tk.game_root, g)

byname = {}
for rec in g:
    f = (rec.get("file") or "").strip()
    n = (rec.get("name") or "").strip()
    if f and f != "None":
        byname.setdefault(f, n)

print("=== A. record names of the colliding files ===")
for f in ("u_inf_hero_themistocles_idle_x1", "u_shp_hero_themistocles_idleA_x1",
          "u_cav_equites_idleB_x1", "u_cav_lancer_idleB_x1",
          "u_arc_bowman_walk_x1", "u_arc_longbowman_walkA_x1"):
    print("   %-36s name=%r" % (f, byname.get(f)))

print()
print("=== B. does one stem group mix several units? ===")
for stem in ("Themistocles", "Lancer", "Archer", "Bowman", "Longbowman"):
    files = idx.group(stem)
    print("   stem %-16s files=%d" % (stem, len(files)))
    for f in sorted(files):
        print("        %-38s %r" % (f, byname.get(f)))

print()
print("=== C. which units resolve to stem 'Lancer' / 'Themistocles'? ===")
for stem in ("Lancer", "Themistocles"):
    hits = []
    for c in civs:
        for u in c.get("units", ()):
            a = idx.art(u)
            if a and a.get("stem") == stem:
                hits.append((c.get("name"), u.get("id"), a.get("file")))
    seen = {}
    for civ, uid, f in hits:
        seen.setdefault(uid, set()).add(f)
    print("   stem %s -> %d (civ,unit) pairs, %d distinct unit ids" % (stem, len(hits), len(seen)))
    for uid, fs in sorted(seen.items()):
        print("        unit %-6d standing files: %s" % (uid, sorted(fs)))
