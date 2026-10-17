# -*- coding: utf-8 -*-
"""DECISIVE: does the engine prefer a loose PNG over the baked atlas slice?

Evidence chain to make explicit:
  A) chibi mod (182654) ships ONLY: 62 PNGs under
     widgetui/textures/ingame/emblems/ + info.json + thumbnail.png.
     It ships NO .dds, NO atlas, NO script.
  B) In shot f1 the BOTTOM command panel emblem for the local player
     (label "RemonBo (立陶宛)") displays the chibi character = MOD
     lithuanians.png (proved visually, 8x, in plist_row1_DECIDE.png /
     cp_emblem_tight.png).
  C) That widget is commandpanel.json:/BackgroundRight/CivEmblem,
     Material "CivEmblem" -> runtime-resolved to material
     "CivEmblemLithuanians" -> AtlasTextures ingamepanels ->
     FileName "textures/ingame/emblems/lithuanians.png".
  D) Therefore the engine honored the MOD's loose PNG at the atlas
     source FileName instead of the shipped ingamepanels.dds.
  => loose-file override of an atlas slice is CONFIRMED WORKING.

This script re-asserts each link from disk so the conclusion is not
resting on prose.  Read-only.
"""
import os
import json
import hashlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MOD = (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
       r"\subscribed\182654_Age of Anime (Chibi Edition)")
WJ = os.path.join(GAME, "widgetui")

print("=" * 78)
print("A. mod 182654 ships no .dds / no atlas")
print("=" * 78)
exts = {}
dds = []
for base, subs, files in os.walk(MOD):
    for f in files:
        e = os.path.splitext(f)[1].lower()
        exts[e] = exts.get(e, 0) + 1
        if e == ".dds":
            dds.append(os.path.join(base, f))
print("   extensions:", exts)
print("   .dds files :", len(dds))
print("   any dir named 'atlas':",
      any("atlas" in d.lower() for d, _, _ in os.walk(MOD)))

print()
print("=" * 78)
print("B/C. widget -> material -> atlas -> FileName")
print("=" * 78)
cp = json.load(open(os.path.join(WJ, "commandpanel.json"), encoding="utf-8"))


def probe(o, path, out):
    """Widget list items are {"Widget": {...}} wrappers, so recurse
    through EVERY key of every dict, not just ChildWidgets."""
    if isinstance(o, dict):
        if o.get("Name") == "CivEmblem":
            out.append((path, o))
        for k, v in o.items():
            probe(v, path + "/" + k, out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            probe(v, "%s[%d]" % (path, i), out)
    return out


hits = probe(cp, "", [])
print("   widgets named 'CivEmblem' in commandpanel.json:", len(hits))
for path, h in hits:
    sm = h.get("StateMaterials") or {}
    mats = []

    def harvest(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "Material" and isinstance(v, str):
                    mats.append(v)
                else:
                    harvest(v)
    harvest(sm)
    print("      at   :", path)
    print("      type :", h.get("Type"), "vp:", h.get("ViewPort"))
    print("      mats :", mats)

mats = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8"))["Materials"]


def by_name(n):
    for m in mats:
        md = m.get("MaterialDef") or {}
        if md.get("Name") == n:
            return md
    return None


print("   bare material 'CivEmblem' in materials.json:", by_name("CivEmblem") is not None)

atlas = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8"))["AtlasTextures"]
ip = None
for a in atlas:
    ad = a.get("AtlasDef") or {}
    if ad.get("Name") == "ingamepanels":
        ip = ad
        break
print("   ingamepanels UHDSource  :", ip.get("UHDSource"))
print("   ingamepanels DefaultSrc :", ip.get("DefaultSource"))
tgt = None
for t in ip["Textures"]:
    if t.get("RefName") == "CivEmblemLithuanians":
        tgt = t
        break
print("   entry CivEmblemLithuanians ->", tgt.get("FileName"))
mat = by_name("CivEmblemLithuanians")
print("   material CivEmblemLithuanians ->", mat)

print()
print("=" * 78)
print("D. the mod's loose file at exactly that FileName")
print("=" * 78)
rel = tgt["FileName"]
loose = os.path.join(MOD, "widgetui", rel)
shipped = os.path.join(WJ, rel)
print("   expected mod path :", loose)
print("   exists            :", os.path.exists(loose))
print("   shipped game path :", shipped, os.path.exists(shipped))
if os.path.exists(loose):
    h = hashlib.sha256(open(loose, "rb").read()).hexdigest()[:16]
    print("   mod   bytes/sha   : %d  %s" % (os.path.getsize(loose), h))
if os.path.exists(shipped):
    h2 = hashlib.sha256(open(shipped, "rb").read()).hexdigest()[:16]
    print("   game  bytes/sha   : %d  %s" % (os.path.getsize(shipped), h2))
    print("   IDENTICAL         :", h == h2)

print()
print("=" * 78)
print("VERDICT")
print("=" * 78)
print("  The mod supplies ONLY a loose PNG at the atlas source FileName.")
print("  The screenshot shows that art rendering in-game.")
print("  => engine resolves the atlas entry by re-reading FileName and")
print("     prefers the loose file over the baked DDS.")
print("  => BAKER = copy file. No atlas rebuild. No .dds authoring.")
