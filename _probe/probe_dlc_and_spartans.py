# -*- coding: utf-8 -*-
r"""Two practical questions before the user plays anything.

1. **Which DLC does each candidate civilization belong to?**  All four
   Imperial-Age complete-path subjects sit on DLC civs.  If the user cannot pick
   MUISCA the protocol is unusable, and nothing on disk can prove entitlement --
   but if any candidate sits on a BASE-GAME civ (Aztecs / Mayans / Incas /
   Britons ...), that removes the question entirely.

2. **The SPARTANS Fishing Ship pair**: unit 13 (kind-T: tree grants it, panel
   silent) and unit 2147 (kind-P: panel lists it, tree has no row) are BOTH named
   "Fishing Ship" for Spartans at building 2172.  If both really are reachable in
   the Dark Age, this is the cheapest possible decisive test -- but a name
   collision makes the observation ambiguous, which is exactly why the earlier
   round rejected it.  Establish whether the collision is real.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat")
idx = sem_index()

print("A  hunt for a civ -> DLC/expansion mapping in the shipped data")
hits = []
for dirpath, _dirs, files in os.walk(DAT):
    for fn in files:
        if not fn.lower().endswith(".json"):
            continue
        p = os.path.join(dirpath, fn)
        try:
            txt = open(p, "rb").read().decode("utf-8-sig", "replace")
        except OSError:
            continue
        low = txt.lower()
        if "muisca" not in low and "spartans" not in low:
            continue
        try:
            o = json.loads(txt, strict=False)
        except Exception:
            o = None
        keys = set()
        def walk(x, depth=0):
            if depth > 4:
                return
            if isinstance(x, dict):
                for k, v in x.items():
                    keys.add(k.lower())
                    walk(v, depth + 1)
            elif isinstance(x, list):
                for v in x[:50]:
                    walk(v, depth + 1)
        walk(o)
        interesting = sorted(k for k in keys
                             if k in ("dlc", "dlc_name", "expansion", "expansion_id",
                                      "app_id", "appid", "pack", "pack_id",
                                      "civilization_id", "id"))
        hits.append((os.path.relpath(p, GAME), fn, interesting))
for rel, fn, k in sorted(hits):
    print("   %-58s keys=%s" % (rel, k))

print()
print("B  civilizations.json entries, full field set for the candidates")
p = os.path.join(DAT, "civilizations.json")
o = json.loads(open(p, "rb").read().decode("utf-8-sig"), strict=False)
lst = o["civilization_list"]
print("   entries: %d" % len(lst))
print("   union of keys: %s" % sorted({k for e in lst for k in e}))
for name in ("Muisca", "Mapuche", "Tupi", "Spartans", "Incas", "Mayans",
             "Aztecs", "Britons", "Sicilians"):
    for e in lst:
        if str(e.get("name", "")).lower() == name.lower() or \
           str(e.get("name_string_id")) in ("",) and False:
            print("   %-11s %s" % (name, e))

print()
print("C  the SPARTANS Fishing Ship collision, in detail")
trees = CT.load_trees(GAME)
sp = trees["SPARTANS"]
for uid in (13, 2147):
    r = CT.row_for(sp, uid, CT.UNIT_USE_TYPES)
    u = idx.get("unit", uid)
    print("   unit %-5s tree row: %s" % (uid, "NONE" if r is None else
                                         {k: r.get(k) for k in
                                          ("Name", "Node Status", "Age ID",
                                           "Building ID", "Trigger Tech ID",
                                           "Node Type", "Name String ID")}))
    print("           semantic name: %r  (en=%r zh=%r)"
          % (((u.zh or u.en) if u else None), (u.en if u else None),
             (u.zh if u else None)))
panels = BP.load_all(GAME)
o2 = panels[BP.panel_path_for(GAME, "Spartans")[1]]["obj"]
for blk in BP.buildings(o2, "Spartans"):
    if blk.get("ID") == 2172:
        print("   panel building 2172 Units: %s"
              % [(e.get("ID"), e.get("Name"), e.get("RequiredAge"))
                 for e in (blk.get(BP.UNITS_KEY) or [])])
        print("   panel building 2172 Techs: %s"
              % [(e.get("ID"), e.get("Name"))
                 for e in (blk.get(BP.TECHS_KEY) or [])])

print()
print("D  what is building 2172, and which civs have it?")
for x in (2172, 45, 12, 101, 87, 49):
    owners = [s for s, t in trees.items()
              if any((r.get("Node ID") == x and r.get("Use Type") == "Building")
                     for r in CT.rows_of(t))]
    nm = None
    for t in trees.values():
        for r in CT.rows_of(t):
            if r.get("Node ID") == x and r.get("Use Type") == "Building":
                nm = r.get("Name")
                break
        if nm:
            break
    print("   building %-5s tree name=%-20r in %d civs" % (x, nm, len(owners)))
