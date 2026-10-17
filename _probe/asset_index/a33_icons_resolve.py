#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a33_icons_resolve.py -- resolve IconID via the game's OWN icon table (icons.json).

THE INSIGHT
  material names embed their atlas: 'UnitIcons02850730' (units atlas) vs
  'BuildingIcons028TownCenter' (buildings atlas).  And icons.json.Buildings["085"] is
  'UnitIcons03250730' -- a UNIT material sitting in the BUILDINGS section.  So the
  atlas is a property of the MATERIAL, not of the section.  Chain:

      entity.IconID  --section-->  icons.json material name  --materials.json-->
      AtlasRef + RefName + Textures[].FileName + UV rect

  The only choice left is which SECTION to read.  Both sections contain ids 000-116
  ('Units' is a superset 000-999), so for those ids the section is load-bearing.
  Discriminator, tested here: the building-section material name DENOTES the entity
  (checked against the game's own author-written loose label, e.g. 028_town_center.DDS).

OUTPUT: icon_resolution.json -- per entity the chosen section/material/atlas/uv + why.
"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ICONS = json.load(open(os.path.join(WID, "icons.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))

# material name -> MaterialDef
MAT = {}
for m in J["Materials"]:
    md = m.get("MaterialDef")
    if md and md.get("Name"):
        MAT.setdefault(md["Name"], md)

# atlas embeddings: atlas -> {embedded NNN: Texture}
def emb(atlas_name):
    out = {}
    for t in ATLS[atlas_name]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out


EMB = {name: emb(name) for name in ATLS}

# the game's own author-written label for building icon N, from the loose file on disk
LOOSE_B = os.path.join(WID, "textures", "ingame", "buildings")
BLABEL = {}
for f in os.listdir(LOOSE_B):
    h = f.split("_")[0]
    if h.isdigit():
        BLABEL[int(h)] = re.sub(r"^[0-9]+_", "", f.rsplit(".", 1)[0])

STOP = {"age", "the", "and", "of", "de", "icon", "sprite", "packed", "dead", "x", "new"}


def toks(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s or "")
    s = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s)
    return set(x for x in re.split(r"[^A-Za-z0-9]+", s.lower())
               if len(x) > 2 and not x.isdigit() and x not in STOP)


def match(entity_en, label):
    return len(toks(entity_en) & toks(label)) > 0


def resolve_material(mname):
    """material name -> atlas/refname/uv/texture, via materials.json."""
    md = MAT.get(mname)
    if not md:
        return {"material": mname, "resolved": False, "why": "no MaterialDef with this name"}
    atlas = md.get("AtlasRef")
    if atlas is None:
        return {"material": mname, "resolved": False, "why": "MaterialDef has no AtlasRef",
                "atlas_def": md.get("Name")}
    at = ATLS.get(atlas)
    if at is None:
        return {"material": mname, "resolved": False, "why": "AtlasRef %r not in AtlasTextures" % atlas}
    # find the texture whose RefName == material name (RefName is unique per Material)
    tex = None
    for t in at["Textures"]:
        if t.get("RefName") == mname or t.get("RefName") == md.get("Name"):
            tex = t
            break
    if tex is None:
        # fall back: the material name embeds NNN, match on that
        m = re.search(r"(\d{3,4})\D*$", mname)
        stem = mname
        for t in at["Textures"]:
            s = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if s.split("_")[0] == (m.group(1) if m else ""):
                stem, tex = mname, t
                break
    if tex is None:
        return {"material": mname, "atlas": atlas, "resolved": False,
                "why": "material not found among atlas Textures (alias?)",
                "atlas_texture_count": len(at["Textures"])}
    uv = {"x1": float(tex["imageTLX"]), "y1": float(tex["imageTLY"]),
          "x2": float(tex["imageBRX"]), "y2": float(tex["imageBRY"])}
    return {"material": mname, "atlas": atlas, "RefName": tex.get("RefName"),
            "TextureFileName": tex["FileName"], "uv": uv, "resolved": True,
            "atlas_max": [at.get("MaxWidth"), at.get("MaxHeight")],
            "atlas_default_source": at.get("DefaultSource")}


