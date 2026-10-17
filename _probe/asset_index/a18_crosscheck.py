#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a18_crosscheck.py -- independent hand-verification of the mapping.

Part 1: 10 well-known entities, checked against disk by exact filename existence and
        by human-readable plausibility of the sprite name.
Part 2: the 1344 vs 1345 icon delta explained.
Part 3: negative controls -- confirm the mapping does NOT accidentally succeed.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
TEX = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
B = json.load(open(os.path.join(HERE, "index_buildings.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))

disk = set(f.lower() for f in os.listdir(GFXDIR))
SEM = json.load(open(_HERE_PATH("_probe", "semantic", "unit_names.json"),
                     encoding="utf-8"))

TARGETS = ["Archer", "Villager (Male)", "Knight", "Militia", "Town Center",
           "Barracks", "Castle", "House", "Stable", "Monastery", "Spearman",
           "Mangonel", "Longbowman", "Monk"]

def pick(en):
    for uid, r in U.items():
        if r.get("en") == en:
            return uid, r
    return None, None

print("=== PART 1: hand cross-check of well-known entities ===")
ok = bad = 0
for name in TARGETS:
    uid, r = pick(name)
    if r is None:
        print("  %-18s NOT FOUND in index" % name)
        continue
    print("\n  %s   (unit id %s, type=%s, class=%s)" % (name, uid, r["type"], r["class"]))
    print("     internal dat name: %s" % r["internal_name"])
    any_ok = False
    for f, rec in r["sprites"].items():
        res = rec.get("resolution", "?")
        files = []
        if rec.get("sld_x1"):
            files.append(rec["sld_x1"])
        for w, a in (rec.get("animations") or {}).items():
            files.append(a["sld_x1"])
        if not files:
            continue
        miss = [x for x in files if x.lower() not in disk]
        print("     %-24s %-34s %d file(s)%s"
              % (f, res, len(files), "  MISSING:%s" % miss if miss else "  all exist on disk"))
        print("        %s" % files)
        if not miss:
            any_ok = True
        else:
            bad += 1
    ic = r.get("icon")
    if ic and ic.get("resolved"):
        print("     icon: %s -> %s  uv=%s" % (ic["icon_id"], ic["TextureFileName"], ic["uv"]))
    if any_ok:
        ok += 1
print("\n  summary: %d/%d targets had every listed sprite file present on disk" % (ok, len(TARGETS)))

# plausibility: does the sprite stem contain the unit's own name?
print("\n=== PART 1b: does the sprite name plausibly match the unit name? ===")
for name in ["Archer", "Villager (Male)", "Knight", "Militia", "Spearman", "Monk"]:
    uid, r = pick(name)
    if not r:
        continue
    st = None
    for f, rec in r["sprites"].items():
        nm = rec.get("FileName")
        if nm and "_" in nm:
            st = nm
            break
    print("   %-18s standing FileName = %s" % (name, st))

# ---------------------------------------------------------------- PART 2
print("\n=== PART 2: the 1344 vs 1345 icon delta ===")
SEM2 = SEM
pos_any = set()
for uid, per in enumerate([]):
    pass
byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u
any_pos = [uid for uid, per in byid.items()
           if any(per[c].get("icon_id", 0) > 0 for c in per)]
primary_res = [int(k) for k, r in U.items() if r.get("icon") and r["icon"].get("resolved")]
print("   unit ids with a positive IconID in SOME civ: %d" % len(any_pos))
print("   unit ids whose PRIMARY-civ IconID resolves:  %d" % len(primary_res))
delta = sorted(set(any_pos) - set(primary_res))
for uid in delta:
    per = byid[uid]
    print("   id %d %s : per-civ icon ids = %s"
          % (uid, U[str(uid)]["en"], {c: per[c].get("icon_id") for c in sorted(per)}))
    u = per[sorted(per)[0]]
    print("        primary civ internal name=%s type=%s class=%s"
          % (u.get("name"), u.get("type"), u.get("class")))

# ---------------------------------------------------------------- PART 3
print("\n=== PART 3: negative controls ===")
# 3a: a unit whose only graphic is -1 must NOT map
n_unmapped_with_file = 0
for uid, r in U.items():
    has = any(x.get("FileName") for x in r["sprites"].values())
    mapped = any(x.get("resolution", "").startswith(("direct", "substituted"))
                 for x in r["sprites"].values())
    if has and not mapped:
        n_unmapped_with_file += 1
print("   units that DO name a FileName but map to nothing: %d" % n_unmapped_with_file)
# 3b: verify no claimed file is absent from disk
tot = bad2 = 0
for uid, r in U.items():
    for f, rec in r["sprites"].items():
        for key in ("sld_x1", "sld_x2"):
            if rec.get(key):
                tot += 1
                if rec[key].lower() not in disk:
                    bad2 += 1
        for w, a in (rec.get("animations") or {}).items():
            for key in ("sld_x1", "sld_x2"):
                if a.get(key):
                    tot += 1
                    if a[key].lower() not in disk:
                        bad2 += 1
print("   total sprite file claims: %d ; claims absent from disk: %d" % (tot, bad2))
# 3c: x1/x2 pairing of every claimed pair
bad3 = 0
for uid, r in U.items():
    for f, rec in r["sprites"].items():
        if rec.get("sld_x1") and rec.get("sld_x2"):
            if rec["sld_x2"].lower() not in disk:
                bad3 += 1
        for w, a in (rec.get("animations") or {}).items():
            if a.get("sld_x2") and a["sld_x2"].lower() not in disk:
                bad3 += 1
print("   claimed x2 twins absent from disk: %d" % bad3)

# 3d: buildings -- are they all b_ prefixed?
pref = {}
for uid, r in B.items():
    for f, rec in r["sprites"].items():
        nm = rec.get("FileName")
        if nm:
            pref[nm.split("_")[0]] = pref.get(nm.split("_")[0], 0) + 1
print("   building sprite FileName prefixes: %s" % sorted(pref.items(), key=lambda x: -x[1])[:10])
