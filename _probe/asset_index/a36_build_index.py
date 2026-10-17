#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a36_build_index.py -- FINAL deliverable builder (supersedes a17_build_index.py).

WHY THIS SUPERSEDES a17
  a17 had two defects, both proven wrong by a28/a31/a35:
    (1) ICONS: it resolved EVERY entity's IconID against the 'ingameunits' atlas, so
        Town Center (IconID 28) was given 'UnitIcons02850730' -- the trebuchet artwork.
        a29 proved every one of the 109 shared numeric stems holds DIFFERENT pixels in
        the two atlases (MAD 33.9-99.9), so the namespace choice is load-bearing.
    (2) BUILDINGS: it selected buildings by .dat type == 80, which wrongly includes the
        Trebuchet (class 54, art u_treb*) and wrongly excludes 138 entities whose art
        is genuinely b_* (rubble / scenario variants, e.g. Granary id 1089).

RULES IMPLEMENTED (see ASSET_INDEX_REPORT.md for the evidence of each)
  R1  dat Graphic.FileName (ends '_x1') + '.sld' == file in resources\\_common\\drs\\graphics
  R2  the '_x2' twin is the same stem with x1->x2 (7743/7743 verified)
  R3  a unit's animation SET = token substitution on the standing graphic's stem
      <stem>_<anim>_x1.sld ; slot-adjacency was disproved
  R4  entity.IconID -> icons.json section ('Buildings' preferred when its material names
      the entity, else 'Units') -> material name -> materials.json MaterialDef.AtlasRef
      -> atlas Textures[] entry by RefName -> FileName + imageTLX/TLY/BRX/BRY UV rect.
      The ATLAS IS A PROPERTY OF THE MATERIAL NAME, not of the section: icons.json's own
      Buildings['085'] = 'UnitIcons03250730' is a unit material inside the buildings
      section, which is what makes this rule expressible at all.
  R5  building = union of (type == 80) and (resolved art's dominant sld prefix is 'b_'),
      tagged per entity -- neither definition alone matches the art.
  R6  tech.IconID -> icons.json 'Techs' -> 'TechIconsT<NNN>' -> ingametechs atlas.

Outputs: index_units.json, index_buildings.json, index_techs.json, index_coverage.json
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
TECH = json.load(open(os.path.join(HERE, "techs_raw.json"), encoding="utf-8"))
SEM = json.load(open(_HERE_PATH("_probe", "semantic", "unit_names.json"),
                     encoding="utf-8"))
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ICONS = json.load(open(os.path.join(WID, "icons.json"), encoding="utf-8"))
atl = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
mats = [e.get("MaterialDef", e) for e in J["Materials"]]
MAT = {}
for m in mats:
    if m and m.get("Name"):
        MAT.setdefault(m["Name"], m)

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
        main.add(f.lower()[:-4])

slot2g = {g["slot"]: g for g in G}
dat_canon = {}
for g in G:
    f = (g["file"] or "").strip().lower()
    if f:
        s, a = canon(f)
        dat_canon["%s_%s" % (s, a) if a else s] = g

# ---------------------------------------------------------------- ICON MACHINERY
STOP = {"age", "the", "and", "of", "de", "icon", "sprite", "packed", "dead", "x", "new"}

def toks(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s or "")
    s = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s)
    return set(x for x in re.split(r"[^A-Za-z0-9]+", s.lower())
               if len(x) > 2 and not x.isdigit() and x not in STOP)

LOOSE_B = os.path.join(WID, "textures", "ingame", "buildings")
BLABEL = {}
if os.path.isdir(LOOSE_B):
    for f in os.listdir(LOOSE_B):
        h = f.split("_")[0]
        if h.isdigit():
            BLABEL[int(h)] = re.sub(r"^[0-9]+_", "", f.rsplit(".", 1)[0])
