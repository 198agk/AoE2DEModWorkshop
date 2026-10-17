#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a31_icon_arbitrate.py -- choose the icon atlas per entity, and show the ERROR of
each candidate rule so the choice is evidence-based, not asserted.

SITUATION
  ingameunits and ingamebuildings share 109/117 numeric stems, and for EVERY shared
  stem the two images differ (a29: MAD 33.9-99.9).  So a Town Center (IconID 28) and a
  Trebuchet (IconID 28) cannot both be right under a single namespace.  Unit 42
  Trebuchet (Type 80, Class 54) and unit 71 Town Center (Type 80, Class 3) really do
  both carry IconID 28 in the .dat, so the engine MUST disambiguate.

INSTRUMENT (still name-based, but used as an ERROR METRIC now, not as the rule)
  The ingamebuildings namespace is the only one whose entry names the entity:
  file '028_town_center.DDS', RefName 'BuildingIcons028TownCenter'.  So for an entity
  with IconID N, 'building-atlas entry N denotes this entity' is a testable predicate.
  Each candidate discriminator is scored by how many entities it sends to the building
  namespace that the entry does NOT denote (false positives) and how many buildings it
  fails to send (misses).

CANDIDATES
  H_type  : Type == 80                    -> ingamebuildings
  H_class : Class in BUILDING_CLASSES     -> ingamebuildings
  H_name  : class is building-ish AND building entry name denotes the entity
"""
import json, os, re, struct, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ICONS = json.load(open(os.path.join(WID, "icons.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))
STOP = {"age", "the", "and", "of", "de", "icon", "sprite", "packed", "dead"}


def toks(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "")
    s = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s)
    s = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", s)
    return set(x for x in re.split(r"[^A-Za-z0-9]+", s.lower())
               if len(x) > 2 and not x.isdigit() and x not in STOP)


def emb(name):
    out = {}
    for t in ATLS[name]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out


U, B = emb("ingameunits"), emb("ingamebuildings")


def bdesc(n):
    return re.sub(r"^[0-9]+_", "", B[n]["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0])


def bmatch(en, n):
    return n in B and len(toks(en) & toks(bdesc(n))) > 0


byid = {}
for civ in C:
    for x in civ["units"]:
        byid.setdefault(x["id"], x)


def EN(u):
    uid = u["id"]
    return (SEM.get(str(uid)) or {}).get("en") or u.get("name") or "?"


ents = [u for u in byid.values() if u.get("icon_id", -1) > 0]
print("entities with IconID>0: %d" % len(ents))

print("\n=== per-Class detail: how often does the ingamebuildings entry DENOTE the entity? ===")
print("%-6s %5s %5s %7s %8s  %s" % ("class", "n", "inB", "denotes", "rate", "classes' meaning seen in names"))
byc = collections.defaultdict(list)
for u in ents:
    byc[u.get("class")].append(u)
for cl in sorted(byc, key=lambda c: (byc[c][0].get("type") or 0, c)):
    us = byc[cl]
    inb = [u for u in us if u["icon_id"] in B]
    ok = [u for u in us if bmatch(EN(u), u["icon_id"])]
    mean = collections.Counter()
    for u in us:
        mean[EN(u).split("(")[0].strip().split()[-1] if EN(u).split() else "?"] += 1
    print("%-6s %5d %5d %7d %7.1f%%  %s"
          % (cl, len(us), len(inb), len(ok), 100.0 * len(ok) / max(1, len(inb)),
             ", ".join(x for x, _ in mean.most_common(4))))

print("\n=== Class 27 mismatches (the weak class) ===")
for u in sorted(byc.get(27, []), key=lambda x: x["id"]):
    n = u["icon_id"]
    print("   id %-5d %-30s icon=%-4s B=%-22s denotes=%s"
          % (u["id"], EN(u)[:30], n, bdesc(n) if n in B else "--", bmatch(EN(u), n)))

print("\n=== sparse / odd classes: 1, 14, 51, 54, 11, 49, 52 ===")
for cl in (1, 14, 51, 54, 11, 49, 52):
    for u in sorted(byc.get(cl, []), key=lambda x: x["id"]):
        n = u["icon_id"]
        print("   class %-3d type %-3s id %-5d %-34s icon=%-4s B=%-22s denotes=%s"
              % (cl, u.get("type"), u["id"], EN(u)[:34], n,
                 bdesc(n) if n in B else "--", bmatch(EN(u), n)))

BUILDING_CLASSES = {1, 3, 11, 14, 27, 39, 49, 52}


def route(u, rule):
    n = u["icon_id"]
    if rule == "H_type":
        return "ingamebuildings" if u.get("type") == 80 else "ingameunits"
    if rule == "H_class":
        return "ingamebuildings" if (u.get("class") in BUILDING_CLASSES and n in B) else "ingameunits"
    if rule == "H_name":
        return "ingamebuildings" if bmatch(EN(u), n) else "ingameunits"
    raise ValueError(rule)


print("\n=== rule error metrics over the %d entities with IconID>0 ===" % len(ents))
print("%-9s %14s %14s %10s %10s" % ("rule", "->buildings", "of those FALSE", "FP rate", "->units"))
for rule in ("H_type", "H_class", "H_name"):
    r = {u["id"]: route(u, rule) for u in ents}
    toB = [u for u in ents if r[u["id"]] == "ingamebuildings"]
    fp = [u for u in toB if not bmatch(EN(u), u["icon_id"])]
    toU = [u for u in ents if r[u["id"]] == "ingameunits"]
    # a building wrongly sent to units: class is architecturally a building and the
    # building entry denotes it
    miss = [u for u in toU if bmatch(EN(u), u["icon_id"])]
    print("%-9s %14d %14d %9.1f%% %10d   (units-side misses of a denoting entry: %d)"
          % (rule, len(toB), len(fp), 100.0 * len(fp) / max(1, len(toB)), len(toU), len(miss)))
    if rule == "H_class":
        print("      H_class FALSE positives (first 20): %s"
              % [(u["id"], EN(u)[:18], u.get("class"), bdesc(u["icon_id"])) for u in fp][:20])

print("\n=== decisive entities, all three rules ===")
for uid in (42, 71, 12, 4, 79, 235, 50, 72, 117, 331, 444, 1712):
    u = byid[uid]
    n = u.get("icon_id", -1)
    print("   id %-5d %-26s type=%-3s class=%-3s icon=%-4s | H_type=%-16s H_class=%-16s H_name=%-16s"
          % (uid, EN(u)[:26], u.get("type"), u.get("class"), n,
             route(u, "H_type") if n > 0 else "-",
             route(u, "H_class") if n > 0 else "-",
             route(u, "H_name") if n > 0 else "-"))

json.dump({"building_classes": sorted(BUILDING_CLASSES),
           "per_class": {str(c): {"n": len(v), "inB": sum(1 for x in v if x["icon_id"] in B),
                                  "denotes": sum(1 for x in v if bmatch(EN(x), x["icon_id"]))}
                         for c, v in byc.items()}},
          open(os.path.join(HERE, "icon_arbitration.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote icon_arbitration.json")
