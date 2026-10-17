"""Is `Civ.TechTreeID` a real pointer, or a legacy field the engine ignores?

The dat ships ONE TechTree object (genieutils `DatFile.h`: `genie::TechTree
TechTree;`), so the per-civ `TechTreeID` cannot index trees.  Its values are
distinct for all 63 civs and land inside the tech array (British 254, Goths 259,
Hindustanis 1, Incas 3, Koreans 504, Italians 10, Gaia 348, max 1460 of 1510).

Spot check suggested `techs[TechTreeID].civ == that civ's own array index` for
several civs.  If that holds for all 63, the field IS meaningful and names each
civ's own root tech -- which would be a per-civ pointer the project has never
used.  If it holds for only some, the field is content, not a pointer.

Also: `tech_tree_name` in civilizations.json vs the file stems, per civ, to see
whether the 6 known桥 overrides are the whole story.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, tail, _how = tk._parsed
techs = L.locate_techs(data, tail, gv)
effects, _ = L.locate_effects(data)

print("=" * 72)
print("1. does techs[TechTreeID] belong to the civ that names it?")
print("=" * 72)
owned = 0
unowned = []
oob = []
types = Counter()
for c in civs:
    tid = c.get("tech_tree_id")
    idx = c["index"]
    if tid is None or not (0 <= tid < len(techs)):
        oob.append((c["name"], tid))
        continue
    t = techs[tid]
    if t.get("civ") == idx:
        owned += 1
    else:
        unowned.append((c["name"], idx, tid, t.get("civ"), t.get("name")))
    types[t.get("type")] += 1

print("   civs whose techs[TechTreeID].civ == their own index : %d of %d"
      % (owned, len(civs)))
print("   out of range (or None)                              : %s" % oob)
print("   tech type at that index                             : %s"
      % types.most_common())
print("   the civs where it does NOT match (%d):" % len(unowned))
for name, idx, tid, owner, tname in unowned[:20]:
    print("     %-14s idx=%-3d TechTreeID=%-5d tech.civ=%-4s name=%r"
          % (name, idx, tid, owner, tname))

print()
print("=" * 72)
print("2. what does the tech at that index DO?")
print("=" * 72)
for name in ("British", "Goths", "Italians", "Gaia"):
    c = [x for x in civs if x["name"] == name][0]
    t = techs[c["tech_tree_id"]]
    rows = C.effect_rows(effects, t, fanout=None, ix=None)
    print("   %-10s TechTreeID=%-5d type=%s effect_id=%s rows=%d %s"
          % (name, c["tech_tree_id"], t.get("type"), t.get("effect_id"),
             len(rows), Counter(r["type"] for r in rows).most_common(4)))

print()
print("=" * 72)
print("3. civilizations.json tech_tree_name vs the tree files on disk")
print("=" * 72)
trees = CT.load_trees(tk.game_root)
cj = os.path.join(tk.game_root, "resources", "_common", "dat", "civilizations.json")
with open(cj, "r", encoding="utf-8") as fh:
    clist = json.load(fh)["civilization_list"]
print("   civilizations.json entries %d / tree files %d / dat civs %d"
      % (len(clist), len(trees), len(civs)))
bad = []
for c, e in zip(civs, clist):
    want = e.get("tech_tree_name")
    stem = CT.civ_file_stem(c["name"])
    if stem != want:
        bad.append((c["name"], stem, want))
print("   civs where civ_file_stem() != civilizations.json tech_tree_name : %d"
      % len(bad))
for n, s, w in bad[:12]:
    print("     %-14s derived=%-14s declared=%s" % (n, s, w))
missing = [e.get("tech_tree_name") for e in clist
           if e.get("tech_tree_name") not in trees]
print("   declared names with no tree file : %s" % missing)

print()
print("NOTE: the dat's own TechTree section is a SINGLE object, so TechTreeID")
print("      cannot be selecting a tree.  What it selects is reported above.")