IUNITS, IBLD, ITECH = ICONS.get("Units", {}), ICONS.get("Buildings", {}), ICONS.get("Techs", {})

_STEM_FALLBACK = collections.Counter()

def resolve_material(mname):
    md = MAT.get(mname)
    if not md:
        return {"material": mname, "resolved": False,
                "why": "no MaterialDef named %r in materials.json" % mname}
    atlas = md.get("AtlasRef")
    if atlas is None:
        return {"material": mname, "resolved": False, "why": "MaterialDef has no AtlasRef"}
    at = atl.get(atlas)
    if at is None:
        return {"material": mname, "resolved": False,
                "why": "AtlasRef %r absent from AtlasTextures" % atlas}
    tex = next((t for t in at["Textures"] if t.get("RefName") == mname), None)
    if tex is None:
        # numeric-stem fallback, as in a33_icons_resolve.py:92-100 (alias materials)
        m = re.search(r"(\d{3,4})\D*$", mname)
        if m:
            for t in at["Textures"]:
                s = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
                if s.split("_")[0] == m.group(1):
                    tex = t
                    _STEM_FALLBACK[(mname, atlas)] += 1
                    break
    if tex is None:
        return {"material": mname, "atlas": atlas, "resolved": False,
                "why": "no Texture in atlas %r with RefName %r" % (atlas, mname)}
    return {"material": mname, "atlas": atlas, "RefName": tex["RefName"],
            "TextureFileName": tex["FileName"],
            "uv": {"x1": float(tex["imageTLX"]), "y1": float(tex["imageTLY"]),
                   "x2": float(tex["imageBRX"]), "y2": float(tex["imageBRY"])},
            "atlas_max": [at.get("MaxWidth"), at.get("MaxHeight")], "resolved": True}

def icon_for(icon_id, entity_en, section_hint="Units"):
    """R4: icons.json section -> material -> materials.json -> atlas entry + UV."""
    if not isinstance(icon_id, int) or icon_id <= 0:
        return None
    k = "%03d" % icon_id
    section = why = None
    if section_hint == "Buildings" and k in IBLD:
        # EXACTLY a33's test (a33_icons_resolve.py:136-140).  Do NOT union the candidate
        # material's own tokens into the entity side: every "BuildingIcons*" name then
        # self-matches and the test fires for all 117 building ids (that regression gave
        # Archer -> BuildingIcons017Market3).
        lab = BLABEL.get(icon_id, "")
        if (toks(entity_en) & toks(lab)) or (toks(entity_en) & toks(IBLD[k])):
            section, why = "Buildings", ("building entry %s (%r) denotes %r" % (k, lab, entity_en))
    if section is None and k in IUNITS:
        section = "Units"
        why = ("no denoting building entry for %s; units entry" % k if k in IBLD
               else "IconID %s absent from icons.json.Buildings" % k)
    if section is None:
        return {"icon_id": icon_id, "resolved": False,
                "why": "IconID %s present in neither icons.json.Units nor .Buildings" % k}
    mname = (IBLD if section == "Buildings" else IUNITS)[k]
    r = resolve_material(mname)
    r.update({"icon_id": icon_id, "icons_json_section": section, "why": why})
    return r

BLD_NICE = {int(k): v for k, v in IBLD.items() if v}

def sprite_block(u):
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
        for cand in (("%s_%s_x1" % (s, a)) if a else nm, nm + "_x1", nm):
            if cand in main:
                direct = cand + ".sld"
                break
        if direct:
            rec["resolution"] = "direct"
            rec["sld_x1"] = direct
            rec["sld_x2"] = direct.replace("_x1.sld", "_x2.sld")
        else:
            rec["resolution"] = "unresolved"
        if a and not rec.get("sld_x1"):
            anims = {}
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

def EN_of(u, uid):
    return (SEM.get(str(uid)) or {}).get("en") or u.get("name") or "?"

