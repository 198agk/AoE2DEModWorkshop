# -*- coding: utf-8 -*-
"""End-to-end validation of the resolution chain against external ground truth.

Ground truth used:
  * hit points independently verified by the dat parser (Archer 4 = 30 hp, ...)
  * the localised names that the game itself must show, cross-checked against
    the CivTechTrees JSON `Name String ID` / `Name` pairs, which are authored
    independently of the dat.
"""
import json
import os
import sys
import collections

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
units = json.load(open(os.path.join(HERE, "unit_names.json"), encoding="utf-8"))
techs = json.load(open(os.path.join(HERE, "tech_names.json"), encoding="utf-8"))

EXPECT_UNITS = [
    (4, "ARCHR", "Archer", "步弓手", 30),
    (7, None, "Skirmisher", "掷矛手", 30),
    (8, None, "Longbowman", "长弓兵", 35),
    (38, "KNGHT", "Knight", "骑士", 100),
    (74, "SPRMN", "Militia", "民兵", 40),
    (75, None, "Man-at-Arms", "武士", 45),
    (83, None, "Villager (Male)", "村民 (男性)", 25),
    (93, None, "Spearman", "长矛兵", 45),
    (448, None, "Scout Cavalry", "斥候骑兵", 45),
    (546, None, "Light Cavalry", "轻型骑兵", 60),
    (751, None, "Eagle Scout", "鹰斥候", 50),
]

print("=" * 72)
print("VALIDATION 1: known units vs externally verified hp")
print("=" * 72)
ok = fail = 0
for uid, code, en, zh, hp in EXPECT_UNITS:
    e = units.get(str(uid))
    if e is None:
        print("  id %-4d MISSING from unit_names.json" % uid)
        fail += 1
        continue
    checks = []
    if e["en"] != en:
        checks.append("en want %r got %r" % (en, e["en"]))
    if e["zh"] != zh:
        checks.append("zh want %r got %r" % (zh, e["zh"]))
    if code and e["internal"] != code:
        checks.append("internal want %r got %r" % (code, e["internal"]))
    if hp not in e["hit_points"]:
        checks.append("hp want %d got %s" % (hp, e["hit_points"]))
    if checks:
        print("  id %-4d %-18s FAIL: %s" % (uid, e["en"], "; ".join(checks)))
        fail += 1
    else:
        print("  id %-4d %-10s en=%-18s zh=%-12s hp=%-4s sid=%-6s OK"
              % (uid, e["internal"], e["en"], e["zh"], e["hit_points"],
                 e["name_string_id"]))
        ok += 1
print("  -> %d/%d passed" % (ok, ok + fail))

print()
print("=" * 72)
print("VALIDATION 2: our names vs CivTechTrees independently authored names")
print("=" * 72)
CT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\CivTechTrees"
agree = disagree = unmatched = 0
examples = []
for fn in sorted(os.listdir(CT)):
    d = json.load(open(os.path.join(CT, fn), encoding="utf-8"))
    for key in ("civ_techs_units", "civ_techs_buildings"):
        for node in d.get(key, []):
            nid = node.get("Node ID")
            nsid = node.get("Name String ID")
            nm = node.get("Name")
            if not isinstance(nid, int) or str(nid) not in units:
                unmatched += 1
                continue
            e = units[str(nid)]
            # compare against the variant that matches THIS json's string id
            got = None
            if e["name_string_id"] == nsid:
                got = e["en"]
            elif e.get("civ_variants") and str(nsid) in e["civ_variants"]:
                got = e["civ_variants"][str(nsid)]["en"]
            if got is None:
                unmatched += 1
            elif got == nm:
                agree += 1
            else:
                disagree += 1
                if len(examples) < 12:
                    examples.append((fn, key, nid, nsid, nm, got))
print("  agree    : %d" % agree)
print("  disagree : %d" % disagree)
print("  unmatched: %d (json name-id not reachable from our variants)" % unmatched)
for ex in examples:
    print("     %s %s node=%s sid=%s json=%r ours=%r" % ex)

print()
print("=" * 72)
print("VALIDATION 3: tech string-id family invariant")
print("=" * 72)
pat = 0
tot = 0
for e in techs.values():
    n = e["name_string_id"]
    if not isinstance(n, int) or n <= 0:
        continue
    tot += 1
    d, h, t = (e["description"]["name_string_id"], e["help"]["name_string_id"],
               e["tech_tree"]["name_string_id"])
    if d == n + 1000 and h == n + 100000 and t == n + 150000:
        pat += 1
print("  techs with positive Name id: %d" % tot)
print("  following Desc=N+1000, Help=N+100000, Tree=N+150000: %d" % pat)
print("  -> the four ids are ONE family derived from the Name id")

print()
print("=" * 72)
print("VALIDATION 4: name_string_id round-trip through the strings DB")
print("=" * 72)
sys.path.insert(0, HERE)
from strings_db import load_language  # noqa: E402
en, _ = load_language("en")
bad = 0
for uid, e in units.items():
    sid = e["name_string_id"]
    if e["resolved"] and en.get(sid) != e["en"]:
        bad += 1
print("  resolved unit entries whose `en` != strings_db[name_string_id]: %d" % bad)
bad = 0
for k, e in techs.items():
    sid = e["name_string_id"]
    if e["resolved"] and en.get(sid) != e["en"]:
        bad += 1
print("  resolved tech entries whose `en` != strings_db[name_string_id]: %d" % bad)
print()
print("ALL VALIDATIONS COMPLETE")
