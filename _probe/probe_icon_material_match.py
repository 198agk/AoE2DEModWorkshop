# -*- coding: utf-8 -*-
"""probe_icon_material_match.py -- am I pairing the material with the right TEXTURE?

probe_icon_look.py resolves a material to a texture with

    t["RefName"] in (material_name, MaterialDef["Name"])

That is a guess.  `MaterialDef` carries THREE name-ish fields (Name, TextureRef,
AtlasRef) and every texture inside an atlas carries a RefName.  If RefName is not
unique inside an atlas, the first match wins and the picture belongs to some other
material -- which would look like "the buildings section is wrong" while the real
fault is the join.

This probe prints, for a handful of materials, all three names and every texture
whose RefName matches any of them, so the join key can be chosen from data.
"""
from __future__ import print_function

import codecs
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"

CASES = ["BuildingIcons002Barracks1", "BuildingIcons028TownCenter",
         "BuildingIcons034House", "BuildingIcons007Castle",
         "UnitIcons02850730", "UnitIcons01550730", "TechIconsT006Loom",
         "IconAction094"]


def main():
    with io.open(os.path.join(WID, "materials.json"), encoding="utf-8-sig") as fh:
        M = json.load(fh)
    atls = {}
    for e in M["AtlasTextures"]:
        d = e.get("AtlasDef", e)
        atls[d["Name"]] = d
    mats = {}
    for m in M["Materials"]:
        md = m.get("MaterialDef")
        if md and md.get("Name"):
            mats.setdefault(md["Name"], md)

    # how unique are RefNames inside one atlas?
    print("=== RefName uniqueness per atlas ===")
    for name in sorted(atls):
        tex = atls[name].get("Textures") or []
        if not tex:
            continue
        refs = [t.get("RefName") for t in tex]
        dup = len(refs) - len(set(refs))
        print("  %-24s %5d textures, %4d distinct RefName, %d duplicate slots"
              % (name, len(refs), len(set(refs)), dup))

    print("\n=== per-material join ===")
    for case in CASES:
        md = mats.get(case)
        print("\n  %s" % case)
        if not md:
            print("    NOT A MATERIAL")
            continue
        print("    Name=%r TextureRef=%r AtlasRef=%r"
              % (md.get("Name"), md.get("TextureRef"), md.get("AtlasRef")))
        at = atls.get(md.get("AtlasRef"))
        if at is None:
            print("    NO ATLAS %r" % md.get("AtlasRef"))
            continue
        hits = []
        for t in at["Textures"]:
            if t.get("RefName") in (case, md.get("TextureRef"), md.get("Name")):
                hits.append((t.get("RefName"), t.get("FileName")))
        for r, f in hits:
            print("    hit RefName=%-28r %s" % (r, f))
        if not hits:
            print("    no texture in %s references it" % at["Name"])
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
