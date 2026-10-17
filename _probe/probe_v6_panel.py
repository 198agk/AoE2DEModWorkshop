# -*- coding: utf-8 -*-
r"""What does the v6 panel file actually say about unit 2550?

An earlier ad-hoc walk over the emitted `futuravailableunits.json` printed NOTHING
for the British, which would mean the panel entry never landed -- yet the user saw
the button (after a Castle).  One of those two facts is wrong, so measure it
properly here: enumerate every civ/building that lists unit 2550 in the emitted
panel, the shipped panel, and v5's panel.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod.game import buildpanel as BP                   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PANEL = os.path.join(GAME, "resources", "_common", "dat", "futuravailableunits.json")
V5 = os.path.join(HERE, "out_dshtest_v5", "resources", "_common", "dat",
                  "futuravailableunits.json")
V6 = os.path.join(HERE, "out_dshtest_v6", "resources", "_common", "dat",
                  "futuravailableunits.json")
UNIT = 2550


def scan(label, path):
    print("=" * 76)
    print("%s   exists=%s" % (label, os.path.exists(path)))
    print("=" * 76)
    if not os.path.exists(path):
        return
    # ★ The panel's TOP LEVEL is a dict keyed by CIV NAME, not a `civs` list --
    # an earlier version of this probe read `obj["civs"]`, got None, and printed
    # "0 listings", which looks like a measurement but is a wrong accessor.
    # Use the product's own load path so the probe cannot disagree with it.
    text, obj = BP.load_panel(path)
    print("  top-level keys: %d civs; first: %s"
          % (len(obj), list(obj.keys())[:6]))
    hits = 0
    for civ_key in sorted(obj):
        # ★ `BP.buildings` returns a list of building BLOCKS (dicts with "ID"),
        # not a list of ids.  Passing a block where an id is expected returns []
        # from `entries()` -- which reads exactly like "the entry is absent".
        for blk in BP.buildings(obj, civ_key):
            bid = blk.get("ID")
            for e in BP.entries(obj, civ_key, bid, BP.UNITS_KEY):
                if e.get("ID") == UNIT:
                    hits += 1
                    print("     %-14s building %-5s -> %s"
                          % (civ_key, bid, json.dumps(e, ensure_ascii=False,
                                                      sort_keys=True)))
    print("  listings of unit %d: %d" % (UNIT, hits))
    for civ_key in ("Britons", "Incas"):
        if civ_key not in obj:
            continue
        for blk in BP.buildings(obj, civ_key):
            bid = blk.get("ID")
            if bid in (12, 87):
                ids = [e.get("ID") for e in
                       BP.entries(obj, civ_key, bid, BP.UNITS_KEY)]
                print("     %-8s building %-4s has %d units: %s"
                      % (civ_key, bid, len(ids), ids))
    print()


scan("SHIPPED", PANEL)
scan("V5 EMITTED", V5)
scan("V6 EMITTED", V6)

print("=" * 76)
print("the tree rows again, verbatim")
print("=" * 76)
for lbl, root in (("V5", os.path.join(HERE, "out_dshtest_v5")),
                  ("V6", os.path.join(HERE, "out_dshtest_v6"))):
    p = os.path.join(root, "resources", "_common", "dat", "CivTechTrees",
                     "BRITONS.json")
    if not os.path.exists(p):
        print("  %s: missing" % lbl)
        continue
    o = json.loads(open(p, "rb").read().decode("utf-8"), strict=False)
    rows = [x for x in o.get("civ_techs_units", []) if x.get("Node ID") == UNIT]
    print("  %s British row: %s" % (lbl, json.dumps(rows, ensure_ascii=False,
                                                    sort_keys=True)))
