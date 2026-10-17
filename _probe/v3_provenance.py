# -*- coding: utf-8 -*-
"""V3 family (widgetui/textures/menu/civs) provenance + override-ability.

Questions:
  1. Does materials.json reference textures/menu/civs/*.png? Which atlas?
  2. Do any installed mods provide those paths (i.e. user-overridable)?
  3. Does the atlas DDS actually contain that art (i.e. it IS baked -> the loose
     file is only a build input unless the engine prefers loose files)?
  4. Is 'menu/civs' referenced by any widgetui layout json?
"""
import os
import json
import numpy as np
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODROOT = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
MAT = os.path.join(GAME, "widgetui", "materials.json")

with open(MAT, "r", encoding="utf-8-sig") as f:
    m = json.load(f)
print("materials.json top keys:", list(m.keys()))

# 1) materials / atlas / global referencing menu/civs
mats = [x["MaterialDef"] for x in m["Materials"]]
atl = [x["AtlasDef"] for x in m["AtlasTextures"]]
glb = [x["TextureDef"] for x in m["GlobalTextures"]]

hit_atlas = {}
for a in atl:
    for t in a.get("Textures", []):
        fn = t.get("FileName", "")
        if "menu/civs" in fn:
            hit_atlas.setdefault(a["Name"], []).append((t.get("RefName"), fn))
print()
print("=== atlases containing textures/menu/civs (n=%d) ===" % len(hit_atlas))
for k, v in hit_atlas.items():
    print("  atlas %-24s entries=%d   e.g. %s" % (k, len(v), v[:3]))

hit_glob = [g for g in glb if "menu/civs" in g.get("FileName", "")]
print("GlobalTextures with menu/civs: %d" % len(hit_glob))

# which materials point at those RefNames / atlas
refnames = {rn for v in hit_atlas.values() for rn, _ in v}
byref = {}
for md in mats:
    if md.get("TextureRef") in refnames or md.get("Name") in refnames:
        byref[md["Name"]] = md
print()
print("materials resolving to those RefNames (n=%d):" % len(byref))
for k in list(byref)[:8]:
    print("   ", byref[k])

# 2) installed mods providing menu/civs
print()
print("=== installed mods providing textures/menu/civs ===")
found = 0
for base, subs, files in os.walk(MODROOT):
    if os.path.basename(base).lower() == "civs" and "menu" in base.lower():
        print("   ", base, "n=", len(files))
        found += 1
print("   total:", found)

# 3) does any atlas DDS hold the V3 art? decode SD + HD and compare to V3 png
V3 = os.path.join(GAME, "widgetui", "textures", "menu", "civs")
print()
print("=== atlas decode probe for menu/civs art ===")
for name, a in [(a["Name"], a) for a in atl if a["Name"] in hit_atlas]:
    src = a.get("DefaultSource") or a.get("HDSource") or a.get("UHDSource")
    p = os.path.join(GAME, "widgetui", src.replace("/", os.sep))
    if not os.path.exists(p):
        print("   %-24s MISSING %s" % (name, p))
        continue
    try:
        img = Image.open(p).convert("RGBA")
    except Exception as e:
        print("   %-24s decode fail %s" % (name, e))
        continue
    Wd, Ht = img.size
    A = np.asarray(img, np.float32)
    for e in hit_atlas[name][:3]:
        rn, fn = e
        t = next((t for t in a["Textures"] if t.get("RefName") == rn), None)
        if not t:
            continue
        u0, v0, u1, v1 = (float(t["imageTLX"]), float(t["imageTLY"]),
                          float(t["imageBRX"]), float(t["imageBRY"]))
        box = (int(round(u0 * Wd)), int(round(v0 * Ht)),
               int(round(u1 * Wd)), int(round(v1 * Ht)))
        sl = img.crop(box)
        p3 = os.path.join(V3, os.path.basename(fn))
        if not os.path.exists(p3):
            continue
        v3 = Image.open(p3).convert("RGBA").resize(sl.size, Image.LANCZOS)
        sa = np.asarray(sl, np.float32)
        va = np.asarray(v3, np.float32)
        mk = (sa[:, :, 3] > 30) | (va[:, :, 3] > 30)
        mad = float(np.abs(sa[:, :, :3][mk] - va[:, :, :3][mk]).mean()) if mk.sum() else -1
        print("   %-14s %-14s atlas%s %s  MAD(atlasSlice, V3png)=%6.2f n=%d"
              % (os.path.basename(fn), rn, (Wd, Ht), box, mad, int(mk.sum())))

# 4) layout json references
print()
print("=== widgetui json files mentioning menu/civs ===")
wj = os.path.join(GAME, "widgetui")
for f in sorted(os.listdir(wj)):
    if not f.endswith(".json"):
        continue
    p = os.path.join(wj, f)
    try:
        with open(p, "r", encoding="utf-8-sig", errors="replace") as fh:
            txt = fh.read()
    except Exception:
        continue
    if "menu/civs" in txt or "menu_civs" in txt:
        print("   ", f, txt.count("menu/civs"))
