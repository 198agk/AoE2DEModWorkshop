"""What the panel cache actually contains, per civ and per key.

Before wiring `unit.availability` to also write `futuravailableunits.json` I need
its exact contract:

  * top-level keys (civ display names?) and each civ's block keys;
  * does every building have a `Techs` list, and is it ever NON-empty?  If it is
    always empty then this cache covers the UNIT space only and a tech grant has
    no place in it;
  * the sibling `paphosfutureavailableunits.json` -- is it per-mode (Paphos) or a
    second full copy?
  * whether `futuravailableunits.json` mentions any of the 8 tech-side family
    ids or tech ids at all.

Run:  python _probe/probe_fu_shape.py
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat")


def load(path):
    return json.loads(open(path, "rb").read().decode("utf-8-sig"))


def main():
    tk = A.open_toolkit()
    d = os.path.join(tk.game_root, DAT_REL)
    fu = load(os.path.join(d, "futuravailableunits.json"))
    pap = load(os.path.join(d, "paphosfutureavailableunits.json"))

    print("futuravailableunits.json")
    print("  top-level keys: %d" % len(fu))
    print("  %s" % sorted(fu)[:8])
    bkeys = Counter()
    tlen = Counter()
    for civ in fu:
        for blk in fu[civ].get("Buildings", []):
            for k in blk:
                bkeys[k] += 1
            tlen[len(blk.get("Techs") or [])] += 1
    print("  building keys: %s" % dict(bkeys))
    print("  len(Techs) histogram: %s" % dict(sorted(tlen.items())))
    nonempty = [b for civ in fu for b in fu[civ].get("Buildings", [])
                if b.get("Techs")]
    print("  buildings with a non-empty Techs: %d" % len(nonempty))
    for b in nonempty[:5]:
        print("    %s" % json.dumps(b, ensure_ascii=False)[:220])
    print()

    print("paphosfutureavailableunits.json")
    print("  top-level keys: %d -> %s" % (len(pap), sorted(pap)[:8]))
    if pap:
        k0 = sorted(pap)[0]
        print("  block keys for %r: %s" % (k0, sorted(pap[k0])[:6]))
        same = set(pap) & set(fu)
        print("  civ keys shared with futuravailableunits: %d of %d"
              % (len(same), len(pap)))
    print()

    # does the unit panel file mention tech ids at all?
    trees = None
    from aoe2mod.game import civtechtrees as CT
    trees = CT.load_trees(tk.game_root)
    tech_ids = set()
    for civ in list(trees)[:3]:
        for r in CT.tech_rows(trees[civ]):
            tech_ids.add(r.get("Node ID"))
    text = json.dumps(fu)
    hits = [t for t in sorted(tech_ids) if ('"ID": %d' % t) in text
            or ('"ID":%d' % t) in text]
    print("tech node ids (sampled %d from 3 civs) appearing as an \"ID\" in the"
          " unit cache: %d" % (len(tech_ids), len(hits)))
    print("  (a hit only means the integer appears; it may be a unit id)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
