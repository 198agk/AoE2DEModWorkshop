#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a35_building_rule.py -- decide how to define "building" for the index, empirically.

WHY
  a17 selected buildings by .dat  unit.type == 80.  a28/a31 showed that set includes the
  Trebuchet (class 54), which is a siege UNIT, and that the game itself stores the packed
  trebuchet as type 80.  So two candidate definitions exist:
     T80   : rec.type == 80                      (the .dat's own placement type)
     BPFX  : the resolved art actually lives in b_*.sld files (art-based, ground truth)
  This script measures both and their disagreement, and also probes the TECH icon link
  (icons.json 'Techs' section -> TechIconsT<NNN> -> ingametechs) so the final builder can
  use the same chain for techs.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
GFX = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ICONS = json.load(open(os.path.join(WID, "icons.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
TECH = json.load(open(os.path.join(HERE, "techs_raw.json"), encoding="utf-8"))
SEM = json.load(open(_HERE_PATH("_probe", "semantic", "unit_names.json"),
                     encoding="utf-8"))

main = set(f[:-4] for f in os.listdir(GFX) if f.endswith(".sld"))

byid = {}
for civ in C:
    for x in civ["units"]:
        byid.setdefault(x["id"], x)

def EN(u):
    return (SEM.get(str(u["id"])) or {}).get("en") or u.get("name") or "?"

SPRITE_FIELDS = [k for k in next(iter(byid.values())).keys()
                 if k.endswith("_graphic") or k in ("standing_1", "standing_2", "dying", "undead")]

def prefix_of(u):
    """the dominant sld prefix of this entity's own resolved art files."""
    for f in ("standing_1", "standing_2", "dying"):
        v = u.get(f)
        if isinstance(v, int) and v >= 0:
            pass
    return None

print("=== candidate building definitions ===")
t80 = [u for u in byid.values() if u.get("type") == 80]
print("  type==80 entities            : %d" % len(t80))
print("  type==70 entities            : %d" % sum(1 for u in byid.values() if u.get("type") == 70))
print("  type histogram               : %s"
      % dict(collections.Counter(u.get("type") for u in byid.values())))
print("  type==80 class histogram     : %s"
      % dict(collections.Counter(u.get("class") for u in t80)))

# compare with the art: which entities' sprite sets are b_* ?
sp = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
bpfx, otherpfx = [], collections.Counter()
disagree_t80_notb, disagree_bnott80 = [], []
for uid, rec in sp.items():
    files = []
    for f, r in (rec.get("sprites") or {}).items():
        if r.get("sld_x1"):
            files.append(r["sld_x1"])
        for a in (r.get("animations") or {}).values():
            if a.get("sld_x1"):
                files.append(a["sld_x1"])
    if not files:
        continue
    p = collections.Counter(x.split("_")[0] for x in files).most_common(1)[0][0]
    otherpfx[p] += 1
    u = byid.get(int(uid))
    isb = (p == "b")
    if isb:
        bpfx.append(int(uid))
    if u is not None and (u.get("type") == 80) != isb:
        (disagree_t80_notb if u.get("type") == 80 else disagree_bnott80).append(
            (int(uid), EN(u)[:30], u.get("type"), u.get("class"), p))

print("\n  dominant-sld-prefix histogram among sprite-mapped entities: %s" % dict(otherpfx))
print("  entities whose art is b_*    : %d" % len(bpfx))
print("  type==80 but art not b_*     : %d" % len(disagree_t80_notb))
for x in disagree_t80_notb[:40]:
    print("       id %-5d %-30s type=%-3s class=%-3s prefix=%s" % x)
print("  art b_* but type!=80         : %d" % len(disagree_bnott80))
for x in disagree_bnott80[:40]:
    print("       id %-5d %-30s type=%-3s class=%-3s prefix=%s" % x)

# ---- TECH icon link ----
print("\n=== tech icon linkage via icons.json 'Techs' ===")
T = ICONS.get("Techs", {})
print("  icons.json.Techs entries: %d" % len(T))
pref = collections.Counter(v.split("0")[0] for v in T.values())
print("  material-name prefixes: %s" % dict(collections.Counter(
    re.sub(r"\d.*$", "", v) for v in T.values())))
MAT = {}
for m in J["Materials"]:
    md = m.get("MaterialDef")
    if md and md.get("Name"):
        MAT.setdefault(md["Name"], md)
atlas_of = collections.Counter()
missing = 0
for k, v in T.items():
    md = MAT.get(v)
    if not md:
        missing += 1
        continue
    atlas_of[md.get("AtlasRef")] += 1
print("  -> AtlasRef of tech materials: %s   (no MaterialDef: %d)" % (dict(atlas_of), missing))
EMB_T = {}
for t in ATLS["ingametechs"]["Textures"]:
    stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
    h = re.match(r"^0*(\d+)", stem)
    if h:
        EMB_T.setdefault(int(h.group(1)), []).append((stem, t["RefName"]))
print("  ingametechs embedded stems: %d distinct numeric" % len(EMB_T))
withid = [t for t in TECH if isinstance(t.get("icon_id"), int) and t["icon_id"] > 0]
print("  tech records with icon_id>0: %d (of %d)" % (len(withid), len(TECH)))
ins = collections.Counter()
for t in withid:
    k = "%03d" % t["icon_id"]
    ins["in icons.json.Techs" if k in T else "NOT in Techs"] += 1
print("  %s" % dict(ins))
print("\n  sample tech resolution:")
for t in withid[:12]:
    k = "%03d" % t["icon_id"]
    m = T.get(k)
    md = MAT.get(m) if m else None
    print("     icon=%-4s Techs[%s]=%-22s -> AtlasRef=%s" %
          (t["icon_id"], k, m, md.get("AtlasRef") if md else "NO MaterialDef"))
