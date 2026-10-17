# -*- coding: utf-8 -*-
"""Does a replacement loose PNG have to keep the ORIGINAL pixel size?

The atlas UV rects in materials.json are normalised (0..1) but were baked
against a specific pixel rect.  If the engine re-reads the loose file, a
different-sized file would change the aspect/slot.  So: do shipped mods
ever ship a DIFFERENT-sized PNG at an atlas source path?

For every mod file that lands on an atlas source FileName, compare its
pixel size against the game's own file at the same relative path.
Read-only.
"""
import os
import json
from PIL import Image

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")
MODS = (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
        r"\mods\subscribed")

mats = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8"))
src = {}
for a in mats["AtlasTextures"]:
    ad = a.get("AtlasDef") or {}
    for t in ad.get("Textures", []):
        src[t["FileName"]] = ad.get("Name")
for g in mats["GlobalTextures"]:
    td = g.get("TextureDef") or {}
    src.setdefault(td.get("FileName"), "<global>")


def size(p):
    try:
        with Image.open(p) as im:
            return im.size
    except Exception as e:
        return ("ERR", str(e)[:30])


rows = []
for mod in sorted(os.listdir(MODS)):
    md = os.path.join(MODS, mod)
    wj = os.path.join(md, "widgetui")
    if not os.path.isdir(wj):
        continue
    for base, subs, files in os.walk(wj):
        for f in files:
            if not f.lower().endswith((".png", ".jpg", ".dds")):
                continue
            full = os.path.join(base, f)
            rel = os.path.relpath(full, wj).replace("\\", "/")
            if rel not in src:
                continue
            gp = os.path.join(WJ, rel)
            ms, gs = size(full), (size(gp) if os.path.exists(gp) else None)
            rows.append((mod, rel, src[rel], ms, gs))

print("=== mod PNGs that land on an atlas/global source path ===")
print("%-46s %-40s %-14s %-14s %s" % ("mod", "rel path", "mod size",
                                      "game size", "SAME?"))
same = diff = missing = 0
for mod, rel, atlas, ms, gs in rows:
    if gs is None:
        tag, missing = "GAME-MISSING", missing + 1
    elif ms == gs:
        tag, same = "same", same + 1
    else:
        tag, diff = "*** DIFFERENT ***", diff + 1
    print("%-46s %-40s %-14s %-14s %s"
          % (mod[:46], rel[-40:], ms, gs, tag))

print()
print("total on-source files: %d   same-size: %d   different-size: %d   "
      "game-missing: %d" % (len(rows), same, diff, missing))
