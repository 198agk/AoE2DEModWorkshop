#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a20_icon_namespace.py -- is the building/tech IconID really indexing the
building/tech atlas, or is it the same 0..936 namespace as unit icons?

The three atlases (ingameunits 794 / ingametechs 307 / ingamebuildings 109) all use
an embedded numeric stem.  If a building's IconID resolved equally well in
ingameunits, the mapping would be ambiguous.  Discriminate by NAME PLAUSIBILITY:
does the resolved entry's RefName actually name the entity?
"""
import json, os, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
atl = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))


def emb(a):
    out = {}
    for t in atl[a]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out


U, T, B = emb("ingameunits"), emb("ingametechs"), emb("ingamebuildings")
print("atlas numeric coverage: units=%d (min %d max %d)  techs=%d (%d..%d)  bldgs=%d (%d..%d)"
      % (len(U), min(U), max(U), len(T), min(T), max(T), len(B), min(B), max(B)))
print("ingameunits missing numbers: %d ; contiguous run? %s"
      % (len(set(range(min(U), max(U) + 1)) - set(U)),
         sorted(set(range(min(U), max(U) + 1)) - set(U))[:3]))

byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u

# ---- Name plausibility score ------------------------------------------------
def toks(s):
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return set(x for x in s.split() if len(x) > 2)


def plaus(entity_name, refname):
    """does the RefName (CamelCase, e.g. BuildingIcons007Castle) name the entity?"""
    r = re.sub(r"^(BuildingIcons|UnitIcons|TechIconsT?)\d+", "", refname or "")
    r = re.sub(r"([a-z])([A-Z])", r"\1 \2", r)
    return len(toks(r) & toks(entity_name)) > 0


print("\n=== BUILDINGS: which atlas does IconID index? ===")
bld_rows = []
for uid, per in sorted(byid.items()):
    u = per[sorted(per)[0]]
    if u.get("type") != 80:
        continue
    ic = u.get("icon_id", -1)
    if ic <= 0:
        continue
    en = SEM.get(str(uid), {}).get("en") or u.get("name")
    bld_rows.append((uid, en, ic, B.get(ic), U.get(ic)))
print("buildings with IconID>0: %d" % len(bld_rows))
nb = sum(1 for r in bld_rows if r[3])
nu = sum(1 for r in bld_rows if r[4])
print("   resolve in ingamebuildings: %d" % nb)
print("   resolve in ingameunits   : %d" % nu)
pl_b = sum(1 for r in bld_rows if r[3] and plaus(r[1] or "", r[3]["RefName"]))
pl_u = sum(1 for r in bld_rows if r[4] and plaus(r[1] or "", r[4]["RefName"]))
print("   NAME-PLAUSIBLE ingamebuildings: %d / %d (%.1f%%)"
      % (pl_b, nb, 100.0 * pl_b / max(1, nb)))
print("   NAME-PLAUSIBLE ingameunits    : %d / %d (%.1f%%)"
      % (pl_u, nu, 100.0 * pl_u / max(1, nu)))
print("\n   per-building evidence (en | iconid | ingamebuildings | ingameunits):")
for uid, en, ic, b, u2 in bld_rows[:26]:
    print("      id %-5d %-22s icon=%-4d B=%-38s U=%s"
          % (uid, (en or "")[:22], ic,
             (b["RefName"] if b else "--"),
             (u2["FileName"].rsplit("/", 1)[-1] if u2 else "--")))

# ---- TECHS -----------------------------------------------------------------
print("\n=== TECHS: which atlas does IconID index? (sample by name) ===")
TECH = json.load(open(os.path.join(HERE, "techs_raw.json"), encoding="utf-8"))
seen = set()
n = 0
for t in TECH:
    ic = t.get("icon_id", -1)
    if ic <= 0 or ic in seen:
        continue
    seen.add(ic)
    if n >= 26:
        break
    n += 1
    te = T.get(ic)
    ue = U.get(ic)
    print("   %-26s icon=%-5d TECH=%-42s UNIT=%s"
          % (t["name"][:26], ic, (te["RefName"] if te else "--"),
             (ue["FileName"].rsplit("/", 1)[-1] if ue else "--")))

# ---- is the tech icon id set disjoint from unit icon ids as VALUES? --------
tu = set(t["icon_id"] for t in TECH if t.get("icon_id", 0) > 0)
uu = set(u.get("icon_id", 0) for per in byid.values() for u in [per[sorted(per)[0]]] if u.get("icon_id", 0) > 0)
print("\ntech icon ids: %d distinct ; unit icon ids: %d distinct ; intersection: %d"
      % (len(tu), len(uu), len(tu & uu)))
print("=> the three atlases share a NUMERIC space but hold different images;")
print("   069_town_watch.dds (tech) vs 069_50730.dds (unit) are different files.")

# ---- where do unit icon ids 757..899 fall? --------------------------------
inrange = sorted(x for x in uu if 757 <= x <= 899)
print("\nunit icon ids inside the ingameunits hole 757..899: %d %s" % (len(inrange), inrange))
print("unit icon ids > 899: %s" % sorted(x for x in uu if x > 899))
print("every positive unit icon id resolves in ingameunits: %s"
      % all(x in U for x in uu))

# ---- does 900..936 exist as real .dds on disk? ----------------------------
TX = os.path.join(WID, "textures", "ingame", "units")
have = set(os.listdir(TX)) if os.path.isdir(TX) else set()
claimed = set(t["FileName"].rsplit("/", 1)[-1] for t in U.values())
print("\nwidgetui\\textures\\ingame\\units files on disk: %d" % len(have))
print("ingameunits atlas claims %d distinct .dds ; present on disk: %d ; missing: %d"
      % (len(claimed), len(claimed & have), len(claimed - have)))
print("examples of atlas-claimed files NOT on disk: %s" % sorted(claimed - have)[:8])
