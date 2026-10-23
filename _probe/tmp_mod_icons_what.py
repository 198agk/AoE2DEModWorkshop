# -*- coding: utf-8 -*-
"""What does the shipped community mod actually do to icons.json / materials.json?

This is the decisive evidence for `unit.create`'s icon limit: if a released UI mod
ships both files under `widgetui\`, then "the icon table is full" is not a wall --
a mod can extend it.  Measure what it extends, and whether it clears the CRC
barrier (these two files are NOT in the EXE's path list, unlike the .dat).
"""
import io
import json
import os

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MOD = os.path.join(os.path.expanduser("~"), "Games", "Age of Empires 2 DE",
                   "76561198406248391", "mods", "subscribed",
                   "411309_[UI]7V1_Three Kingdoms [兰亭三国系列文本音乐] v1.46",
                   "widgetui")

shipped_icons = os.path.join(GAME, "widgetui", "icons.json")

def load(p):
    with io.open(p, encoding="utf-8-sig") as fh:
        return json.loads(fh.read())

print("=== A. sizes")
for p in (shipped_icons, os.path.join(MOD, "icons.json"),
          os.path.join(GAME, "widgetui", "materials.json"),
          os.path.join(MOD, "materials.json")):
    print("   %-58s %s bytes" % (os.path.basename(p) + " @" +
                                 ("game" if p.startswith(GAME) else "mod"),
                                 os.path.getsize(p)))
# disambiguate: the two icons.json have the same basename, print full tail
print()
for p in (shipped_icons, os.path.join(MOD, "icons.json")):
    print("   ", p.replace(GAME, "<game>").replace(os.path.expanduser("~"), "~"))

print()
print("=== B. section sizes, shipped vs modded")
a = load(shipped_icons)
b = load(os.path.join(MOD, "icons.json"))
for sec in sorted(set(a) | set(b)):
    if sec.startswith("$"):
        continue
    av = a.get(sec)
    bv = b.get(sec)
    na = len(av) if isinstance(av, dict) else "-"
    nb = len(bv) if isinstance(bv, dict) else "-"
    flag = "  <== DIFFERENT" if na != nb else ""
    print("   %-26s shipped=%-5s modded=%-5s%s" % (sec, na, nb, flag))

print()
print("=== C. what Units keys the mod has beyond the shipped range")
ua = a.get("Units") or {}
ub = b.get("Units") or {}
extra = sorted(set(ub) - set(ua))
print("   extra keys:", len(extra), extra[:12])
changed = [k for k in set(ua) & set(ub) if ua[k] != ub[k]]
print("   changed values:", len(changed), changed[:8])
if extra:
    for k in extra[:4]:
        print("     %s -> %s" % (k, ub[k]))
if changed:
    for k in changed[:4]:
        print("     %s: %s  =>  %s" % (k, ua[k], ub[k]))

print()
print("=== D. does the mod's materials.json carry materials the shipped one lacks")
ma = load(os.path.join(GAME, "widgetui", "materials.json"))
mb = load(os.path.join(MOD, "materials.json"))

def names(doc):
    out = set()
    for m in doc.get("Materials") or []:
        d = m.get("MaterialDef") or {}
        if d.get("Name"):
            out.add(d["Name"])
    return out

na, nb = names(ma), names(mb)
print("   shipped materials:", len(na))
print("   modded  materials:", len(nb))
print("   added by the mod :", len(nb - na))
print("   removed by it    :", len(na - nb))
added = sorted(nb - na)
for nm in added[:10]:
    print("     +", nm)
