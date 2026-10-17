# -*- coding: utf-8 -*-
"""probe_unmapped_named.py -- do the unnamed cost types now read as words?

The cost slots whose type no intent can name used to reach the UI as a bare
number ("成本 type 506").  The resource_labels table should name the ones AGE
itself names, and must leave the rest as numbers.

This prints, for every cost type that appears in shipped slots but is NOT a
declared resource, the entity that carries it and what describe() now reports.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod import api as A
from aoe2mod.intent import compiler as C
from aoe2mod.dat import locate as L
from aoe2mod.semantic import index as semantic

tk = A.open_toolkit()
tk._ensure()
bindings = C.load_schema()[1]
_ix = semantic.index()

labels = C.load_resource_labels()
print("resource label table: %d ids" % len(labels))
declared = sorted(bindings["resource_types"].values())
print("declared resource ids: %s" % declared)

# Which ids the table names for the ones we care about?
print("\n=== the eight unmapped ids, as the table knows them ===")
for t in (7, 214, 215, 501, 506, 508, 513, 514):
    print("  type %-4s -> %r" % (t, labels.get(t)))

# --- tech side -------------------------------------------------------------
print("\n=== techs carrying an unmapped cost, as describe() reports it ===")
seen_t = {}
for _idx, tech in enumerate(tk._tech_records()):
    _c, um = C.cost_report(bindings, tech.get("costs"))
    for e in um:
        seen_t.setdefault(e["type"], []).append((_idx, e))
for t in sorted(seen_t):
    rows = seen_t[t]
    ids = sorted({tid for tid, _ in rows})
    names = []
    for tid in ids[:4]:
        _e = _ix.get("tech", tid)
        names.append(_e.display if _e else str(tid))
    print("  type %-4s (%d slots) on techs %s" % (t, len(rows), ids))
    print("        name reported: %r   (e.g. %s)"
          % (rows[0][1].get("name"), ", ".join(names)))
    if "name" not in rows[0][1]:
        print("        ^ still a bare number: AGE's ini does not name this id")

# --- unit side -------------------------------------------------------------
print("\n=== units carrying an unmapped cost, as describe() reports it ===")
seen_u = {}
for c in tk._civs:
    for u in c.get("units") or ():
        um = C.cost_report(bindings, u.get("costs"))[1]
        for e in um:
            key = (e["type"], u["id"])
            if key not in seen_u:
                seen_u[key] = (u, e)
by_type = {}
for (t, uid), (u, e) in seen_u.items():
    by_type.setdefault(t, []).append((uid, u, e))
for t in sorted(by_type):
    rows = by_type[t]
    ids = sorted({uid for uid, _, _ in rows})
    print("  type %-4s (%d distinct unit ids) %s" % (t, len(ids), ids[:8]))
    print("        name reported: %r" % (rows[0][2].get("name"),))
    if "name" not in rows[0][2]:
        print("        ^ still a bare number: AGE's ini does not name this id")

# --- the biconditional must be untouched ----------------------------------
print("\n=== the declared ones are unchanged (sanity) ===")
d = tk.describe(22, "tech")
print("  Loom costs: %s" % d["stats"]["costs"])
d = tk.describe(4)
print("  Archer costs: %s" % d["stats"]["costs"])
for uid in (1259, 2162, 2443, 1270):
    d = tk.describe(uid)
    print("  unit %-5s %-22s unmapped=%s"
          % (uid, d["name"], d["stats"].get("unmapped_costs")))
for tid in (699, 1195, 1270, 1323):
    d = tk.describe(tid, "tech")
    print("  tech %-5s %-24s unmapped=%s"
          % (tid, d["name"], d["stats"].get("unmapped_costs")))

# --- every unmapped entry must be either named or deliberately nameless ---
named, nameless = 0, 0
for t, rows in seen_t.items():
    named += 1 if rows[0][1].get("name") else 0
    nameless += 0 if rows[0][1].get("name") else 1
for t, rows in by_type.items():
    if rows[0][2].get("name"):
        named += 1
    else:
        nameless += 1
print("\nnamed ids: %d   deliberately nameless ids: %d" % (named, nameless))
print("every unmapped entry still carries its raw `type`: %s"
      % all("type" in e for rows in list(seen_t.values()) + list(by_type.values())
            for e in [rows[0][1] if isinstance(rows[0][1], dict) else rows[0][2]]))
