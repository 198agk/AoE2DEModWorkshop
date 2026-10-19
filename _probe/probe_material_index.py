# -*- coding: utf-8 -*-
"""probe_material_index.py -- measure the icon chain over EVERY shipped entity.

The question this answers before any product code is written: for the units and
techs the game actually ships, how far does

    entity.IconID -> icons.json[section][%03d] -> materials.json MaterialDef
                  -> AtlasTextures[AtlasRef] entry whose RefName == TextureRef
                  -> FileName + UV rect

get us, and where does it stop?  ``_probe/ICONS_RESOLUTION.md`` settled the
rules on a research-era copy of the data; this probe re-measures them against
the CURRENT install and, crucially, measures the ONE thing the report left as a
tie-break ("use the Buildings section only when its name denotes this entity"):

* how many entities resolve through ``Units`` and how many through ``Buildings``
  when the same numeric key exists in both (they overlap on 117 keys), and
* whether the two atlases really hold different artwork (the report says all 109
  shared stems differ), because if they do, guessing the section is a visible
  bug, not a cosmetic one.

Everything printed is a count; nothing is inferred from a sample.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "_probe", "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
WID = os.path.join(GAME, "widgetui")


def load_widget_json(name):
    with io.open(os.path.join(WID, name), encoding="utf-8-sig") as fh:
        return json.load(fh)


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)
    techs = L.locate_techs(data, tail, gv)
    print("dat: %s, %d civs, %d techs" % (how, len(civs), len(techs)))

    icons = load_widget_json("icons.json")
    mat = load_widget_json("materials.json")
    atlases = {e["AtlasDef"]["Name"]: e["AtlasDef"] for e in mat["AtlasTextures"]}
    materials = {e["MaterialDef"]["Name"]: e["MaterialDef"] for e in mat["Materials"]}

    def resolve(section, key):
        """(texture dict, atlas name, material) or (None, reason, None)."""
        name = (icons.get(section) or {}).get(key)
        if not name:
            return None, "no icons.json %s[%s]" % (section, key), None
        md = materials.get(name)
        if md is None:
            return None, "no material %r" % name, None
        atlas = atlases.get(md.get("AtlasRef"))
        if atlas is None:
            return None, "no atlas %r" % md.get("AtlasRef"), name
        ref = md.get("TextureRef")
        for tex in atlas["Textures"]:
            if tex["RefName"] == ref:
                return tex, md["AtlasRef"], name
        return None, "atlas %r has no RefName %r" % (md["AtlasRef"], ref), name

    # ---- units (the id is unique across civs; take the first record) ------
    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)
    units = [u for u in by_id.values() if (u.get("icon_id") or 0) > 0]
    techs_with_icon = [t for t in techs if (t.get("icon_id") or 0) > 0]
    print("entities with icon_id > 0: %d units (of %d), %d tech records (of %d)"
          % (len(units), len(by_id), len(techs_with_icon), len(techs)))

    stats = {"unit": {}, "tech": {}}
    overlap = 0
    both_differ = 0
    both_same = 0
    for kind, rows in (("unit", units), ("tech", techs_with_icon)):
        for e in rows:
            key = "%03d" % e["icon_id"]
            if kind == "tech":
                tex, why, _ = resolve("Techs", key)
                tag = "techs_section" if tex else ("miss: %s" % (why or "").split("[")[0][:26])
                stats[kind][tag] = stats[kind].get(tag, 0) + 1
                continue
            u_tex, u_why, _ = resolve("Units", key)
            b_tex, b_why, _ = resolve("Buildings", key)
            if u_tex and b_tex:
                overlap += 1
                if u_tex["FileName"] != b_tex["FileName"]:
                    both_differ += 1
                else:
                    both_same += 1
            slot = "unit_atlas" if u_tex else ("building_atlas_only" if b_tex else "miss")
            tag = "%s|u=%s|b=%s" % (
                slot,
                "ok" if u_tex else (u_why or "")[:26],
                "ok" if b_tex else (b_why or "")[:26])
            stats[kind][tag] = stats[kind].get(tag, 0) + 1

    print("\nunit icons by outcome (a unit's key often exists in BOTH sections):")
    for k in sorted(stats["unit"], key=lambda s: -stats["unit"][s]):
        print("  %5d  %s" % (stats["unit"][k], k))
    print("\ntech icons by outcome:")
    for k in sorted(stats["tech"], key=lambda s: -stats["tech"][s]):
        print("  %5d  %s" % (stats["tech"][k], k))
    print("\nboth sections resolve the same numeric key: %d units" % overlap)
    print("  of those, the two atlas tiles are DIFFERENT files: %d" % both_differ)
    print("  of those, the same file: %d" % both_same)

    # ---- how many icon_id values never resolve at all --------------------
    miss_u = sorted({e["icon_id"] for e in units
                     if not resolve("Units", "%03d" % e["icon_id"])[0]})
    miss_t = sorted({e["icon_id"] for e in techs_with_icon
                     if not resolve("Techs", "%03d" % e["icon_id"])[0]})
    print("\ndistinct unit icon ids that do not resolve via Units: %d %s"
          % (len(miss_u), miss_u[:24]))
    print("distinct tech icon ids that do not resolve via Techs: %d %s"
          % (len(miss_t), miss_t[:24]))
    print("\nresource files referenced by the three icon atlases:")
    for atlas_name in ("ingameunits", "ingamebuildings", "ingametechs"):
        a = atlases[atlas_name]
        missing = [t["FileName"] for t in a["Textures"]
                   if not os.path.isfile(os.path.join(WID, t["FileName"].replace("/", os.sep)))]
        print("  %-16s %4d textures, %d missing on disk" % (atlas_name, len(a["Textures"]), len(missing)))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
