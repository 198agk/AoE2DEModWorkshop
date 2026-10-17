# -*- coding: utf-8 -*-
"""Final pin: all 14 icons.json sections -> resolution rule + coverage.

Rules discovered:
  R1 materials-name: value is (or maps to) a MaterialDef.Name -> atlas FileName
  R2 wpfg-strip:     value starts with <dir>_ -> wpfg/resources/<dir>/<rest>.png
  R3 wpfg-whole:     value itself is <dir>/<value>.png
  R4 hardcoded:      small special-case maps (Notification -> ScorePanel*)
Read-only.
"""
import os
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WJ = os.path.join(GAME, "widgetui")
WR = os.path.join(GAME, "resources", "_common", "wpfg", "resources")

icons = json.load(open(os.path.join(WJ, "icons.json"), encoding="utf-8"))
mats = json.load(open(os.path.join(WJ, "materials.json"), encoding="utf-8"))

mat = {}
for m in mats["Materials"]:
    md = m.get("MaterialDef") or {}
    mat[md.get("Name")] = md
atlas_file = {}
for a in mats["AtlasTextures"]:
    ad = a.get("AtlasDef") or {}
    for t in ad.get("Textures", []):
        atlas_file.setdefault(t["RefName"], []).append(
            (ad["Name"], t["FileName"]))

pix = {}
for base in (WR, os.path.join(WJ, "textures")):
    for b, s, fs in os.walk(base):
        for f in fs:
            st, e = os.path.splitext(f)
            if e.lower() in (".png", ".jpg", ".dds"):
                pix.setdefault(st.lower(), []).append(
                    os.path.join(b, f).replace(GAME, "<GAME>"))


def mat_file(name):
    md = mat.get(name)
    if not md:
        return None
    ref = md.get("TextureRef") or name
    hit = atlas_file.get(ref) or atlas_file.get(name)
    return hit[0][1] if hit else None


def rule_for(sec, v):
    """Return (rule, artifact) or (None, None)."""
    # R1
    f = mat_file(v)
    if f:
        return "R1-material", f
    # R2 wpfg strip
    for sub in ("civ_emblems", "civ_techtree", "civ_hero", "history",
                "usericons", "mapicons", "mappoolicon", "uniticons",
                "empireicons", "ingame_civ_emblems", "ingame_emblems"):
        for pre in (sub + "_", "ingame_" + sub + "_"):
            if v.startswith(pre):
                stem = v[len(pre):]
                p = os.path.join(WR, sub, stem + ".png")
                if os.path.exists(p):
                    return "R2-wpfg-strip", p.replace(GAME, "<GAME>")
    # R3 wpfg whole
    for sub in ("civ_techtree", "history", "usericons", "mapicons",
                "mappoolicon", "uniticons", "civ_emblems"):
        p = os.path.join(WR, sub, v + ".png")
        if os.path.exists(p):
            return "R3-wpfg-whole", p.replace(GAME, "<GAME>")
    # R3b widgetui textures whole
    for p in pix.get(v.lower(), []):
        return "R3b-widgetui", p
    # R4 notification special-case
    if sec == "Notification":
        base = v.replace("_icon", "")
        cand = "ScorePanel" + "".join(p.capitalize() for p in base.split("_"))
        f = mat_file(cand)
        if f:
            return "R4-ScorePanel", f
    return None, None


rows = []
for sec, entries in icons.items():
    if not isinstance(entries, dict):
        continue
    vals = [(k, v) for k, v in entries.items() if isinstance(v, str) and v]
    empty = len(entries) - len(vals)
    ok, miss, rules = 0, [], {}
    for k, v in vals:
        r, art = rule_for(sec, v)
        if r:
            ok += 1
            rules[r] = rules.get(r, 0) + 1
        else:
            miss.append(v)
    rows.append((sec, len(entries), empty, len(vals), ok, miss, rules))

print("=== icons.json: all sections ===")
print("%-24s %5s %5s %5s %5s  %-38s %s"
      % ("section", "n", "empty", "val", "res", "rules", "unresolved"))
for sec, n, e, v, ok, miss, rules in rows:
    rs = ",".join("%s:%d" % t for t in sorted(rules.items()))
    print("%-24s %5d %5d %5d %5d  %-38s %s"
          % (sec, n, e, v, ok, rs[:38],
             ("%d  %s" % (len(miss), miss[:2])) if miss else ""))

print()
tot = sum(r[3] for r in rows)
res = sum(r[4] for r in rows)
print("TOTAL non-empty values: %d   resolved: %d  (%.1f%%)"
      % (tot, res, 100.0 * res / tot))
