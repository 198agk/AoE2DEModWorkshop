#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a17_build_index.py -- build the final deliverables.

Outputs (all in this scratch dir):
  index_units.json      unit id -> sprite files (per animation, per civ) + icon atlas entry
  index_buildings.json  building id -> sprite files + icon atlas entry
  index_techs.json      tech id -> icon atlas entry
  index_coverage.json   honest coverage numbers + failure taxonomy

Correspondence rules used (all established empirically; see ASSET_INDEX_REPORT.md):
  R1  dat Graphic.FileName  ==  the .sld file stem, MINUS extension, on disk in
      resources\\_common\\drs\\graphics.  The field already ends in '_x1'.
  R2  the '_x2' variant is the same string with 'x1'->'x2' (7743/7743 verified).
  R3  the game's animation SET for a unit is found by substituting the animation
      token in the standing graphic's stem: <stem>_<anim>_x1.sld (verified by the
      cross-field stem-identity test in a15).
  R4  unit.IconID indexes the 'ingameunits' atlas by the EMBEDDED NUMBER NNN in
      RefName 'UnitIcons<NNN>50730' / FileName '<NNN>_50730.dds' (724/724 ids).
  R5  tech.IconID indexes 'ingametechs' the same way (177/180 ids).
  R6  building.IconID indexes 'ingamebuildings' by embedded number.
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
TECH = json.load(open(os.path.join(HERE, "techs_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
atl = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
mats = [e.get("MaterialDef", e) for e in J["Materials"]]

ANIMS = set("""idlea idleb idlec walka walkb walkc attacka attackb attackc
deatha deathb decaya constr rubble destruction flag garrison""".split())
SPRITE_ANIMS = ["idlea", "idleb", "idlec", "walka", "walkb", "attacka", "attackb",
                "attackc", "deatha", "decaya"]


def canon(name):
    n = (name or "").strip().lower()
    if n.endswith(".sld"):
        n = n[:-4]
    if n.endswith("_x1") or n.endswith("_x2"):
        n = n[:-3]
    i = n.rfind("_")
    if i > 0 and n[i + 1:] in ANIMS:
        return n[:i], n[i + 1:]
    return n, None


main = set()
for f in os.listdir(GFXDIR):
    if f.lower().endswith(".sld"):
        n = f.lower()[:-4]
        main.add(n)

slot2g = {g["slot"]: g for g in G}
dat_canon = {}
for g in G:
    f = (g["file"] or "").strip().lower()
    if f:
        s, a = canon(f)
        dat_canon["%s_%s" % (s, a) if a else s] = g


def emb(atlas_name, want_material=False):
    out = {}
    for t in atl[atlas_name]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            rec = {
                "atlas": atlas_name,
                "RefName": t["RefName"],
                "TextureFileName": t["FileName"],
                "uv": {"x1": float(t["imageTLX"]), "y1": float(t["imageTLY"]),
                       "x2": float(t["imageBRX"]), "y2": float(t["imageBRY"])},
            }
            m = next((m for m in mats if m.get("Name") == t["RefName"]), None)
            if m:
                rec["Material"] = {"Name": m.get("Name"), "Blend": m.get("Blend"),
                                   "TextureRef": m.get("TextureRef"),
                                   "AtlasRef": m.get("AtlasRef")}
            out[int(h)] = rec
    return out


EMB_UNIT = emb("ingameunits")
EMB_TECH = emb("ingametechs")
EMB_BLD = emb("ingamebuildings")
ATLAS_SRC = {n: {"SD": atl[n].get("SDSource"), "HD": atl[n].get("HDSource"),
                 "UHD": atl[n].get("UHDSource"), "Default": atl[n].get("DefaultSource")}
             for n in ("ingameunits", "ingametechs", "ingamebuildings")}

ALL_FIELDS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic",
              "attack_graphic2", "garrison_graphic", "spawning_graphic",
              "upgrade_graphic", "hero_glow_graphic", "idle_attack_graphic",
              "special_graphic", "construction_graphic", "snow_graphic",
              "destruction_graphic", "destruction_rubble_graphic",
              "researching_graphic", "research_completed_graphic"]

byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u
CIVNAME = [c["name"] for c in C]


def sprite_block(u):
    """-> {field: {"graphic_slot","FileName","direct_sld","animations":{...}}}"""
    out = {}
    for f in ALL_FIELDS:
        v = u.get(f)
        if not isinstance(v, int):
            continue
        rec = {"graphic_slot": v}
        if v < 0:
            rec["resolution"] = "unset(-1 sentinel)"
            out[f] = rec
            continue
        g = slot2g.get(v)
        if g is None:
            rec["resolution"] = "slot not decoded"
            out[f] = rec
            continue
        nm = (g["file"] or "").strip().lower()
        rec["FileName"] = nm
        if not nm:
            rec["resolution"] = "graphic has no FileName"
            out[f] = rec
            continue
        s, a = canon(nm)
        direct = None
        for cand in ("%s_%s_x1" % (s, a) if a else nm, nm + "_x1", nm):
            if cand in main:
                direct = cand + ".sld"
                break
        if direct:
            rec["resolution"] = "direct"
            rec["sld_x1"] = direct
            rec["sld_x2"] = direct.replace("_x1.sld", "_x2.sld")
        else:
            rec["resolution"] = "unresolved"
        anims = {}
        if a and not rec.get("sld_x1"):
            for w in SPRITE_ANIMS:
                cand = "%s_%s" % (s, w)
                if cand in main:
                    dg = dat_canon.get(cand)
                    anims[w] = {"sld_x1": cand + "_x1.sld", "sld_x2": cand + "_x2.sld",
                                "graphic_slot": dg["slot"] if dg else None,
                                "frame_count": dg["frame_count"] if dg else None,
                                "angle_count": dg["angle_count"] if dg else None}
            if anims:
                rec["resolution"] = "substituted-by-animation-token"
                rec["animations"] = anims
        out[f] = rec
    return out


def icon_for(icon_id, table):
    if not isinstance(icon_id, int) or icon_id <= 0:
        return None
    e = table.get(icon_id)
    if not e:
        return {"icon_id": icon_id, "resolved": False}
    r = dict(e)
    r["icon_id"] = icon_id
    r["resolved"] = True
    r["atlas_source"] = ATLAS_SRC[e["atlas"]]
    return r


# ------------------------------------------------------------------- UNITS
units_out = {}
cov = collections.Counter()
for uid, per in sorted(byid.items()):
    civ0 = sorted(per)[0]
    u = per[civ0]
    sp = sprite_block(u)
    ok = any(r.get("resolution", "").startswith(("direct", "substituted")) for r in sp.values())
    ic = icon_for(u.get("icon_id"), EMB_UNIT)
    semantic = SEM.get(str(uid), {})
    cov["unit ids"] += 1
    if ok:
        cov["sprite mapped"] += 1
    if ic and ic.get("resolved"):
        cov["icon mapped"] += 1
    if ok and ic and ic.get("resolved"):
        cov["both sprite and icon"] += 1
    if not ok and not (ic and ic.get("resolved")):
        cov["neither"] += 1
    # per-civ differences
    variants = {}
    for ci in sorted(per):
        uu = per[ci]
        if uu.get("icon_id") != u.get("icon_id") or uu.get("name") != u.get("name"):
            variants.setdefault("civs", {})[CIVNAME[ci]] = {
                "internal_name": uu.get("name"), "icon_id": uu.get("icon_id"),
                "icon": icon_for(uu.get("icon_id"), EMB_UNIT)}
    units_out[str(uid)] = {
        "unit_id": uid,
        "internal_name": u.get("name"),
        "en": semantic.get("en"),
        "zh": semantic.get("zh"),
        "type": u.get("type"), "class": u.get("class"),
        "hit_points": u.get("hit_points"),
        "civ_count": len(per),
        "sprites": sp,
        "icon": ic,
        "per_civ_variants": variants or None,
    }

# --------------------------------------------------------------- BUILDINGS
bld_out = {}
bcov = collections.Counter()
for uid, rec in units_out.items():
    if rec["type"] != 80:
        continue
    bcov["buildings"] += 1
    sp = rec["sprites"]
    u = byid[int(uid)][sorted(byid[int(uid)])[0]]
    ok = any(r.get("resolution", "").startswith(("direct", "substituted")) for r in sp.values())
    if ok:
        bcov["sprite mapped"] += 1
    ic_u = rec["icon"]
    ic_b = icon_for(u.get("icon_id"), EMB_BLD)
    if ic_b and ic_b.get("resolved"):
        bcov["ingamebuildings icon mapped"] += 1
    bld_out[uid] = {
        "building_id": int(uid), "internal_name": rec["internal_name"],
        "en": rec["en"], "zh": rec["zh"], "hit_points": rec["hit_points"],
        "sprites": sp,
        "icon_ingameunits": ic_u,
        "icon_ingamebuildings": ic_b,
    }

# ------------------------------------------------------------------- TECHS
techs_out = {}
tcov = collections.Counter()
for t in TECH:
    key = "%d|civ%d" % (t.get("effect_id", -1), t.get("civ", -1))
    ic = icon_for(t.get("icon_id"), EMB_TECH)
    techs_out.setdefault(key, {
        "name": t.get("name"), "civ": t.get("civ"), "type": t.get("type"),
        "effect_id": t.get("effect_id"), "icon_id": t.get("icon_id"), "icon": ic,
        "research_locations": t.get("research_locations"),
    })
    tcov["tech records"] += 1
    if t.get("icon_id", 0) > 0:
        tcov["with icon_id>0"] += 1
        if ic and ic.get("resolved"):
            tcov["icon resolved"] += 1
        else:
            tcov["icon UNRESOLVED"] += 1

# ------------------------------------------------------------------- OUTPUT
def dump(name, obj):
    p = os.path.join(HERE, name)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print("wrote %-24s %9d bytes" % (name, os.path.getsize(p)))


dump("index_units.json", units_out)
dump("index_buildings.json", bld_out)
dump("index_techs.json", techs_out)
dump("index_coverage.json", {
    "units": dict(cov), "buildings": dict(bcov), "techs": dict(tcov),
    "rules": {
        "R1": "dat Graphic.FileName (ends in '_x1') + '.sld' == file in resources\\_common\\drs\\graphics",
        "R2": "x2 twin = same name with x1->x2 (7743/7743 verified)",
        "R3": "animation set = token substitution on the standing graphic stem",
        "R4": "unit.IconID -> ingameunits atlas entry by embedded number NNN",
        "R5": "tech.IconID -> ingametechs atlas entry by embedded number NNN",
        "R6": "building.IconID -> ingamebuildings atlas entry by embedded number NNN",
    },
})

print("\n=== COVERAGE ===")
for k in ["unit ids", "sprite mapped", "icon mapped", "both sprite and icon", "neither"]:
    print("   units    %-24s %d" % (k, cov[k]))
for k in ["buildings", "sprite mapped", "ingamebuildings icon mapped"]:
    print("   buildings %-23s %d" % (k, bcov[k]))
for k in ["tech records", "with icon_id>0", "icon resolved", "icon UNRESOLVED"]:
    print("   techs    %-24s %d" % (k, tcov[k]))