byid = {}
for civ in C:
    for x in civ["units"]:
        byid.setdefault(x["id"], x)


def EN(u):
    return (SEM.get(str(u["id"])) or {}).get("en") or u.get("name") or "?"


UNITS, BLD = ICONS.get("Units", {}), ICONS.get("Buildings", {})
print("icons.json sections: Units=%d Buildings=%d" % (len(UNITS), len(BLD)))

ents = sorted([u for u in byid.values() if u.get("icon_id", -1) > 0], key=lambda x: x["id"])
print("entities with IconID>0: %d" % len(ents))

sect = collections.Counter()
out = {}
for u in ents:
    n = u["icon_id"]
    en = EN(u)
    k = "%03d" % n
    choice, why = None, None
    if k in BLD:
        lab = BLABEL.get(n, "")
        if match(en, lab) or match(en, BLD[k]):
            choice = ("Buildings", BLD[k])
            why = "building entry %s (%r) denotes %r" % (k, lab or BLD[k], en)
    if choice is None and k in UNITS:
        choice = ("Units", UNITS[k])
        why = ("no denoting building entry; units entry %s" % k if k in BLD
               else "id has no Buildings entry; units entry %s" % k)
    if choice is None:
        sect["NO SECTION"] += 1
        out[u["id"]] = {"unit_id": u["id"], "en": en, "icon_id": n, "resolved": False,
                        "why": "IconID absent from both icons.json sections"}
        continue
    section, mname = choice
    r = resolve_material(mname)
    r.update({"unit_id": u["id"], "en": en, "icon_id": n, "section": section, "why": why,
              "type": u.get("type"), "class": u.get("class")})
    out[u["id"]] = r
    sect[(section, r.get("atlas"), r["resolved"])] += 1

print("\n=== routing outcome ===")
for k in sorted(sect, key=lambda x: str(x)):
    print("  section=%-10s atlas=%-18s resolved=%-5s  n=%d" % (k[0], k[1], k[2], sect[k]))
ok = sum(1 for r in out.values() if r.get("resolved"))
print("  resolved=%d / %d  (unresolved=%d)" % (ok, len(ents), len(ents) - ok))

print("\n=== decisive entities (raw label shown so the reader can audit the match) ===")
print("%-6s %-26s %-4s %-4s %-6s %-10s %-30s %-9s" %
      ("id", "english name", "type", "class", "icon", "section", "material", "atlas"))
for uid in (42, 71, 12, 82, 70, 50, 79, 72, 4, 83, 331, 444, 1712, 2442, 2068, 235, 199, 1187, 1690, 682):
    r = out.get(uid)
    if not r:
        print("  id %-5d  (no IconID>0)" % uid)
        continue
    lab = BLABEL.get(r["icon_id"], "--")
    print("%-6s %-26s %-4s %-4s %-6s %-10s %-30s %-9s  label=%s%s"
          % (uid, r["en"][:26], r.get("type", "?"), r.get("class", "?"), r["icon_id"],
             r.get("section", "-"), (r.get("material") or "")[:30], r.get("atlas", "-"),
             lab, "" if r.get("resolved") else "  UNRESOLVED: %s" % r.get("why")))

print("\n=== unresolved entities, grouped by why ===")
un = collections.Counter()
for r in out.values():
    if not r.get("resolved"):
        un[r.get("why")] += 1
for w, c in un.most_common():
    print("  %-60s %d" % (w[:60], c))

# distribution of IconID values seen in icons.json sections
print("\n=== IconID value range among resolved entities ===")
ids = [r["icon_id"] for r in out.values() if r.get("resolved")]
print("  min=%d max=%d  distinct=%d" % (min(ids), max(ids), len(set(ids))))
over = sorted(set(i for i in ids if i > 999))
print("  ids >999 (outside Units section 000-999): %s" % over[:20])

json.dump(out, open(os.path.join(HERE, "icon_resolution.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote icon_resolution.json")
