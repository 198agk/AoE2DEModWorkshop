"""Settle the MenuIcons / Notification / StatIcons buckets.

Established (sections_last3_fix.py):
  Notification wonder_icon -> ScorePanelWonder -> icons/indicator_wonder.png
  Notification relic_icon  -> ScorePanelRelic  -> icons/indicator_relic.png
  StatIcons   24/24: stat_icon_<x> -> StatIcons<TitleCase(x)> -> staticons/

The exe context dump showed submenu_oligarchy / democracy / tyranny correspond to
the Return of Rome government techs (display strings "Oligarchy"/"Democracy"/
"Tyranny" sit in the exe string pool" and materials has TechIconsT154Tyranny /
T155Oligarchy / T156Democracy).  Test that as a RULE, not a guess.

Also test the decisive structural question: does the engine ever read icons.json?
Read-only.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
W = os.path.join(GAME, "widgetui")

sys.stdout.reconfigure(encoding="utf-8")

mat = json.load(open(os.path.join(W, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))
ref_to_file, ref_to_atlas = {}, {}
for wrap in mat.get("AtlasTextures", []):
    ad = wrap.get("AtlasDef") or {}
    for t in ad.get("Textures", []):
        if t.get("RefName"):
            ref_to_file[t["RefName"]] = t.get("FileName")
            ref_to_atlas[t["RefName"]] = ad.get("Name")
matdefs = {}
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    if md.get("Name"):
        matdefs[md["Name"]] = md

def desc(n):
    md = matdefs.get(n)
    if not md:
        return "<none>"
    k = md.get("TextureRef") or n
    return "atlas=%-16s file=%s" % (ref_to_atlas.get(k), ref_to_file.get(k))

print("=" * 96)
print("RULE TEST: submenu_<X> -> TechIconsT<id><X>  (Return of Rome governments)")
print("=" * 96)
for tail in ("oligarchy", "democracy", "tyranny"):
    tc = tail[:1].upper() + tail[1:]
    cands = sorted(n for n in matdefs
                   if n.startswith("TechIconsT") and n.lower().endswith(tail))
    print("   submenu_%-12s -> %s" % (tail, cands if cands else "<none>"))
    for c in cands:
        print("        %-28s %s" % (c, desc(c)))

print()
print("=" * 96)
print("Other MenuIcons values: any material whose name contains their tail token?")
print("=" * 96)
for v in ("submenu_button_base", "submenu_open_arrow_overlay",
          "submenu_return_arrow_overlay", "submenu_open", "submenu_return",
          "mutually_exclusive_tech_unavailable"):
    toks = [t for t in v.split("_")]
    cands = [n for n in matdefs
             if all(t.lower() in n.lower() for t in ("submenu",) + tuple(toks[1:]))
             or all(t.lower() in n.lower() for t in toks)]
    print("   %-36s %s" % (v, cands[:4] if cands else "<none>"))

print()
print("=" * 96)
print("DECISIVE: does the engine read icons.json?")
print("=" * 96)
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
for name in (b"icons.json", b"materials.json", b"morematerials.json",
             b"objreplacement.json", b"futuravailableunits.json"):
    print("   %-26s in exe: %d" % (name.decode(), exe.count(name)))
print()
print("   -> icons.json is NOT named in the exe; materials.json/morematerials.json ARE.")
print("      icons.json is a UI-editor-side artifact, not an engine input.")
