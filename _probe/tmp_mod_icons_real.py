# -*- coding: utf-8 -*-
"""Which of the mod's extra Units keys carry a REAL material name?

The literal string "None" means the slot was reserved and left empty.  Anything
else is a material the mod actually added.  If real ones exist, then a mod CAN
give a unit an icon above 999, and the product's "no icon of its own" sentence
describes a limit of the shipped file, not of the engine.
"""
import io
import json
import os
import sys

sys.path.insert(0, r"D:\Software\AI\帝国项目")

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODROOT = os.path.join(os.path.expanduser("~"), "Games", "Age of Empires 2 DE",
                       "76561198406248391", "mods", "subscribed",
                       "411309_[UI]7V1_Three Kingdoms [兰亭三国系列文本音乐] v1.46")

def load(p):
    with io.open(p, encoding="utf-8-sig") as fh:
        return json.loads(fh.read())

shipped = load(os.path.join(GAME, "widgetui", "icons.json"))
modded = load(os.path.join(MODROOT, "widgetui", "icons.json"))

for sec in ("Units", "Techs"):
    base = shipped.get(sec) or {}
    mine = modded.get(sec) or {}
    extra = {k: v for k, v in mine.items() if k not in base}
    real = {k: v for k, v in extra.items()
            if v and str(v).strip().lower() not in ("none", "null", "")}
    print("=== %s" % sec)
    print("   extra keys       :", len(extra))
    print("   literal 'None'   :", len([v for v in extra.values()
                                        if str(v).strip().lower() == "none"]))
    print("   REAL material    :", len(real))
    for k in sorted(real, key=lambda s: int(s))[:10]:
        print("     %s -> %s" % (k, real[k]))
    print()

print("=== does the game's own materials.json have those material names?")
mats = load(os.path.join(GAME, "widgetui", "materials.json"))
names = set()
for m in mats.get("Materials") or []:
    d = m.get("MaterialDef") or {}
    if d.get("Name"):
        names.add(d["Name"])
modmats = load(os.path.join(MODROOT, "widgetui", "materials.json"))
for m in modmats.get("Materials") or []:
    d = m.get("MaterialDef") or {}
    if d.get("Name"):
        names.add(d["Name"])
real_units = {k: v for k, v in (modded.get("Units") or {}).items()
              if k not in (shipped.get("Units") or {})
              and str(v).strip().lower() not in ("none", "null", "")}
present = [v for v in real_units.values() if v in names]
print("   real extra Unit materials resolvable:", len(present), "of",
      len(real_units))
for nm in present[:6]:
    print("     ", nm)
