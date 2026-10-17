# -*- coding: utf-8 -*-
"""Probe: what are a unit's costs and train locations, really?

Establishes the resource-type id mapping and the shape of the cost/train-time
records against ground truth (Archer = 25 wood + 45 gold, Knight = 60 food +
75 gold) BEFORE any of it is encoded in the intent schema.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P
from aoe2mod.dat import locate as L

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

KNOWN = {
    4:  ("Archer", {"wood": 25, "gold": 45}, 35),
    38: ("Knight", {"food": 60, "gold": 75}, 30),
    83: ("Villager", {"food": 50}, 25),
    74: ("Militia", {"food": 60, "gold": 20}, 21),
}


def main():
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    print("parsed %d bytes via %s, gv=%s" % (len(data), how, p.r.gv))

    civs, civs_start, gv, tail = L.locate(data, parser=p)
    print("civs=%d tail=0x%X" % (len(civs), tail))

    for uid, (name, cost, time_) in sorted(KNOWN.items()):
        hits = L.find_units(civs, uid)
        if not hits:
            print("\n%s (id %d): NO RECORDS" % (name, uid))
            continue
        u = hits[0][2]
        print("\n%s (id %d) in %d civs" % (name, uid, len(hits)))
        print("   costs: %s" % [(c["type"], c["amount"], c["flag"])
                                for c in u.get("costs", [])])
        print("   train_locations: %s"
              % [(t["unit_id"], t["train_time"], t["button_id"])
                 for t in u.get("train_locations", [])])
        print("   expected cost %s, train_time %s" % (cost, time_))
        # verify total units seen
        allsum = sum(len(c["units"]) for c in civs)
        print("   (total unit records in dat: %d)" % allsum)

    # resource-type histogram across every cost slot in every civ
    hist = {}
    for c in civs:
        for u in c["units"]:
            for cost in u.get("costs", []):
                if cost["amount"]:
                    hist[cost["type"]] = hist.get(cost["type"], 0) + 1
    print("\nnon-zero cost (type, count) histogram, top 12:")
    for k, v in sorted(hist.items(), key=lambda kv: -kv[1])[:12]:
        print("   type %-4s %d" % (k, v))

    # train-time sanity: which type values appear as cost Type
    print("\ndistinct cost Type values present: %s" % sorted(hist))


if __name__ == "__main__":
    main()
