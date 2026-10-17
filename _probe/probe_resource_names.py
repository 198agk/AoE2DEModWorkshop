"""Name the cost-slot resource types the dat actually uses.

CORRECTED RANGE.  The first version of this probe iterated
`tk._stats["techs"]` (the raw parser's list) and found ZERO techs carrying costs,
which silently emptied the tech half of the scan and produced a histogram with
only unit types.  Tech costs live in the LOCATOR's records:
`tk._tech_records()` -> `L.locate_techs(raw, tail, tech_start)`.  That is also
what `describe()` reads (api.py:138 `tech.get("costs")` on a `find_techs` hit),
so it is the right source -- being the one the product reads, not merely a
non-empty one.

The range assertion is the point: a scan that covers nothing reports "clean".
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import aoe2mod.api as A                                            # noqa: E402
from aoe2mod.intent import compiler as C                           # noqa: E402

INI_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "schema", "AGE3NamesV0007.json")
names = json.load(open(INI_JSON, encoding="utf-8"))["AoE2DECivResourceNames"]

tk = A.open_toolkit()
tk._ensure()
_b, bindings = C.load_schema()
declared = set(bindings["resource_types"].values())

techs = tk._tech_records()
techs_with = [t for t in techs if t.get("costs")]
units = [r for civ in tk._civs for r in civ.get("units", ())]

print("=== RANGE (assert, do not assume) ===")
print("  techs: %d, of which carrying a costs list: %d" % (len(techs), len(techs_with)))
print("  unit records: %d" % len(units))
assert techs_with, "tech half is empty again -- this probe would report clean vacuously"
assert units, "unit half is empty"

hist = {}      # type -> [tech slots, unit slots]


def _bump(t, which):
    row = hist.setdefault(t, [0, 0])
    row[which] += 1


for t in techs:
    for c in (t.get("costs") or ()):
        _bump(c["type"], 0)
for r in units:
    for c in (r.get("costs") or ()):
        _bump(c["type"], 1)

print("\n=== every distinct cost type in the dat, tech / unit ===")
for t in sorted(hist):
    mark = "declared" if t in declared else "UNMAPPED"
    print("  type %-5d tech %-5d unit %-6d  %-9s ini: %r"
          % (t, hist[t][0], hist[t][1], mark, names.get(str(t))))

print("\n=== per-tech view of the unmapped ones (what a user would see) ===")
for t in (7, 506, 508, 513):
    rows = [(i, c) for i, tech in enumerate(techs)
            for c in (tech.get("costs") or ()) if c["type"] == t]
    print("  type %-4d slots %-4d tech indices %s" % (t, len(rows), [i for i, _ in rows][:12]))
    if rows:
        i, c = rows[0]
        print("        first: %s" % (c,))

print("\n=== would the ini name them? ===")
for t in (7, 506, 508, 513, 214, 215, 501, 514):
    print("  type %-4d -> %r" % (t, names.get(str(t))))
