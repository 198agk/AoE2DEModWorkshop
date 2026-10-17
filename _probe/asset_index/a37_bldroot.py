#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a37_bldroot.py -- reconcile the two building-prefix metrics.

a35 measured the prefix of ONE graphic (the standing slot) and found 20 type-80
entities whose art is not b_*.  a36 measures the DOMINANT prefix over all resolved
sprite fields and finds 86.  This script prints both metrics for every type-80 entity
so the report can state which one it uses and why the numbers differ.
"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))


def prefix_of(sld):
    return sld.split("_")[0] if sld else None


rows = []
for k, r in U.items():
    if r["type"] != 80:
        continue
    st = (r["sprites"].get("standing_1") or {})
    stand_pref = prefix_of(st.get("sld_x1"))
    if stand_pref is None:
        for a in (st.get("animations") or {}).values():
            stand_pref = prefix_of(a.get("sld_x1"))
            if stand_pref:
                break
    allf = [x.get("sld_x1") for x in r["sprites"].values() if x.get("sld_x1")]
    for x in r["sprites"].values():
        allf += [a.get("sld_x1") for a in (x.get("animations") or {}).values() if a.get("sld_x1")]
    c = collections.Counter(prefix_of(f) for f in allf if f)
    dom = c.most_common(1)[0][0] if c else None
    rows.append((int(k), r["en"], r["class"], stand_pref, dom, len(allf), dict(c)))

n_stand = sum(1 for x in rows if x[3] != "b")
n_dom = sum(1 for x in rows if x[4] != "b")
n_mixed = sum(1 for x in rows if x[6] and len(x[6]) > 1)
print("type-80 entities: %d" % len(rows))
print("  standing-graphic prefix != 'b_' : %d   (a35's metric)" % n_stand)
print("  dominant prefix      != 'b_'    : %d   (a36's metric)" % n_dom)
print("  sprite set mixes several prefixes: %d" % n_mixed)

print("\n--- the %d entities whose DOMINANT prefix is not b_ (a36 'type80_only') ---" % n_dom)
print("%-6s %-34s %-4s %-6s %-6s %s" % ("id", "en", "cls", "stand", "dom", "prefix counts"))
only_dom = [x for x in rows if x[4] != "b"]
only_dom.sort(key=lambda x: x[4] or "")
for uid, en, cls, sp, dom, n, c in only_dom:
    print("%-6d %-34s %-4s %-6s %-6s %s" % (uid, (en or "")[:34], cls, sp, dom, c))

print("\n--- the %d entities whose STANDING prefix is not b_ but DOMINANT is b_ ---"
      % (n_stand - n_dom))
for uid, en, cls, sp, dom, n, c in [x for x in rows if x[3] != "b" and x[4] == "b"]:
    print("%-6d %-34s cls=%-3s stand=%-4s dom=%-3s %s" % (uid, (en or "")[:34], cls, sp, dom, c))
