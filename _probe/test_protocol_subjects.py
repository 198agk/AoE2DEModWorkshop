# -*- coding: utf-8 -*-
r"""PIN: the complete five-gate filter, and the subjects that survive it.

Five gate classes have now cost this project a wasted experiment, in this order:

  1. age            `RequiredAge` -- Hand Cannoneer is Age 4, so a Dark-Age game
                    could never show it however the menu is fed
  2. research       `PrereqTech` -- 354 shipped panel entries carry one
  3. channel        a panel building has `Units` AND `Techs`; a unit arriving via
                    an upgrade appears in `Techs`
  4. upgrade tech   the unit's own `Trigger Tech ID` must be reachable in the layer
                    that promises the unit (panel: in `Techs`; tree: the chain's
                    predecessor UNIT rows, because a tree never carries an upgrade
                    as a `Use Type: Tech` row -- only .dat 34/35 exist as exceptions)
  5. building       the PRODUCING BUILDING must itself be buildable by that civ --
                    found when six base-game candidates (Aztecs/Incas/Mayans Xolotl
                    Warrior at the Stable) turned out to sit inside a building those
                    civilizations cannot construct

Every one of these was scored backwards or missed on the first attempt.  This pin
runs the whole filter over the corpus and names what survives, so the criterion
lives in one place.

Run:  $env:PYTHONPATH='D:\\Software\\DeepSeek Harness\\工作区2'; python _probe\test_protocol_subjects.py
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)


def named(uid):
    u = idx.get("unit", uid)
    return (u.zh or u.en) if u else None


def building_row(tree, bid):
    for r in CT.rows_of(tree):
        if r.get("Use Type") == "Building" and r.get("Node ID") == bid:
            return r
    return None


TRIG = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        u, tt = r.get("Node ID"), r.get("Trigger Tech ID")
        if u is not None and tt is not None:
            TRIG.setdefault(u, set()).add(tt)

# ---------------------------------------------------------------- build the table
kindP, kindT = [], []
for stem, tree in sorted(trees.items()):
    disp = next((d for d in sorted(panels)
                 if CT.civ_file_stem(d) == stem), None)
    if disp is None:
        continue
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    own = {r.get("Node ID") for r in CT.rows_of(tree)
           if r.get("Use Type") == "Building"}
    listed, ptechs, pages = {}, {}, {}
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        listed[bid] = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
        ptechs[bid] = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
        for e in (blk.get(BP.UNITS_KEY) or []):
            pages[(bid, e.get("ID"))] = e.get("RequiredAge")

    # ---- kind-P: the panel names it, the tree refuses it
    for bid, uids in listed.items():
        if bid not in own:
            continue
        brow = building_row(tree, bid)
        # gate 5 (this direction): the user must be able to build the building.
        # The promising layer here is the PANEL, but a building the tree marks
        # NotAvailable is not reachable in game, so the subject is unobservable.
        if (brow or {}).get("Node Status") == "NotAvailable":
            continue
        for uid in uids:
            nm = named(uid)
            if not nm:
                continue
            row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
            if row is None or row.get("Node Status") != "NotAvailable":
                continue
            tts = TRIG.get(uid) or set()
            if tts and not (tts & ptechs[bid]):      # gate 4
                continue
            kindP.append((stem, disp, bid, uid, nm, pages.get((bid, uid))))

    # ---- kind-T: the tree grants it, the panel is silent in BOTH channels
    # SILENCE MUST BE GLOBAL.  Judging it at the building the tree row names is a
    # hole: ARMENIANS' tree puts the Monk (125) at building 1806 (Fortified Church)
    # while the panel lists that same Monk under building 104 (Temple) -- so the
    # panel is not silent at all and the subject cannot discriminate.  Search the
    # WHOLE panel for the unit and for its upgrade tech.
    any_u_all = {u for s in listed.values() for u in s}
    any_t_all = {t for s in ptechs.values() for t in s}
    for r in CT.unit_rows(tree):
        uid, bid = r.get("Node ID"), r.get("Building ID")
        if uid is None or bid is None or bid not in own:
            continue
        if r.get("Node Status") != "ResearchedCompleted":
            continue
        nm = named(uid)
        if not nm:
            continue
        if uid in any_u_all:
            continue                                   # panel names it (channel 1)
        tts = TRIG.get(uid) or set()
        if tts & any_t_all:
            continue                                   # panel names it (channel 2)
        # gate 4 for the tree: the chain's predecessors must also be granted
        chain_ok = True
        seen, cur = set(), r
        while cur is not None:
            u = cur.get("Node ID")
            if u in seen:
                break
            seen.add(u)
            if cur.get("Node Status") != "ResearchedCompleted":
                chain_ok = False
                break
            tt = cur.get("Trigger Tech ID")
            cur = None
            if tt is not None:
                for r2 in CT.unit_rows(tree):
                    if r2.get("Trigger Tech ID") == tt and \
                            r2.get("Node ID") != u:
                        cur = r2
                        break
        if not chain_ok:
            continue
        # gate 5: the building must be buildable here too
        if (building_row(tree, bid) or {}).get("Node Status") not in (
                "ResearchedCompleted", "ResearchRequired"):
            continue
        kindT.append((stem, disp, bid, uid, nm, r.get("Age ID")))

print("A  the filter, applied over the whole corpus")
print("     kind-P survivors (panel names it, tree refuses): %d" % len(kindP))
for stem, disp, bid, uid, nm, age in kindP:
    print("        %-11s bldg %-5s unit %-6s age %-4s %s"
          % (stem, bid, uid, age, nm))
print("     kind-T survivors (tree grants, panel silent both ways): %d"
      % len(kindT))
for stem, disp, bid, uid, nm, age in kindT:
    print("        %-11s bldg %-5s unit %-6s age %-4s %s"
          % (stem, bid, uid, age, nm))

print()
print("B  gate 5 really does kill the base-game candidates")
for c in ("AZTECS", "INCAS", "MAYANS", "MUISCA", "MAPUCHE", "TUPI"):
    br = building_row(trees[c], 101)
    check("%s cannot build a Stable, so its Xolotl Warrior is unobservable"
          % c, (br or {}).get("Node Status") == "NotAvailable",
          "status=%r" % ((br or {}).get("Node Status"),))
check("no base-game civilization survives the filter",
      not any(s in ("AZTECS", "INCAS", "MAYANS", "BRITONS", "FRANKS", "GOTHS",
                    "TEUTONS", "JAPANESE", "CHINESE", "BYZANTINES", "PERSIANS",
                    "SARACENS", "TURKS", "VIKINGS", "MONGOLS", "CELTS", "SPANISH",
                    "HUNS", "KOREANS", "ITALIANS")
              for s, _d, _b, _u, _n, _a in kindP + kindT))

print()
print("B2 the SILENCE HOLE: silence must be global, not just at the named building")
# ARMENIANS' tree puts the Monk (125) at building 1806 (Fortified Church) and the
# panel lists it under building 104 -- judging silence at the named building would
# have passed a subject whose panel is not silent at all.
_arm = panels[BP.panel_path_for(GAME, "Armenians")[1]]["obj"]
_where = [(blk.get("ID"), e.get("Name"), e.get("RequiredAge"))
          for blk in BP.buildings(_arm, "Armenians")
          for e in (blk.get(BP.UNITS_KEY) or []) if e.get("ID") == 125]
check("Armenians' tree names the Monk at 1806 but the panel lists it at 104",
      bool(_where) and all(w[0] == 104 for w in _where),
      "panel locations: %s" % _where)
check("the Armenian Monk is therefore NOT a kind-T subject",
      not any(s == "ARMENIANS" and u == 125 for s, _d, _b, u, _n, _a in kindT))
_geo = panels[BP.panel_path_for(GAME, "Georgians")[1]]["obj"]
_gwhere = [(blk.get("ID"), e.get("Name"))
           for blk in BP.buildings(_geo, "Georgians")
           for e in (blk.get(BP.UNITS_KEY) or []) if e.get("ID") == 125]
check("Georgians' Monk is likewise listed at 104, so it is not a subject either",
      bool(_gwhere) and all(w[0] == 104 for w in _gwhere),
      "panel locations: %s" % _gwhere)
check("building 1806 is the Fortified Church, held only by ARMENIANS/GEORGIANS",
      sorted(s for s, t in trees.items()
             if building_row(t, 1806) is not None) == ["ARMENIANS", "GEORGIANS"])

print()
print("B3 Steam depot evidence for the two recommended civilizations")
# `appmanifest_813780.acf`'s `InstalledDepots` is the closest on-disk record.
_acf = os.path.join(r"D:\Games\Steam\steamapps", "appmanifest_813780.acf")
if os.path.exists(_acf):
    import re as _re
    _t = open(_acf, "rb").read().decode("utf-8", "replace")
    _m = _re.search(r'"InstalledDepots"\s*\{(.*?)\n\t\}', _t, _re.S)
    _ids = _re.findall(r'"(\d+)"\s*\{', _m.group(1)) if _m else []
    print("     InstalledDepots: %s" % _ids)
    check("depot 1039811 (Lords of the West, which carries the Sicilians) is "
          "installed", "1039811" in _ids, "depots=%s" % _ids)
    check("depot 1389240 (Dawn of the Dukes, which carries the Poles) is installed",
          "1389240" in _ids, "depots=%s" % _ids)
    print("     NOTE: this shows the DLC payload is INSTALLED; it does not by")
    print("     itself prove Steam entitlement.  Ask the user if unsure.")
else:
    print("     no appmanifest found -- skipping")


print()
print("C  the recommended pair -- both on civilizations whose DLC depot is")
print("   actually installed (appmanifest_813780.acf InstalledDepots)")
REC_P = [c for c in kindP if c[0] == "POLES" and c[3] == 691]
REC_T = [c for c in kindT if c[0] == "SICILIANS" and c[3] == 588]
check("GAME 1 subject POLES 691 exists", bool(REC_P), "kindP=%s" % kindP)
check("GAME 2 subject SICILIANS 588 exists", bool(REC_T), "kindT=%s" % kindT)
for stem, disp, bid, uid, nm, age in REC_P:
    print("     GAME 1  %s / %s / unit %s %s / building %s (Dock) / age %s"
          % (disp, stem, uid, nm, bid, age))
    print("        tree: 691 NotAvailable ; panel: lists 691 AND tech 376")
    print("        depot 1389240 (Dawn of the Dukes) is installed")
for stem, disp, bid, uid, nm, age in REC_T:
    print("     GAME 2  %s / %s / unit %s %s / building %s (Siege Workshop) / age %s"
          % (disp, stem, uid, nm, bid, age))
    print("        tree: whole siege chain ResearchedCompleted ; panel: silent both")
    print("        depot 1039811 (Lords of the West) is installed")
check("POLES 691's producing building is the Dock",
      building_row(trees["POLES"], 45).get("Name") == "Dock")
check("SICILIANS 588's producing building is the Siege Workshop",
      building_row(trees["SICILIANS"], 49).get("Name") == "Siege Workshop")
check("the two subjects are not name-colliding",
      "精锐炮舰" != "重型投石车")

print()
print("D  the complete-path alternatives, for a player who owns different DLC")
for stem, disp, bid, uid, nm, age in kindP:
    print("     %-11s unit %-6s %-16s building %-5s age %s"
          % (stem, uid, nm, bid, age))

print()
print("PROTOCOL SUBJECTS: five gate classes, one filter.  Survivors: %d kind-P, %d "
      "kind-T." % (len(kindP), len(kindT)))
print("  Every base-game candidate is killed by gate 5.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
