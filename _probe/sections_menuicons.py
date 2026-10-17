"""MenuIcons resolution, focused.

Established so far:
  Notification wonder_icon -> ScorePanelWonder -> icons/indicator_wonder.png
  Notification relic_icon  -> ScorePanelRelic  -> icons/indicator_relic.png
  StatIcons   24/24 -> StatIcons<X> -> ingamepanels -> staticons/<x>.png

MenuIcons' 9 values are absent verbatim from materials.json, the tree, and the
exe, and the official filename->RefName normalization does not produce them.
This script asks what the *layout* side expects: which widgets reference a
submenu, and what material names those widgets use.  Read-only.
"""
import json
import os
import re
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

print("=" * 96)
print("A. materials whose FileName contains 'submenu' or 'menu/buttons'")
print("=" * 96)
for rn, fn in sorted(ref_to_file.items()):
    if fn and ("submenu" in fn.lower() or "menu/button" in fn.lower()):
        print("   %-34s %-58s atlas=%s" % (rn, fn, ref_to_atlas.get(rn)))

print()
print("=" * 96)
print("B. on-disk PNGs under widgetui/textures/menu whose name looks submenu-ish")
print("=" * 96)
for root, dirs, files in os.walk(os.path.join(W, "textures", "menu")):
    for fn in files:
        low = fn.lower()
        if "submenu" in low or "return_arrow" in low or "open_arrow" in low:
            print("   ", os.path.relpath(os.path.join(root, fn), W))

print()
print("=" * 96)
print("C. which layouts mention 'submenu' and with what material")
print("=" * 96)
for root, dirs, files in os.walk(W):
    for fn in files:
        if not fn.lower().endswith(".json"):
            continue
        p = os.path.join(root, fn)
        try:
            txt = open(p, "r", encoding="utf-8-sig", errors="replace").read()
        except Exception:
            continue
        if "submenu" not in txt.lower() and "SubMenu" not in txt:
            continue
        mats = sorted(set(re.findall(r'"Material"\s*:\s*"([^"]+)"', txt)))
        smat = [m for m in mats if "menu" in m.lower() or "sub" in m.lower()]
        print("   %-40s materials(%d): %s" % (fn, len(mats), smat[:8]))

print()
print("=" * 96)
print("D. every material name containing 'Sub' (case-insensitive)")
print("=" * 96)
for n in sorted(matdefs):
    if "sub" in n.lower():
        md = matdefs[n]
        k = md.get("TextureRef") or n
        print("   %-34s type=%-8s atlas=%-16s file=%s"
              % (n, md.get("Type"), ref_to_atlas.get(k), ref_to_file.get(k)))
