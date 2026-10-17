#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a32_loose_truth.py -- use the GAME'S OWN loose texture filenames as ground truth
for the icon-namespace question, instead of my tokenizer.

WHY
  a31 scored three routing rules with a name-overlap test, which is circular for the
  name-based rule.  But the game ships the icon sources as LOOSE FILES with author-written
  names:
      widgetui\\textures\\ingame\\buildings\\028_town_center.DDS   <- authoritative label
      widgetui\\textures\\ingame\\units\\028_50730.DDS             <- bare numeric, no label
  So for each numeric icon id N, the building-author's label for N is available verbatim,
  and we can ask: for every entity carrying IconID N, does label(N) denote that entity?
  No tokenizer involved on the label side; we just print it.

WHAT IT PRINTS
  1. every shared stem N (present in both ingameunits and ingamebuildings embeddings),
     the building loose label, and ALL entities carrying IconID N.
  2. the H_class "false positive" list with its label, so we can see whether they are
     really false.
"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))
LOOSE_B = os.path.join(WID, "textures", "ingame", "buildings")
LOOSE_U = os.path.join(WID, "textures", "ingame", "units")

# ---- loose filename maps: numeric stem -> full filename (author-written labels) ----
lb, lu = {}, {}
for d, tgt in ((LOOSE_B, lb), (LOOSE_U, lu)):
    for f in os.listdir(d):
        h = f.split("_")[0]
        if h.isdigit():
            tgt.setdefault(int(h), f)
print("loose building files with numeric stem: %d" % len(lb))
print("loose unit files with numeric stem: %d" % len(lu))
print("labels for EVERY ingamebuildings atlas entry, from disk:")
print("   N   loose-building-label                     atlas-embed FileName")
for t in ATLS["ingamebuildings"]["Textures"]:
    stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
    h = stem.split("_")[0]
    print("  %-4s %-40s %s" % (h, lb.get(int(h), "-- NO LOOSE FILE --") if h.isdigit() else "?",
                              t["FileName"]))

def emb(name):
    out = {}
    for t in ATLS[name]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out

U, B = emb("ingameunits"), emb("ingamebuildings")
byid = {}
for civ in C:
    for x in civ["units"]:
        byid.setdefault(x["id"], x)


def EN(u):
    return (SEM.get(str(u["id"])) or {}).get("en") or u.get("name") or "?"


byicon = collections.defaultdict(list)
for u in byid.values():
    if u.get("icon_id", -1) > 0:
        byicon[u["icon_id"]].append(u)

shared = sorted(set(U) & set(B))
print("\n=== %d shared stems: the building-author's label vs every entity carrying that IconID ===" % len(shared))
for n in shared:
    us = sorted(byicon.get(n, []), key=lambda x: x["id"])
    lab = lb.get(n, "-- no loose file --")
    lab = re.sub(r"^[0-9]+_", "", lab).rsplit(".", 1)[0]
    print("  N=%-4d label=%-34s holders=%d" % (n, lab, len(us)))
    for u in us[:6]:
        print("        id %-5d type=%-3s class=%-3s  %s" % (u["id"], u.get("type"), u.get("class"), EN(u)[:44]))
    if len(us) > 6:
        print("        ... %d more" % (len(us) - 6))

# ---- what does a building-atlas stem look like when NOT in the unit atlas? ----
print("\n=== building-atlas stems NOT present in the unit atlas (label + holders) ===")
only_b = sorted(set(B) - set(U))
for n in only_b:
    lab = re.sub(r"^[0-9]+_", "", lb.get(n, "-- none --")).rsplit(".", 1)[0]
    us = byicon.get(n, [])
    print("  N=%-4d label=%-34s holders=%s" % (n, lab, [(u["id"], EN(u)[:22]) for u in us]))

print("\n=== unit-atlas stems NOT present in the building atlas, WITH a holding entity (first 40) ===")
only_u = sorted(set(U) - set(B))
shown = 0
for n in only_u:
    us = byicon.get(n, [])
    if not us:
        continue
    lab = re.sub(r"^[0-9]+_", "", lu.get(n, "-- none --")).rsplit(".", 1)[0]
    print("  N=%-4d looseUnitLabel=%-24s holders=%s" % (n, lab, [(u["id"], EN(u)[:22]) for u in us]))
    shown += 1
    if shown >= 40:
        break
print("  (%d unit-only stems carry at least one holder)" % sum(1 for n in only_u if byicon.get(n)))
