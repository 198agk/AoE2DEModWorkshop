# -*- coding: utf-8 -*-
r"""What id space is `Trigger Tech ID`, and what is in the panel's `Techs` array?

Established facts that now look inconsistent:
  * `CivTechTrees/<CIV>.json` rows of `Use Type: Tech` are said to be `.dat` tech
    array indices (5,244 tech rows across the corpus).
  * But Sicilians' tree has NO row for tech 320, 257, 255 or 96 -- and 320 is
    unit 588's `Trigger Tech ID`, 257 is 550's, 255 is 548's, 96 is 422's.
  * The PANEL lists 320 in its `Techs` array for those same civs.

Two live possibilities:
  (a) `Trigger Tech ID` is NOT a `.dat` tech index, so `node_status(tree, 320)`
      was the wrong lookup all along and the Round 49 comparison mixed id spaces.
  (b) `Trigger Tech ID` IS a `.dat` tech index, and the tree simply does not carry
      rows for that class of technology (while the panel does).

Resolve it by identity: look up `.dat` tech 320 and see whether its name is
'Siege Onager' (a technology) or something unrelated.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LANG = {}
kd = os.path.join(GAME, "resources", "en", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        for line in open(os.path.join(kd, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                LANG.setdefault(int(k.strip()), v[1:-1])

idx = sem_index()
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
techs_dat = tk._tech_records()
print("A  .dat tech records: %d" % len(techs_dat))
for tid in (320, 257, 255, 96, 207, 429, 264, 244):
    t = techs_dat[tid] if tid < len(techs_dat) else None
    e = idx.get("tech", tid)
    nm = None
    if t:
        sid = t.get("LanguageDLLName")
        nm = LANG.get(sid) if sid else None
        if nm is None:
            nm = (e.zh or e.en) if e else None
    print("   .dat tech %-5s internal=%-28r name=%r" % (
        tid, (t or {}).get("name"), nm))

print()
print("B  what `Use Type: Tech` node ids DOES the Sicilians tree carry?")
_trees = CT.load_trees(GAME)
sc = _trees["SICILIANS"]
tids = sorted(r.get("Node ID") for r in CT.tech_rows(sc))
print("   tech rows: %d" % len(tids))
print("   min=%s max=%s" % (min(tids), max(tids)))
print("   ids 200..450 present: %s" % [i for i in tids if 200 <= i <= 450][:40])
print("   first 25: %s" % tids[:25])

print()
print("C  and what does the PANEL's `Techs` array at building 49 contain?")
panels = BP.load_all(GAME)
o = panels[BP.panel_path_for(GAME, "Sicilians")[1]]["obj"]
for blk in BP.buildings(o, "Sicilians"):
    if blk.get("ID") == 49:
        pt = [e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])]
        pu = [e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])]
        print("   panel Units: %s" % pu)
        print("   panel Techs: %s" % pt)
        for i in pt:
            t = techs_dat[i] if i < len(techs_dat) else None
            e = idx.get("tech", i)
            nm = None
            if t:
                sid = t.get("LanguageDLLName")
                nm = LANG.get(sid) if sid else None
            print("      %-6s .dat internal=%-28r name=%r"
                  % (i, (t or {}).get("name"), nm or ((e.zh or e.en) if e else None)))

print()
print("D  identity test: is panel tech id == .dat tech index?")
# tech 22 is Loom in the .dat; check a panel Techs array that should contain it
l = panels[BP.panel_path_for(GAME, "Britons")[1]]["obj"]
for blk in BP.buildings(l, "Britons"):
    pt = [e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])]
    if 22 in pt:
        print("   panel lists 22 (Loom) at building %s -- and .dat tech 22 is %r"
              % (blk.get("ID"), techs_dat[22].get("name")))
        break
else:
    print("   no Britons building lists tech 22")

print()
print("E  so: does ANY civ's tree carry a row for a unit-upgrade technology?")
# unit 588's upgrade is 320; 550's is 257; 548's is 255; 422's is 96
for probe_tid in (320, 257, 255, 96, 207, 429):
    present = [s for s, t in _trees.items()
               if CT.node_status(t, probe_tid, CT.TECH_USE_TYPES) is not None]
    print("   tech %-5s in trees of %d civs" % (probe_tid, len(present)))

print()
print("F  the KEY question: does the tree carry a row for the technology that")
print("   produces the units it grants?  Compare, per civ, for unit 588:")
for s in ("SICILIANS", "CELTS", "AZTECS", "MONGOLS"):
    t = _trees[s]
    u = CT.row_for(t, 588, CT.UNIT_USE_TYPES)
    tt = (u or {}).get("Trigger Tech ID")
    print("   %-11s unit588 status=%-18s trigTech=%r  tree row for %s: %s"
          % (s, CT.node_status(t, 588, CT.UNIT_USE_TYPES), tt, tt,
             CT.node_status(t, tt, CT.TECH_USE_TYPES) if tt else "-"))

