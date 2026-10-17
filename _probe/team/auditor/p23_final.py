# -*- coding: utf-8 -*-
"""Audit probe 23: final consolidation.
(a) Britons bldg-12 panel entry key shapes (any suppression rule?),
(b) mod-status.json mtime vs newest game log (is smoke5 registered?),
(c) the 2x2 outcome -> engine-regime mapping, enumerated,
(d) field asymmetry of the GRANTED 2550 row vs Britons' own Age-1 rows,
(e) what happens if BOTH mods are enabled (which contents win per path).
"""
import os, sys, json, glob, time
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
ACC = os.path.join(PROFILE, "76561198406248391")
MS = os.path.join(ACC, "mods", "mod-status.json")
LOCAL = os.path.join(ACC, "mods", "local")
BUNDLE = "aoe2mod Bundle VillagerHP plus Britons HandCannon"
SMOKE5 = "aoe2mod Smoke5 TreeVsPanel"
BLD, A, B = 12, 2550, 74


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


def fts(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


trees = CT.load_trees(GAME)
_t, po = BP.load_panel(os.path.join(GAME, BP.PANEL_REL))
kb = BP.civ_key_for(po, "Britons")

head("23a: Britons bldg-12 panel entries -- every key present (any suppression rule?)")
shapes = {}
prereq = 0
for b in BP.buildings(po, kb):
    if b.get("ID") != BLD:
        continue
    for space in ("Units", "Techs"):
        for e in (b.get(space) or []):
            sh = tuple(sorted(e.keys()))
            shapes.setdefault((space, sh), 0)
            shapes[(space, sh)] += 1
            if any(k != "ID" and k != "Name" and k != "RequiredAge" for k in e):
                prereq += 1
                print("   NON-STANDARD: %s %s" % (space, json.dumps(e, ensure_ascii=False)))
for (space, sh), n in sorted(shapes.items()):
    print("   %-6s %-40s x%d" % (space, sh, n))
print("   => entries at Britons bldg 12 carrying any extra field: %d" % prereq)

head("23b: is Smoke5 registered, and when was mod-status.json last written?")
print("   mod-status.json mtime : %s" % fts(os.path.getmtime(MS)))
sess = sorted([d for d in glob.glob(os.path.join(PROFILE, "logs", "*")) if os.path.isdir(d)],
              key=os.path.getmtime, reverse=True)
for s in sess[:3]:
    print("   log session           : %-28s %s" % (os.path.basename(s), fts(os.path.getmtime(s))))
for d in (BUNDLE, SMOKE5):
    p = os.path.join(LOCAL, d)
    print("   mod dir mtime         : %-52s %s" % (d[:50], fts(os.path.getmtime(p))))
j = json.load(open(MS, encoding="utf-8-sig"))
print("   Smoke5 in mod-status  : %s" % any("Smoke5" in (m.get("Title") or "") for m in j["Mods"]))
print("   Bundle Enabled        : %s" % [m.get("Enabled") for m in j["Mods"]
                                          if "Bundle" in (m.get("Path") or "")])

head("23c: enumerate the engine regimes vs the 4 observable outcomes")
regimes = [
    ("tree-only",        "A present", "B present"),
    ("panel-only",       "A absent",  "B absent"),
    ("union (either)",   "A present", "B present"),
    ("intersection",     "A absent",  "B absent"),
    ("tree-for-A+panel-for-B", "A present", "B absent"),
    ("panel-for-A+tree-for-B", "A absent",  "B present"),
]
cells = {}
for name, a, bb in regimes:
    cells.setdefault((a, bb), []).append(name)
for cell, names in sorted(cells.items()):
    print("   outcome %-24s <- %d regime(s): %s" % (str(cell), len(names), ", ".join(names)))
print()
print("   DESIGN'S STATED MAPPING (install_smoke5.py:100-101 / build_smoke5.py header):")
print("      A present + B present -> 'TREE drives'")
print("      A absent  + B absent  -> 'PANEL drives'")
print("      A present + B absent  -> 'both'")
print("      A absent  + B present -> 'neither / mod did not load'")
print("   CONFLICT: 'TREE drives' is ALSO the union outcome; 'PANEL drives' is ALSO intersection.")

head("23d: the GRANTED 2550 row vs Britons' own Age-1 bldg-12 rows (field asymmetry)")
dro = CT.donor_row(trees, A, CT.UNIT_USE_TYPES)[1]
print("   granted row keys:", sorted(dro.keys()))
native = [r for r in CT.rows_of(trees["BRITONS"])
          if isinstance(r, dict) and r.get("Age ID") == 1 and r.get("Building ID") == BLD
          and r.get("Use Type") == "Unit"]
print("   Britons' OWN Age-1 bldg-12 unit rows: %d" % len(native))
for r in native:
    print("      %-8s keys=%s" % (r.get("Name"), sorted(r.keys())))
allkeys = set()
for r in native:
    allkeys |= set(r.keys())
extra = sorted(set(dro.keys()) - allkeys)
missing = sorted(allkeys - set(dro.keys()))
print("   keys on the GRANT that NO native Britons Age-1 row has : %s" % extra)
print("   keys native Britons Age-1 rows have that the GRANT lacks: %s" % missing)
print("   granted Trigger Tech ID = %r ; native Age-1 rows carry it: %s"
      % (dro.get("Trigger Tech ID"), [r.get("Trigger Tech ID") for r in native]))

head("23e: if BOTH mods are present, which contents exist per path?")
def treeof(mod):
    return CT.load_trees(os.path.join(LOCAL, mod))["BRITONS"]
def panelof(mod):
    _x, o = BP.load_panel(os.path.join(LOCAL, mod, r"resources\_common\dat\futuravailableunits.json"))
    k = BP.civ_key_for(o, "Britons")
    return o, k
for m in (BUNDLE, SMOKE5):
    t = treeof(m)
    o, k = panelof(m)
    print("   %-8s tree A(2550)=%-5s tree B(74)=%-5s panel A=%-5s panel B=%-5s" % (
        m.split()[-2][:8] if "Bundle" in m else "Smoke5",
        CT.row_for(t, A, CT.UNIT_USE_TYPES) is not None,
        CT.row_for(t, B, CT.UNIT_USE_TYPES) is not None,
        BP.find_entry(o, k, A, BP.UNITS_KEY)[1] is not None,
        BP.find_entry(o, k, B, BP.UNITS_KEY)[1] is not None))
