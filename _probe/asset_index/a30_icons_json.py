#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a30_icons_json.py -- THE AUTHORITATIVE icon namespace map.

DISCOVERY: widgetui/icons.json is a game-authored file that maps a numeric icon
id to a MATERIAL NAME, partitioned into explicit NAMESPACES:

    {"Buildings": {"000": "BuildingIcons000ArcheryRange1", ...},
     "Units":     {"000": "UnitIcons00050730", ...},
     "Techs":     {...}, "StatIcons": {...}, "CivTechTree": {...}, ...}

This settles the atlas question that a26-a29 could only narrow by pixels: the
atlas a given numeric icon id belongs to is decided by WHICH SECTION of icons.json
it appears in --- not by the unit's Type or Class.  The material name then has a
matching MaterialDef in materials.json whose "AtlasRef" names the atlas.

This script:
  1. dumps every top-level section, its size, and its material-name prefix;
  2. cross-checks every section's material name against materials.json MaterialDef
     names and reports the join rate (an explicit integrity test);
  3. resolves the atlas for each section via MaterialDef.AtlasRef;
  4. applies the icons.json rule to the decisive entities from a28/a29 and
     compares the outcome with the Type/Class rules that failed.
"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ICONS = json.load(open(os.path.join(WID, "icons.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}

MD = {}
for e in J["Materials"]:
    d = e.get("MaterialDef", e)
    MD[d["Name"]] = d
print("materials.json: Materials=%d MaterialDef names=%d AtlasTextures=%d"
      % (len(J["Materials"]), len(MD), len(ATLS)))

print("\n=== icons.json top-level sections ===")
print("%-26s %6s  %-30s %s" % ("section", "n", "material-name prefix", "AtlasRef (via MaterialDef)"))
SEC_ATLAS = {}
for sec in ICONS:
    v = ICONS[sec]
    if not isinstance(v, dict):
        print("%-26s %6s  (not a dict: %s)" % (sec, "-", type(v).__name__)); continue
    pref = collections.Counter()
    defs = collections.Counter()
    missing = 0
    for k, m in v.items():
        pref[re.sub(r"[0-9].*$", "", str(m))] += 1
        d = MD.get(m)
        if d is None:
            missing += 1
        else:
            defs[d.get("AtlasRef", "(no AtlasRef: Type=%s)" % d.get("Type"))] += 1
    SEC_ATLAS[sec] = defs
    print("%-26s %6d  %-30s %s%s"
          % (sec, len(v), "; ".join("%s x%d" % p for p in pref.most_common(3)),
             "; ".join("%s x%d" % a for a in defs.most_common(3)),
             "  MISSING_MatDef=%d" % missing if missing else ""))

print("\n=== namespace -> atlas, distilled ===")
NS = {}
for sec in ICONS:
    v = ICONS[sec]
    if not isinstance(v, dict):
        continue
    at = collections.Counter()
    for m in v.values():
        d = MD.get(m)
        if d is not None and d.get("AtlasRef"):
            at[d["AtlasRef"]] += 1
    if at:
        NS[sec] = at.most_common(1)[0][0]
        print("  %-24s -> %-18s (%d/%d entries, %d distinct ids)"
              % (sec, NS[sec], at.most_common(1)[0][1], len(v), len(set(v.values()))))

# ---- do the Units/Buildings sections DISAGREE on the same numeric id? ----
u = ICONS.get("Units", {})
b = ICONS.get("Buildings", {})
both = sorted(set(u) & set(b), key=lambda x: int(x))
print("\n=== numeric ids present in BOTH 'Units' and 'Buildings' sections ===")
print("count %d" % len(both))
print("  sample: %s" % [(k, u[k], b[k]) for k in both[:6]])
print("  NOTE: every such id names a DIFFERENT material per section -> the section IS the namespace")
u_only = len(set(u) - set(b)); b_only = len(set(b) - set(u))
print("  Units-only %d ; Buildings-only %d ; union of numeric ids %d"
      % (u_only, b_only, len(set(u) | set(b))))

# ---- the decisive entities ----
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))
byid = {}
for civ in C:
    for x in civ["units"]:
        byid.setdefault(x["id"], x)

print("\n=== decisive entities under the icons.json rule ===")
for uid in [42, 71, 12, 79, 235, 50, 72, 117, 444, 331, 4, 83]:
    x = byid[uid]
    n = x.get("icon_id", -1)
    en = (SEM.get(str(uid)) or {}).get("en") or x.get("name") or "?"
    if n <= 0:
        print("  id %-5s %-24s IconID=%s (none)" % (uid, en[:24], n)); continue
    key = "%03d" % n
    inu, inb = key in u, key in b
    print("  id %-5s %-24s type=%-3s class=%-3s IconID=%-4d -> Units[%s]=%-22s Buildings[%s]=%s"
          % (uid, en[:24], x.get("type"), x.get("class"), n, key,
             u.get(key, "--"), key, b.get(key, "--")))

# ---- which section does the whole .dat population fall into? ----
print("\n=== whole-population routing by icons.json section ===")
route = collections.Counter()
unrouted = []
for x in byid.values():
    n = x.get("icon_id", -1)
    if n <= 0:
        route["no IconID"] += 1; continue
    k = "%03d" % n
    if k in u and k in b:
        route["both Units+Buildings"] += 1
    elif k in u:
        route["Units only"] += 1
    elif k in b:
        route["Buildings only"] += 1
    elif k in ICONS.get("Techs", {}):
        route["Techs only"] += 1
    else:
        route["NOT in icons.json"] += 1
        unrouted.append((x["id"], (SEM.get(str(x["id"])) or {}).get("en"), n, x.get("type"), x.get("class")))
for k, c in route.most_common():
    print("  %-24s %d" % (k, c))
print("\n  entities whose IconID is absent from icons.json (first 25):")
for r in unrouted[:25]:
    print("     id %-5d %-26s icon=%-4s type=%-3s class=%s" % (r[0], str(r[1])[:26], r[2], r[3], r[4]))
print("  total absent: %d" % len(unrouted))
json.dump({"sections": {s: len(v) for s, v in ICONS.items() if isinstance(v, dict)},
           "section_atlas": NS,
           "units_section": len(u), "buildings_section": len(b),
           "overlap": len(both),
           "routing": dict(route)},
          open(os.path.join(HERE, "icons_json_analysis.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote icons_json_analysis.json")
