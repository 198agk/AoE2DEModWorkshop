# -*- coding: utf-8 -*-
"""Audit probe 15: (a) full mod-status dump, (b) the 2x2 the TWO installed mods
can synthesise by file layering, (c) .dat button/hotkey fields for 74 & 2550,
(d) mod-manager passes in the log."""
import json, os, sys, glob, collections
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
BLD = 12


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


head("15a: every entry in mod-status.json")
j = json.load(open(os.path.join(ACC, "mods", "mod-status.json"), encoding="utf-8-sig"))
mods = j["Mods"]
print("   %d entries" % len(mods))
for m in mods:
    print("   Enabled=%-5s Prio=%-3s Path=%-58s Title=%s" % (
        m.get("Enabled"), m.get("Priority"), m.get("Path"), m.get("Title")))
print("   'Smoke5' anywhere in mod-status.json: %r" % ("Smoke5" in json.dumps(j, ensure_ascii=False)))
print("   Unsub:", json.dumps(j.get("Unsub"), ensure_ascii=False)[:200])

head("15b: can the two INSTALLED mods, by file layering alone, produce each 2x2 cell?")
def look(mod, node):
    t = CT.load_trees(os.path.join(MODS, mod))["BRITONS"]
    return CT.row_for(t, node, CT.UNIT_USE_TYPES)

def plook(mod, node):
    _t, o = BP.load_panel(os.path.join(MODS, mod, r"resources\_common\dat\futuravailableunits.json"))
    k = BP.civ_key_for(o, "Britons")
    return BP.find_entry(o, k, node, BP.UNITS_KEY)[1]

print("   %-46s %-12s %-12s" % ("mod", "tree has 2550", "panel has 74"))
for mod in (BUNDLE, SMOKE5):
    print("   %-46s %-12s %-12s" % (mod[:44],
                                    "YES" if look(mod, 2550) else "no",
                                    "YES" if plook(mod, 74) else "no"))
print()
print("   file-layered combinations the engine could pick (tree from X, panel from Y):")
for tm in (BUNDLE, SMOKE5):
    for pm_ in (BUNDLE, SMOKE5):
        a = "A present" if look(tm, 2550) else "A absent"
        b = "B present" if plook(pm_, 74) else "B absent"
        print("      tree<-%-6s panel<-%-6s => %-10s %-10s  reads as '%s'" % (
            tm.split()[-2] if "Bundle" in tm else "Smoke5",
            "Smoke5" if "Smoke5" in pm_ else "Bundle",
            a, b,
            {"A presentB present": "TREE drives", "A absentB absent": "PANEL drives",
             "A presentB absent": "both", "A absentB present": "neither"}[a + b]))

head("15c: .dat train-location / button / hotkey fields for the two subjects")
from aoe2mod.dat import parser as P
tk_ok = True
try:
    import aoe2mod.api as A
    tk = A.open_toolkit(); tk._ensure()
    data, civs, civs_start, gv, tail, how = tk._parsed
    print("   gv=%s" % gv)
except Exception as e:
    print("   toolkit failed: %s" % e); tk_ok = False

head("15d: mod manager passes -- MainLog.txt")
logs = os.path.join(PROFILE, "logs")
sessions = sorted(glob.glob(os.path.join(logs, "*"))) if os.path.isdir(logs) else []
print("   %d session dirs" % len(sessions))
for s in sessions[-6:]:
    print("      %s" % os.path.basename(s))
hits = 0
for s in sessions[-8:]:
    ml = os.path.join(s, "MainLog.txt")
    if not os.path.isfile(ml):
        continue
    txt = open(ml, encoding="utf-8", errors="replace").read()
    for pat in ("Setup mod manager", "Enabling mod #", "Terminating Mod Manager"):
        c = txt.count(pat)
        if c:
            print("   %-34s %-24s x%d" % (os.path.basename(s), pat, c))
            hits += 1
if not hits:
    print("   no mod-manager markers found in the last 8 sessions")

head("15e: what the Bundle mod does to BRITONS (its tree/panel delta vs shipped)")
tt = CT.load_trees(os.path.join(MODS, BUNDLE))["BRITONS"]
ts = CT.load_trees(GAME)["BRITONS"]
si = {r.get("Node ID"): r for r in CT.rows_of(ts) if isinstance(r, dict)}
for r in CT.rows_of(tt):
    if isinstance(r, dict) and r.get("Node ID") not in si:
        print("   bundle adds: %s" % json.dumps(r, ensure_ascii=False)[:220])
for nid, r in si.items():
    if not any(isinstance(x, dict) and x.get("Node ID") == nid for x in CT.rows_of(tt)):
        print("   bundle removes: %s %s" % (nid, r.get("Name")))
