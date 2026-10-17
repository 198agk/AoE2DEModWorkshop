# -*- coding: utf-8 -*-
r"""Is the ZERO-MOD experiment clean?  Check every ENABLED mod first.

If any enabled mod ships `CivTechTrees/<CIV>.json` or `futuravailableunits.json`,
the shipped-disagreement experiment is contaminated and the user's observation
would not be about the game's own files.  Check before asking for a game.
"""
import json
import os
import sys

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
MODS = os.path.join(ACC, "mods")
INTERESTING = ("futuravailableunits.json", "paphosfutureavailableunits.json",
               "CivTechTrees", "empires2_x2_p1.dat", "civilizations.json",
               "linkedUnits.json", "linkedTechs.json")

st = json.loads(open(os.path.join(MODS, "mod-status.json"), "rb")
                .read().decode("utf-8-sig"), strict=False)
print("enabled / disabled mods, and whether each touches a relevant path")
print("-" * 78)
for m in sorted(st.get("Mods", []), key=lambda m: m.get("Priority") or 0):
    path = (m.get("Path") or "").replace("//", os.sep).replace("/", os.sep)
    d = os.path.join(MODS, path)
    hits = []
    if os.path.isdir(d):
        for root, _dd, files in os.walk(d):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), d)
                if any(k.lower() in rel.lower() for k in INTERESTING):
                    hits.append(rel)
    flag = "ON " if m.get("Enabled") else "off"
    print("  %s prio %-2s %-58s %s"
          % (flag, m.get("Priority"), os.path.basename(path)[:58],
             ("TOUCHES %d: %s" % (len(hits), hits[:3])) if hits else "clean"))

print()
print("local mods on disk (a mod present but NOT in mod-status.json is not loaded):")
loc = os.path.join(MODS, "local")
for d in sorted(os.listdir(loc)) if os.path.isdir(loc) else []:
    registered = any("Smoke5" in (m.get("Path") or "") and "Smoke5" in d
                     or os.path.basename((m.get("Path") or "").replace("//", os.sep)) == d
                     for m in st.get("Mods", []))
    print("   %-58s registered=%s" % (d, registered))
