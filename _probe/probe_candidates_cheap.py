# -*- coding: utf-8 -*-
r"""The full candidate table for the zero-mod experiment, cheapest first.

GAME 1's subject currently needs **Imperial Age**, which is a real burden.  Combine
BOTH disagreement classes:

    kind-P  tree says `NotAvailable`, panel lists the unit
    kind-P' tree has NO ROW at all,    panel lists the unit   (found: 7 more)

Apply the corrected completeness test per layer (the panel is the promising layer,
so it must offer the unit's upgrade research where the unit has one), require a
display name, and sort by the age the unit needs.  Then also report DLC ownership
evidence from Steam so the recommendation cannot land on a civilization the user
does not own.
"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.semantic.index import index as sem_index       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
idx = sem_index()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)


def named(uid):
    u = idx.get("unit", uid)
    return (u.zh or u.en) if u else None


TRIG = {}
for t in trees.values():
    for r in CT.unit_rows(t):
        u, tt = r.get("Node ID"), r.get("Trigger Tech ID")
        if u is not None and tt is not None:
            TRIG.setdefault(u, set()).add(tt)

cands = []
for stem, tree in sorted(trees.items()):
    disp = next((d for d in sorted(panels)
                 if CT.civ_file_stem(d) == stem), None)
    if disp is None:
        continue
    obj = panels[BP.panel_path_for(GAME, disp)[1]]["obj"]
    own = {r.get("Node ID") for r in CT.rows_of(tree)
           if r.get("Use Type") == "Building"}
    for blk in BP.buildings(obj, disp):
        bid = blk.get("ID")
        if bid not in own:
            continue
        techs = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
        for e in (blk.get(BP.UNITS_KEY) or []):
            uid = e.get("ID")
            nm = named(uid)
            if not nm:
                continue
            row = CT.row_for(tree, uid, CT.UNIT_USE_TYPES)
            if row is None:
                kind = "no-row"
            elif row.get("Node Status") == "NotAvailable":
                kind = "NotAvailable"
            else:
                continue
            tts = TRIG.get(uid) or set()
            if tts and not (tts & techs):
                continue          # panel promises the unit but not its research
            cands.append({
                "stem": stem, "disp": disp, "bid": bid, "uid": uid, "name": nm,
                "age": e.get("RequiredAge"), "kind": kind,
                "trig": sorted(tts),
                "tree_status": (row or {}).get("Node Status") or "no row",
                "building": (row or {}).get("Building ID"),
            })

print("A  full candidate table (both disagreement classes, complete paths only)")
print("   total: %d" % len(cands))
print("   by kind: %s" % Counter(c["kind"] for c in cands))
print("   by age : %s" % Counter(c["age"] for c in cands))
print()
cands.sort(key=lambda c: (c["age"] or 9, c["stem"], c["uid"]))
print("   %-13s %-6s %-5s %-4s %-26s %-13s %s"
      % ("civ", "unit", "bldg", "age", "name", "class", "tree says"))
for c in cands:
    print("   %-13s %-6s %-5s %-4s %-26s %-13s %s"
          % (c["stem"], c["uid"], c["bid"], c["age"], c["name"], c["kind"],
             c["tree_status"]))

print()
print("B  the EARLIEST complete-path candidates (age <= 3), which avoid needing "
      "Imperial Age")
for c in cands:
    if (c["age"] or 9) <= 3:
        print("      %-13s bldg %-5s unit %-6s age %-3s %-26s %s"
              % (c["stem"], c["bid"], c["uid"], c["age"], c["name"], c["kind"]))

print()
print("C  Steam ownership evidence (DLC app ids installed for app 813780)")
lib = r"D:\Games\Steam\steamapps"
acf = os.path.join(lib, "appmanifest_813780.acf")
if os.path.exists(acf):
    txt = open(acf, "rb").read().decode("utf-8", "replace")
    import re
    keys = re.findall(r'"([A-Za-z]+)"', txt)
    print("   acf keys present: %s" % sorted(set(keys))[:20])
    for m in re.findall(r'"(InstalledDepots|DLCAppIds|SharedDepots)"\s*\{(.*?)\n\t\}',
                        txt, re.S):
        ids = re.findall(r'"(\d+)"', m[1])
        print("   %s: %d entries %s" % (m[0], len(ids), ids[:25]))
else:
    print("   no appmanifest found at %s" % acf)
print()
print("   NOTE: AoE2DE ships every DLC's data regardless; entitlement is Steam-side,")
print("   so on-disk data CANNOT prove the user owns a DLC.  Ask before relying on")
print("   a DLC civilization for the experiment.")