def files_of(sp):
    out = []
    for f, r in sp.items():
        if r.get("sld_x1"):
            out.append(r["sld_x1"])
        for a in (r.get("animations") or {}).values():
            if a.get("sld_x1"):
                out.append(a["sld_x1"])
    return out

def dominant_prefix(sp):
    fs = files_of(sp)
    if not fs:
        return None
    return collections.Counter(x.split("_")[0] for x in fs).most_common(1)[0][0]

# ------------------------------------------------------------------- UNITS
units_out = {}
cov = collections.Counter()
res_hist = collections.Counter()
for uid, per in sorted(byid.items()):
    civ0 = sorted(per)[0]
    u = per[civ0]
    en = EN_of(u, uid)
    sp = sprite_block(u)
    ok = any(r.get("resolution", "").startswith(("direct", "substituted")) for r in sp.values())
    for f, r in sp.items():
        res_hist[r.get("resolution")] += 1
    # section_hint "Buildings" == TEST BUILDINGS FIRST, then fall back to Units.
    # Passing "Units" here was the bug the a38 cross-check caught: it forced every
    # entity onto the unit atlas and gave Town Center the trebuchet tile.
    ic = icon_for(u.get("icon_id"), en, "Buildings")
    sem = SEM.get(str(uid), {})
    cov["unit ids"] += 1
    if ok:
        cov["sprite mapped"] += 1
    else:
        cov["sprite FAILED"] += 1
    if ic and ic.get("resolved"):
        cov["icon mapped"] += 1
    else:
        cov["icon FAILED"] += 1
    if ok and ic and ic.get("resolved"):
        cov["both sprite and icon"] += 1
    if not ok and not (ic and ic.get("resolved")):
        cov["neither"] += 1
    variants = {}
    for ci in sorted(per):
        uu = per[ci]
        if uu.get("icon_id") != u.get("icon_id") or uu.get("name") != u.get("name"):
            variants.setdefault("civs", {})[CIVNAME[ci]] = {
                "internal_name": uu.get("name"), "icon_id": uu.get("icon_id"),
                "icon": icon_for(uu.get("icon_id"), EN_of(uu, uid), "Buildings")}
    units_out[str(uid)] = {
        "unit_id": uid, "internal_name": u.get("name"), "en": sem.get("en"),
        "zh": sem.get("zh"), "type": u.get("type"), "class": u.get("class"),
        "hit_points": u.get("hit_points"), "civ_count": len(per),
        "sprite_prefix": dominant_prefix(sp),
        "sprites": sp, "icon": ic, "per_civ_variants": variants or None,
    }

# --------------------------------------------------------------- BUILDINGS
bld_out = {}
bcov = collections.Counter()
for uid_s, rec in units_out.items():
    uid = int(uid_s)
    pre = rec["sprite_prefix"]
    t80 = rec["type"] == 80
    artb = pre == "b"
    if not (t80 or artb):
        continue
    bcov["buildings (union)"] += 1
    if t80 and artb:
        bcov["  def: both type80 and b_ art"] += 1
        tag = "type80+b_art"
    elif t80:
        bcov["  def: type80 only (art NOT b_)"] += 1
        tag = "type80_only"
    else:
        bcov["  def: b_ art only (type != 80)"] += 1
        tag = "b_art_only"
    if artb:
        bcov["sprite mapped (b_ art)"] += 1
    elif any(r.get("resolution", "").startswith(("direct", "substituted"))
             for r in rec["sprites"].values()):
        bcov["sprite mapped (non-b_ art)"] += 1
    name = rec["en"] or rec["internal_name"] or ""
    ic_b = icon_for((rec["icon"] or {}).get("icon_id", 0), name, "Buildings")
    if ic_b and ic_b.get("resolved"):
        bcov["icon mapped"] += 1
    else:
        bcov["icon FAILED"] += 1
    if ic_b and ic_b.get("atlas") == "ingamebuildings":
        bcov["  icon from ingamebuildings"] += 1
    elif ic_b and ic_b.get("atlas") == "ingameunits":
        bcov["  icon from ingameunits (fallback)"] += 1
    bld_out[uid_s] = {
        "building_id": uid, "internal_name": rec["internal_name"], "en": rec["en"],
        "zh": rec["zh"], "hit_points": rec["hit_points"], "type": rec["type"],
        "class": rec["class"], "building_definition": tag, "sprite_prefix": pre,
        "sprites": rec["sprites"], "icon": ic_b,
    }

