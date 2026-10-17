# -*- coding: utf-8 -*-
"""Print the raw label every unit binding produces, for one unit.

The sweeper guard caught "armour cls 4" surviving the five-place label fix.
This enumerates ALL bindings so the extent is measured rather than guessed --
including the FORWARD mirror path, which walks the schema's inline `mirror`
dict, and that dict is a second place a label can be missing from.
"""
import os, sys, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from aoe2mod import api as A
from aoe2mod.intent import compiler as C

_RAW = re.compile(r"(cost type\s*\d+|attack cls\s*\d+|armour cls\s*\d+|"
                  r"location\[|train\[|creatable tail|hit_points|max_range|"
                  r"speed|min_range|accuracy|garrison_capacity|reload_time|"
                  r"line_of_sight|creation_time|displayed_)")

tk = A.open_toolkit()
tk._ensure()
intents, bindings = C.load_schema()

# unit 12 = Barracks (an age-variant building: gives class entries to mirror),
# unit 38 = Knight, unit 4 = Archer.  Between them every armour/attack class
# shape appears.
for uid in (12, 38, 4):
    hit = C.L.find_units(tk._civs, uid)[0]
    rec = hit[2]
    print("=" * 72)
    print("unit %d  (%s)" % (uid, rec.get("_dll_name")))
    for name, b in (bindings.get("unit_fields") or {}).items():
        try:
            ts = list(C._targets_for_unit(bindings, rec, b))
        except Exception as exc:
            print("  %-24s ERROR %r" % (name, exc))
            continue
        if not ts:
            continue
        labs = [t[3] for t in ts]
        bad = [x for x in labs if _RAW.search(x.replace(" (mirror)", ""))]
        mark = "  <<< LEAK" if bad else ""
        print("  %-24s %s%s" % (name, labs, mark))
