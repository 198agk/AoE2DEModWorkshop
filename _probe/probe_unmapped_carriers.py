"""Who are the entities carrying an unmapped cost type?

The corrected scan (probe_resource_names.py) gives the ids and their slot
counts, but "type 506" is only a defect if nothing can name it.  Two candidate
namers exist and they are NOT the same kind of table:

  * AGE3NamesV0007.ini [AoE2DECivResourceNames] -- AGE's own name for a civ
    resource slot (id 7 = 'Relics Captured', 214/215 = Mercenary Kipchak).  It
    names 4 of the 8 unmapped ids and leaves 501/506/508/513/514 as None.
    (SUPERSEDED: the game's own `15000 + type` block names all 8 including
    501/506/508/513/514 -- see `_probe/schema/build_resource_labels.py`.  This
    probe keeps the AGE table only to show WHAT the weaker source could not do.)
  * The entities themselves -- if every carrier of a type is one mechanic (the
    'C-Bonus' family, Satrapy, a specific unit), the honest description is the
    mechanic, not the numeric id.

Also worth measuring: flag.  The whole-dat flag histogram is {0, 1, 2} and
flag 2 occurs only 6 times.  If those 6 are exactly the type 506/508/513 slots,
flag 2 is not an independent variable and must not be presented as one.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import aoe2mod.api as A                                            # noqa: E402
from aoe2mod.semantic import index as semantic                     # noqa: E402

tk = A.open_toolkit()
tk._ensure()
ix = semantic.index()
techs = tk._tech_records()

WANT = (7, 506, 508, 513, 501, 514, 214, 215)

print("=== flag histogram per unmapped type (techs then units) ===")
flag_hist = {}
for t in techs:
    for c in (t.get("costs") or ()):
        flag_hist[(c["type"], c["flag"])] = flag_hist.get((c["type"], c["flag"]), 0) + 1
for civ in tk._civs:
    for r in civ.get("units", ()):
        for c in (r.get("costs") or ()):
            flag_hist[(c["type"], c["flag"])] = flag_hist.get((c["type"], c["flag"]), 0) + 1
allflag2 = sorted(k for k in flag_hist if k[1] == 2)
print("  every (type, flag==2) pair in the dat: %s" % (allflag2,))
print("  count of flag==2 slots: %d"
      % sum(v for k, v in flag_hist.items() if k[1] == 2))

print("\n=== tech carriers, named ===")
for t in (7, 506, 508, 513):
    rows = []
    for i, tech in enumerate(techs):
        for c in (tech.get("costs") or ()):
            if c["type"] == t:
                e = ix.get("tech", i)
                rows.append((i, e.display if e else "?", c["amount"], c["flag"]))
    print("  type %-4d (%d slots):" % (t, len(rows)))
    for i, nm, amt, fl in rows:
        print("      tech %-5d %-34s amount %-4s flag %s" % (i, nm, amt, fl))

print("\n=== unit carriers, named (deduped by id) ===")
for t in (501, 514, 214, 215):
    seen = {}
    for civ in tk._civs:
        for r in civ.get("units", ()):
            for c in (r.get("costs") or ()):
                if c["type"] == t:
                    seen.setdefault(r.get("id"), (c["amount"], c["flag"]))
    print("  type %-4d (%d distinct unit ids):" % (t, len(seen)))
    for uid in sorted(seen)[:10]:
        e = ix.get("unit", uid)
        amt, fl = seen[uid]
        print("      unit %-6s %-26s amount %-5s flag %s"
              % (uid, (e.display if e else "?"), amt, fl))
    if len(seen) > 10:
        print("      ... and %d more" % (len(seen) - 10))