# ------------------------------------------------------------------- TECHS
techs_out = {}
tcov = collections.Counter()
for t in TECH:
    key = "%d|civ%d" % (t.get("effect_id", -1), t.get("civ", -1))
    iid = t.get("icon_id")
    ic = None
    if isinstance(iid, int) and iid > 0:
        k = "%03d" % iid
        if k in ITECH:
            ic = resolve_material(ITECH[k])
            ic["icon_id"] = iid
            ic["icons_json_section"] = "Techs"
        else:
            ic = {"icon_id": iid, "resolved": False,
                  "why": "IconID %s absent from icons.json.Techs" % k}
    techs_out.setdefault(key, {
        "name": t.get("name"), "civ": t.get("civ"), "type": t.get("type"),
        "effect_id": t.get("effect_id"), "icon_id": iid, "icon": ic,
        "research_locations": t.get("research_locations")})
    tcov["tech records"] += 1
    if isinstance(iid, int) and iid > 0:
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

RULES = {
    "R1": "dat Graphic.FileName (ends '_x1') + '.sld' == file in "
          "resources\\_common\\drs\\graphics (8185/8296 DE-style = 98.66%)",
    "R2": "x2 twin = same stem with x1->x2 (7743/7743 verified)",
    "R3": "animation set = token substitution on the standing graphic stem; "
          "slot-adjacency disproved",
    "R4": "entity.IconID -> icons.json section ('Buildings' if its entry names the entity, "
          "else 'Units') -> material name -> materials.json MaterialDef.AtlasRef -> atlas "
          "Texture by RefName -> FileName + imageTLX/TLY/BRX/BRY. The atlas follows the "
          "MATERIAL NAME, not the section (icons.json Buildings['085']='UnitIcons03250730').",
    "R5": "building = union of (type == 80) and (dominant resolved sld prefix == 'b_'); "
          "tagged per entity because neither definition alone matches the art",
    "R6": "tech.IconID -> icons.json 'Techs' -> 'TechIconsT<NNN>' -> ingametechs atlas",
}
dump("index_units.json", units_out)
dump("index_buildings.json", bld_out)
dump("index_techs.json", techs_out)
dump("index_coverage.json", {
    "units": dict(cov), "buildings": dict(bcov), "techs": dict(tcov),
    "sprite_field_resolution_histogram": dict(res_hist), "rules": RULES,
    "note_icon_denominator": ("1,344 of 2,693 unit ids carry IconID>0; the other 1,349 "
                              "have IconID 0 or -1 and therefore NO icon by construction, "
                              "which is not a resolution failure."),
})

print("\n=== UNIT COVERAGE (denominator 2693) ===")
for k in ["unit ids", "sprite mapped", "sprite FAILED", "icon mapped", "icon FAILED",
          "both sprite and icon", "neither"]:
    print("   %-22s %d" % (k, cov[k]))
print("\n=== per-sprite-field resolution histogram ===")
for k, v in res_hist.most_common():
    print("   %-34s %d" % (k, v))
print("\n=== BUILDING COVERAGE ===")
for k in sorted(bcov):
    print("   %-40s %d" % (k, bcov[k]))
print("\n=== TECH COVERAGE ===")
for k in ["tech records", "with icon_id>0", "icon resolved", "icon UNRESOLVED"]:
    print("   %-22s %d" % (k, tcov[k]))
