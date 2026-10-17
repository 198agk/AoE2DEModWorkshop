#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a22_icon_final.py -- close the last two atlas questions.

1. The 10 type-80 units whose IconID has NO ingamebuildings entry: do they fall
   back to ingameunits, and what is the plausibility of that fallback?
2. For the 53 'name-implausible' buildings: print the atlas entry\'s own
   FileName (which is more descriptive than the RefName suffix) so a reader can
   judge whether the mapping is actually right (Monastery3 for a Cathedral is
   correct: cathedral-class buildings share the monastery art).
3. Same for the disputed units id 42 / 331 (Trebuchet / Trebuchet (Packed)).
"""
import json, os, re, collections

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
byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u

print("=== 1. type-80 units with NO ingamebuildings entry ===")
rows = []
for uid, per in sorted(byid.items()):
    u = per[sorted(per)[0]]
    if u.get("type") != 80 or u.get("icon_id", -1) <= 0:
        continue
    if u["icon_id"] in B:
        continue
    en = (SEM.get(str(uid)) or {}).get("en") or u.get("name") or ""
    rows.append((uid, en, u["icon_id"]))
print("count %d" % len(rows))
for uid, en, ic in rows:
    print("   id %-5d %-26s icon=%-4d -> ingameunits %s   (%s)"
          % (uid, en[:26], ic,
             U[ic]["RefName"] if ic in U else "ABSENT",
             U[ic]["FileName"] if ic in U else "-"))

print("\n=== 2. the 53 name-implausible buildings, with the atlas FileName ===")
STOP = {"age", "the", "and", "icon"}
def toks(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "")
    s = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s)
    s = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", s)
    return set(x for x in re.split(r"[^A-Za-z0-9]+", s.lower())
               if len(x) > 2 and not x.isdigit() and x not in STOP)
for uid, per in sorted(byid.items()):
    u = per[sorted(per)[0]]
    if u.get("type") != 80 or u.get("icon_id", -1) <= 0:
        continue
    ic = u["icon_id"]
    if ic not in B:
        continue
    en = (SEM.get(str(uid)) or {}).get("en") or u.get("name") or ""
    ref = re.sub(r"^BuildingIcons[0-9]+", "", B[ic]["RefName"])
    if toks(en) & toks(ref):
        continue
    print("   id %-5d %-30s icon=%-4d %-34s %s"
          % (uid, en[:30], ic, B[ic]["RefName"], B[ic]["FileName"]))

print("\n=== 3. disputed siege/building units ===")
for uid in (42, 331, 280, 283, 888):
    per = byid.get(uid)
    if not per:
        print("   id %d absent" % uid)
        continue
    ic = per[sorted(per)[0]].get("icon_id", -1)
    en = (SEM.get(str(uid)) or {}).get("en") or per[sorted(per)[0]].get("name")
    print("   id %-5d %-28s icon=%-4d B=%-34s U=%s"
          % (uid, (en or "")[:28], ic,
             "%s (%s)" % (B[ic]["RefName"], B[ic]["FileName"].rsplit("/", 1)[-1]) if ic in B else "--",
             U[ic]["FileName"].rsplit("/", 1)[-1] if ic in U else "--"))
