# -*- coding: utf-8 -*-
"""Audit probe 16: the three remaining ways smoke5 can produce a wrong reading.
(a) does the emitted .dat actually carry the control edit (Villager HP 1000)?
(b) does anything else in Britons' panel/tree DEPEND on unit 74 (so removing it
    breaks a second button, contaminating subject B)?
(c) which enabled mods ship the panel/dat paths at all?
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, sys, hashlib, collections
sys.path.insert(0, _HERE_PATH("..", "..", ".."))
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
ACC = os.path.join(PROFILE, "76561198406248391")
MODS = os.path.join(ACC, "mods", "local")
OUT = _HERE_PATH("_probe", "out_smoke5")
BUNDLE = "aoe2mod Bundle VillagerHP plus Britons HandCannon"
SMOKE5 = "aoe2mod Smoke5 TreeVsPanel"
BLD = 12

def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]

head("16a: the emitted .dat -- is the CONTROL edit (Villager HP 1000) really in it?")
try:
    from aoe2mod.dat.parser import Parser
    for tag, p in (("SHIPPED", os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat")),
                   ("BUNDLE ", os.path.join(MODS, BUNDLE, r"resources\_common\dat\empires2_x2_p1.dat")),
                   ("SMOKE5 ", os.path.join(MODS, SMOKE5, r"resources\_common\dat\empires2_x2_p1.dat")),
                   ("OUT    ", os.path.join(OUT, r"resources\_common\dat\empires2_x2_p1.dat"))):
        try:
            pr = Parser(p)
            s = pr.parse_all() if hasattr(pr, "parse_all") else None
            print("   %s size=%-9d sha=%s parse_all=%s" % (tag, os.path.getsize(p), sha(p),
                                                           type(s).__name__ if s else "n/a"))
        except Exception as e:
            print("   %s size=%-9d sha=%s PARSE FAIL: %s: %s" % (
                tag, os.path.getsize(p), sha(p), type(e).__name__, e))
except Exception as e:
    print("   import failed: %s" % e)

head("16b: does anything in BRITONS' panel DEPEND on unit 74? (dependents of the removal)")
_t, po = BP.load_panel(os.path.join(GAME, r"resources\_common\dat\futuravailableunits.json"))
kb = BP.civ_key_for(po, "Britons")
deps = 0
for b in BP.buildings(po, kb):
    bid = b.get("ID")
    for space in ("Units", "Techs"):
        for e in (b.get(space) or []):
            hit = {k: v for k, v in e.items() if v == 74 and k != "ID"}
            if hit:
                deps += 1
                print("   bldg %-5s %-5s entry ID=%-6s name=%-28s refs 74 via %s" % (
                    bid, space, e.get("ID"), e.get("Name"), hit))
if not deps:
    print("   no Britons panel entry references 74 as a dependency field")

head("16c: the infantry upgrade chain in Britons' panel -- what gates 75/77/473/567?")
for b in BP.buildings(po, kb):
    if b.get("ID") != BLD:
        continue
    for e in (b.get("Units") or []):
        if e.get("ID") in (74, 75, 77, 473, 567, 93, 358, 359):
            print("   %s" % json.dumps(e, ensure_ascii=False))
print("   --- tree rows for the same ids ---")
tt = CT.load_trees(GAME)["BRITONS"]
for nid in (74, 75, 77, 473, 567):
    r = CT.row_for(tt, nid, CT.UNIT_USE_TYPES)
    print("   %-5s %s" % (nid, json.dumps(r, ensure_ascii=False) if r else None))

head("16d: does anything in BRITONS' TREE depend on 74?")
for r in CT.rows_of(tt):
    if not isinstance(r, dict):
        continue
    for k in ("Link ID", "Prerequisite IDs", "Prerequisite Types", "RequiredUnitID", "Trigger Tech ID"):
        v = r.get(k)
        if v == 74 or (isinstance(v, list) and 74 in v):
            print("   node %-6s %-22s %s=%r" % (r.get("Node ID"), r.get("Name"), k, v))

head("16e: which ENABLED mods ship the two engine paths at all?")
st = json.load(open(os.path.join(ACC, "mods", "mod-status.json"), encoding="utf-8-sig"))
for m in st["Mods"]:
    rel = m.get("Path", "").replace("//", os.sep)
    p = os.path.join(ACC, "mods", rel) if rel else None
    has_panel = p and os.path.isfile(os.path.join(p, r"resources\_common\dat\futuravailableunits.json"))
    has_dat = p and os.path.isfile(os.path.join(p, r"resources\_common\dat\empires2_x2_p1.dat"))
    has_tree = p and os.path.isfile(os.path.join(p, r"resources\_common\dat\CivTechTrees\BRITONS.json"))
    print("   Enabled=%-5s panel=%-5s dat=%-5s britons=%-5s %s" % (
        m.get("Enabled"), bool(has_panel), bool(has_dat), bool(has_tree), m.get("Path")))
