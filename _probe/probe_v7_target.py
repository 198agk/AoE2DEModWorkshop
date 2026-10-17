# -*- coding: utf-8 -*-
r"""What exactly carries the Castle gate on the British Champi Scout button?

v5 and v6 both show the Barracks button only AFTER a Castle is built (user m26421),
so the gate is neither `EnablingResearch` (v6 removed it) nor the button slot.

This prints every layer side by side, BRITONS-v6 against INCAS-shipped, and flags
whichever field differs in a way that could mean "Castle":

  * the tree row (Age ID is the age gate the panel copies its RequiredAge from)
  * the panel entry (RequiredAge)
  * tech 263 'Longbow (make avail)' -- its owner, prerequisites and locations
  * the British unit 2550 record and its TechTree UnitConnection
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from aoe2mod.dat import locate as L                          # noqa: E402
from aoe2mod.dat import parser as P                          # noqa: E402
from aoe2mod.game import buildpanel as BP                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
V6 = os.path.join(HERE, "out_dshtest_v6")
UNIT = 2550
KEYS = ("Node ID", "Node Type", "Node Status", "Age ID", "Building ID",
        "Trigger Tech ID", "Link ID", "Picture Index", "Name String ID")

print("=" * 78)
print("1  TREE ROW for unit %d" % UNIT)
print("=" * 78)
shipped = CT.load_trees(GAME)
v6 = CT.load_trees(V6)
for label, trees, civ in (("SHIPPED INCAS", shipped, "INCAS"),
                          ("SHIPPED BRITONS", shipped, "BRITONS"),
                          ("V6 BRITONS", v6, "BRITONS"),
                          ("V6 INCAS", v6, "INCAS")):
    row = CT.row_for(trees.get(civ) or {}, UNIT, CT.UNIT_USE_TYPES)
    print("  %-16s %s" % (label,
                          "NO ROW" if row is None
                          else json.dumps({k: row.get(k) for k in KEYS},
                                          ensure_ascii=False)))

print()
print("=" * 78)
print("2  PANEL ENTRY for unit %d" % UNIT)
print("=" * 78)
for label, root in (("SHIPPED", GAME), ("V6", V6)):
    panels = BP.load_all(root)
    for civ in ("Britons", "Incas"):
        hits = []
        for ck in (panels or {}):
            if CT.civ_file_stem(ck) != civ.upper():
                continue
            obj = panels[ck]["obj"]
            for b in (BP.buildings(obj, ck) or {}):
                for e in (BP.entries(obj, ck, b, BP.UNITS_KEY) or []):
                    if e.get("ID") == UNIT:
                        hits.append((ck, b, e))
        print("  %-8s %-8s %s" % (label, civ,
                                  json.dumps(hits, ensure_ascii=False) if hits
                                  else "not listed"))

print()
print("=" * 78)
print("3  DAT: tech 263 and the British unit %d record" % UNIT)
print("=" * 78)
for label, path in (("SHIPPED", os.path.join(
        GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")),
        ("V6", os.path.join(V6, "resources", "_common", "dat",
                            "empires2_x2_p1.dat"))):
    data, how = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    print("  --- %s" % label)
    for tn in (263, 1350):
        t = p.stats["techs"][tn]
        print("     tech %-5d name=%-28r civ=%-4s eff=%-5s req=%s"
              % (tn, t.get("name"), t.get("civ"), t.get("effect_id"),
                 t.get("required_techs")))
        print("            locs=%s" % (t.get("research_locations"),))
    brit = next(c for c in p.stats["civs"] if c["name"] == "British")
    rec = next((u for u in brit["units"] if u.get("id") == UNIT), None)
    if rec is None:
        print("     British unit %d: NO RECORD" % UNIT)
    else:
        tl = [{k: v for k, v in x.items() if not k.startswith("_")}
              for x in (rec.get("train_locations") or [])]
        print("     British unit %d: enabled=%s disabled=%s train=%s"
              % (UNIT, rec.get("enabled"), rec.get("disabled"),
                 json.dumps(tl, ensure_ascii=False)))

print()
print("=" * 78)
print("4  TechTree UnitConnection for %d (Champi line + the Castle unit 8)" % UNIT)
print("=" * 78)
import probe_regional_recipe as PRR                          # noqa: E402
for label, path in (("SHIPPED", os.path.join(
        GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")),
        ("V6", os.path.join(V6, "resources", "_common", "dat",
                            "empires2_x2_p1.dat"))):
    data2, _h = P.load_dat(path)
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(data2)
        pr.parse()
    conn, pX = PRR.connections(data2, pr.r.gv)
    print("  --- %s" % label)
    for uid in (2550, 2552, 2554, 2588, 8):
        c = conn.get(uid)
        if c is None:
            print("     unit %-5d (no connection)" % uid)
            continue
        print("     unit %-5d %s" % (uid, json.dumps(c, ensure_ascii=False)))
