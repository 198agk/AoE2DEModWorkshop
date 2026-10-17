"""Pin the last families by going through materials.json the other way.

Round 1 (sections_last3_exhaustive.py) found:
  wonder_icon -> widgetui/textures/ingame/icons/indicator_wonder.png
  relic_icon  -> widgetui/textures/ingame/icons/indicator_relic.png
  stat_icon_hpregen -> materials StatIconsHpRegeneration / hpRegen.png
  submenu_oligarchy/democracy/tyranny -> materials TechIconsT154Tyranny / T155 / T156
  9 MenuIcons values: absent from every text file

Now search materials.json for a material whose FileName is each of the found
PNGs, so the value -> material -> atlas -> FileName chain is complete.
Read-only.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")

sys.stdout.reconfigure(encoding="utf-8")

mat = json.load(open(os.path.join(WIDGETUI, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))

# FileName -> [material names]
byfile = {}
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    nm = md.get("Name")
    tr = md.get("TextureRef")
    key = tr or nm
    if not key:
        continue
    # find the atlas entry that carries this key
    for at in mat.get("AtlasTextures", []):
        for t in at.get("Textures", []):
            if t.get("RefName") == key:
                byfile.setdefault(t.get("FileName", "").lower(), []).append(
                    (nm, t.get("FileName"), at.get("Name")))
# global textures too
for gt in mat.get("GlobalTextures", []):
    td = gt.get("TextureDef") or {}
    fn = td.get("FileName")
    if fn:
        byfile.setdefault(fn.lower(), []).append((td.get("Name"), fn, "<global>"))

TARGETS = [
    "textures/ingame/icons/indicator_wonder.png",
    "textures/ingame/icons/indicator_relic.png",
    "textures/ingame/staticons/hpRegen.png",
]
for t in TARGETS:
    print("=" * 92)
    print(t)
    print("=" * 92)
    hits = byfile.get(t.lower())
    if hits:
        for nm, fn, atlas in hits:
            print("   material=%r  atlas=%r" % (nm, atlas))
    else:
        print("   <not an atlas/global FileName>")
    print()

# ---- material -> FileName for the StatIcons family -------------------------
print("=" * 92)
print("StatIcons* materials and their FileNames")
print("=" * 92)
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    nm = md.get("Name") or ""
    if nm.startswith("StatIcons"):
        key = md.get("TextureRef") or nm
        fn = None
        for at in mat.get("AtlasTextures", []):
            for t2 in at.get("Textures", []):
                if t2.get("RefName") == key:
                    fn = t2.get("FileName")
        print("   %-34s -> %s" % (nm, fn))

# ---- MenuIcons: is there any material with these stems? --------------------
print()
print("=" * 92)
print("MenuIcons candidate materials (any material whose name contains the tail)")
print("=" * 92)
tails = ["button_base", "open_arrow_overlay", "return_arrow_overlay",
         "submenu_open", "submenu_return", "mutually_exclusive"]
allnames = []
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    if md.get("Name"):
        allnames.append(md["Name"])
for tl in tails:
    cand = [n for n in allnames
            if all(p in n.lower() for p in tl.split("_"))]
    print("   %-24s %s" % (tl, cand[:6] if cand else "<none>"))
