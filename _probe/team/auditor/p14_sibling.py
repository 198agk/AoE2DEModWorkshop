# -*- coding: utf-8 -*-
"""Audit probe 14: the co-installed sibling mod and the enable state.
Two local mods ship the SAME three engine paths; whichever the engine picks
determines the read, independent of what smoke5's own bytes say."""
import json, os, sys, hashlib
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
ACC = os.path.join(PROFILE, "76561198406248391")
MODS = os.path.join(ACC, "mods", "local")
BUNDLE = "aoe2mod Bundle VillagerHP plus Britons HandCannon"
SMOKE5 = "aoe2mod Smoke5 TreeVsPanel"


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


head("14a: mod-status.json -- which local mods are ENABLED, and in what order")
ms = os.path.join(ACC, "mods", "mod-status.json")
j = json.load(open(ms, encoding="utf-8-sig"))
print("   file:", ms)
print("   top keys:", list(j))
mods = j.get("Mods")
print("   Mods type=%s len=%s" % (type(mods).__name__, len(mods) if hasattr(mods, "__len__") else "-"))
if isinstance(mods, list):
    for m in mods:
        if isinstance(m, dict):
            s = json.dumps(m, ensure_ascii=False)
            if "Smoke5" in s or "Bundle" in s or "aoe2mod" in s:
                print("   >> %s" % s[:400])
elif isinstance(mods, dict):
    for k, v in mods.items():
        if "Smoke5" in k or "Bundle" in k or "aoe2mod" in k:
            print("   >> %s : %s" % (k, json.dumps(v, ensure_ascii=False)[:400]))
print("   total matching 'aoe2mod' entries:", json.dumps(mods, ensure_ascii=False).count("aoe2mod"))

head("14b: the two mods' three shared paths -- sizes and sha256")
rels = [r"resources\_common\dat\empires2_x2_p1.dat",
        r"resources\_common\dat\futuravailableunits.json",
        r"resources\_common\dat\CivTechTrees\BRITONS.json"]
shipped = {"dat": os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat"),
           "panel": os.path.join(GAME, r"resources\_common\dat\futuravailableunits.json"),
           "tree": os.path.join(GAME, r"resources\_common\dat\CivTechTrees\BRITONS.json")}
print("   %-34s %12s %-12s" % ("source", "bytes", "sha256[:12]"))
for label, p in shipped.items():
    print("   %-34s %12d %-12s" % ("SHIPPED " + label, os.path.getsize(p), sha(p)[:12]))
for mod in (BUNDLE, SMOKE5):
    for rel in rels:
        p = os.path.join(MODS, mod, rel)
        print("   %-34s %12s %-12s" % (mod[:4] + " " + os.path.basename(rel),
                                       os.path.getsize(p) if os.path.isfile(p) else "-",
                                       sha(p)[:12] if os.path.isfile(p) else "-"))

head("14c: what does the BUNDLE mod's BRITONS.json / panel actually contain?")
bp_ = os.path.join(MODS, BUNDLE, rels[2])
if os.path.isfile(bp_):
    t = CT.load_trees(os.path.join(MODS, BUNDLE))["BRITONS"]
    print("   bundle BRITONS.json unit rows:", len(t.get("civ_techs_units") or []))
    for nid in (74, 2550, 5):
        r = CT.row_for(t, nid, CT.UNIT_USE_TYPES)
        print("      node %-5d -> %s" % (nid, (r.get("Name"), r.get("Node Status"), r.get("Building ID")) if r else None))
bpan = os.path.join(MODS, BUNDLE, rels[1])
if os.path.isfile(bpan):
    _t, o = BP.load_panel(bpan)
    k = BP.civ_key_for(o, "Britons")
    for nid in (74, 2550, 5):
        print("      panel %-5s -> %s" % (nid, BP.find_entry(o, k, nid, BP.UNITS_KEY)))
    print("      panel civs:", len([c for c in o]))

head("14d: smoke5's installed panel -- is the 74 removal present on disk?")
span = os.path.join(MODS, SMOKE5, rels[1])
if os.path.isfile(span):
    _t, o = BP.load_panel(span)
    k = BP.civ_key_for(o, "Britons")
    print("   panel 74  ->", BP.find_entry(o, k, 74, BP.UNITS_KEY))
    print("   panel 2550->", BP.find_entry(o, k, 2550, BP.UNITS_KEY))
st = os.path.join(MODS, SMOKE5, rels[2])
if os.path.isfile(st):
    t = CT.load_trees(MODS)[SMOKE5] if False else CT.load_trees(os.path.join(MODS, SMOKE5))["BRITONS"]
    print("   tree 2550 ->", CT.row_for(t, 2550, CT.UNIT_USE_TYPES))
    print("   tree 74   ->", CT.row_for(t, 74, CT.UNIT_USE_TYPES))

head("14e: info.json of both -- title/priority fields the engine may order by")
for mod in (BUNDLE, SMOKE5):
    p = os.path.join(MODS, mod, "info.json")
    if os.path.isfile(p):
        print("   %-46s %s" % (mod, json.dumps(json.load(open(p, encoding="utf-8-sig")), ensure_ascii=False)[:400]))
