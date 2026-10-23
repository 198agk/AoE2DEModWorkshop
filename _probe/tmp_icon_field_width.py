# -*- coding: utf-8 -*-
"""Can a clone's icon_id point at a material a MOD adds?

`unit.create`'s `what_it_cannot_do` says a clone has no icon of its own because
"`widgetui/icons.json`'s Units section is full (0..999 all taken)".  Two things
are wrong with using that as a reason:

  * icons.json is not engine input (0 hits for its name inside AoE2DE_s.exe);
  * the material NAME is derivable from the id (`UnitIcons%03d50730`), and the
    file the engine does name is materials.json -- so "the table is full" is a
    fact about a look-up table, not about the engine's ceiling.

What actually decides the ceiling is the width of the icon_id field in the unit
record.  Measure that, then look for the two pieces of evidence that decide
whether a mod may add a material: is materials.json in the EXE's CRC path list
(that tells us the engine reads it as a game file), and does any shipped
community mod already ship one.
"""
import os
import struct
import sys

sys.path.insert(0, r"D:\Software\AI\帝国项目")

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")

print("=== A. how wide is `icon_id` in a unit record")
import aoe2mod.dat.parser as P
import inspect
src = inspect.getsource(P.read_unit)
for line in src.splitlines():
    if "icon" in line.lower():
        print("   parser:", line.strip())
import aoe2mod.dat.writer as W
wsrc = inspect.getsource(W.write_unit)
for line in wsrc.splitlines():
    if "icon" in line.lower():
        print("   writer:", line.strip())
vs = inspect.getsource(P.__dict__.get("read_unit") or (lambda: ""))
print("   (read_unit is at parser.py:%d)" % P.read_unit.__code__.co_firstlineno)
print("   (write_unit is at writer.py:%d)" % W.write_unit.__code__.co_firstlineno)

print()
print("=== B. is materials.json one of the CRC'd game files")
blob = open(EXE, "rb").read()
text = blob.decode("latin-1")
for needle in (r"widgetui\materials.json", r"widgetui\icons.json",
               r"materials.json", r"icons.json"):
    print("   %-28s hits=%d" % (needle, text.count(needle)))

print()
print("=== C. does a shipped community mod already ship materials.json")
prof = os.path.join(os.path.expanduser("~"), "Games", "Age of Empires 2 DE",
                    "76561198406248391", "mods")
hits = []
for base, dirs, files in os.walk(prof):
    for f in files:
        if f.lower() in ("materials.json", "icons.json", "morematerials.json"):
            hits.append(os.path.join(base, f).replace(prof, "<mods>"))
print("   files found:", len(hits))
for h in hits[:12]:
    print("     ", h)
