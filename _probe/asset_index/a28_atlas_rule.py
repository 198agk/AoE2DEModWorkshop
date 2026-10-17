#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a28_atlas_rule.py -- settle WHICH atlas an IconID indexes, per entity.

Visual evidence from a26/a27: ingameunits 028_50730.dds renders a TREBUCHET while
ingamebuildings 028_town_center.dds renders a TOWN CENTER, and unit 42
"Trebuchet" carries IconID 28.  So a plain "Type==80 -> ingamebuildings" rule
would give the Trebuchet a town-centre icon, which is wrong.  The discriminator
must be finer than Type.

This tests candidate discriminators against the ONLY name-bearing atlas
(ingamebuildings, 110 entries, RefName like 'BuildingIcons002Barracks1'):
  D1  Type == 80
  D2  Type == 80 and Class == 3
  D3  Class == 3
  D4  the building atlas simply has an entry for that IconID
and reports, for each, name-plausibility, plus what happens to unit 42.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))


def emb(a):
    out = {}
    for t in ATLS[a]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out


U, B, T = emb("ingameunits"), emb("ingamebuildings"), emb("ingametechs")
STOP = {"age", "the", "and", "icon", "sprite"}


def toks(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "")
    s = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s)
    s = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", s)
    return set(x for x in re.split(r"[^A-Za-z0-9]+", s.lower())
               if len(x) > 2 and not x.isdigit() and x not in STOP)


def plaus(entity, ref):
    r = re.sub(r"^(BuildingIcons|UnitIcons|TechIconsT?)", "", ref or "")
    r = re.sub(r"^[0-9]+", "", r)
    return len(toks(r) & toks(entity)) > 0


byid = {}
for civ in C:
    for u in civ["units"]:
        byid.setdefault(u["id"], u)

rows = []
for uid, u in sorted(byid.items()):
    if u.get("icon_id", -1) <= 0:
        continue
    en = (SEM.get(str(uid)) or {}).get("en") or u.get("name") or ""
    rows.append({"id": uid, "en": en, "type": u.get("type"), "class": u.get("class"),
                 "icon": u["icon_id"]})
print("units with IconID>0 : %d" % len(rows))
print("Type histogram      : %s" % sorted(
    {t: sum(1 for r in rows if r["type"] == t) for t in set(r["type"] for r in rows)}.items()))
print("Class histogram (type 80) : %s" % sorted(
    {c: sum(1 for r in rows if r["type"] == 80 and r["class"] == c)
     for c in set(r["class"] for r in rows if r["type"] == 80)}.items()))

TESTS = {
    "D1 Type==80": lambda r: r["type"] == 80,
    "D2 Type==80 & Class==3": lambda r: r["type"] == 80 and r["class"] == 3,
    "D3 Class==3": lambda r: r["class"] == 3,
    "D4 building atlas has entry": lambda r: r["icon"] in B,
}
print("\n%-30s %6s %6s %6s %8s  %s" % ("discriminator", "n", "inB", "inU", "plaus%", "verdict"))
for name, fn in TESTS.items():
    sel = [r for r in rows if fn(r)]
    nb = sum(1 for r in sel if r["icon"] in B)
    nu = sum(1 for r in sel if r["icon"] in U)
    pl = sum(1 for r in sel if r["icon"] in B and plaus(r["en"], B[r["icon"]]["RefName"]))
    pct = 100.0 * pl / max(1, nb)
    print("%-30s %6d %6d %6d %7.1f%%" % (name, len(sel), nb, nu, pct))
    if name == "D2 Type==80 & Class==3":
        d2miss = [r for r in sel if not (r["icon"] in B and plaus(r["en"], B[r["icon"]]["RefName"]))]
        print("      D2 name-implausible: %d ; ids %s"
              % (len(d2miss), [r["id"] for r in d2miss][:24]))

print("\n=== Type 80 but NOT Class 3 (candidate unit-space entities) ===")
odd = [r for r in rows if r["type"] == 80 and r["class"] != 3]
print("count %d" % len(odd))
for r in odd[:30]:
    print("   id %-5d %-26s class=%-4s icon=%-4s U=%-22s B=%s"
          % (r["id"], r["en"][:26], r["class"], r["icon"],
             U[r["icon"]]["RefName"] if r["icon"] in U else "--",
             B[r["icon"]]["RefName"] if r["icon"] in B else "--"))

print("\n=== Class 3 but NOT Type 80 ===")
o2 = [r for r in rows if r["class"] == 3 and r["type"] != 80]
print("count %d -> %s" % (len(o2), [(r["id"], r["en"][:18], r["type"]) for r in o2][:12]))

print("\n=== Type 80 & Class 3 whose IconID has NO building entry (fallback needed) ===")
fb = [r for r in rows if r["type"] == 80 and r["class"] == 3 and r["icon"] not in B]
print("count %d" % len(fb))
for r in fb:
    print("   id %-5d %-28s icon=%-4s -> unit atlas %s"
          % (r["id"], r["en"][:28], r["icon"],
             U[r["icon"]]["FileName"].rsplit("/", 1)[-1] if r["icon"] in U else "ABSENT"))
