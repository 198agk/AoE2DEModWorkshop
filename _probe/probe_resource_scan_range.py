"""Why did the resource probe not see the tech cost types it was supposed to?

probe_resource_names.py reported only 10 distinct cost types and NOTHING for the
ids the report records (7 / 506 / 508 / 513).  Either the techs were never
scanned, or the recorded histogram came from a different source.  Find out
before drawing any conclusion from a scan that may have read an empty list.

The lesson being applied: "I scanned every X" is a claim about the RANGE, so
assert the range was non-empty and that each half contributed.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import aoe2mod.api as A                                            # noqa: E402

tk = A.open_toolkit()
tk._ensure()

print("=== what keys does stats actually have? ===")
print(sorted(tk._stats.keys()))
for k, v in sorted(tk._stats.items()):
    try:
        print("  %-14s %s len=%d" % (k, type(v).__name__, len(v)))
    except TypeError:
        print("  %-14s %s (no len)" % (k, type(v).__name__))

print("\n=== tech half: how many techs, how many have costs at all? ===")
techs = tk._stats.get("techs") or ()
print("  techs: %d" % len(techs))
nonempty = [t for t in techs if t.get("costs")]
print("  techs with a non-empty costs list: %d" % len(nonempty))

types = {}
for t in techs:
    for c in (t.get("costs") or ()):
        types[c["type"]] = types.get(c["type"], 0) + 1
print("  distinct tech cost types: %s" % sorted(types.items()))

print("\n=== the ids the report records, searched explicitly ===")
for want in (7, 506, 508, 513):
    hits = []
    for t in techs:
        for c in (t.get("costs") or ()):
            if c["type"] == want:
                hits.append(c)
    us = []
    for civ in tk._civs:
        for rec in civ.get("units", ()):
            for c in (rec.get("costs") or ()):
                if c["type"] == want:
                    us.append(c)
    print("  type %-4d tech slots %-4d unit slots %-4d  sample tech %s unit %s"
          % (want, len(hits), len(us),
             hits[0] if hits else None, us[0] if us else None))

print("\n=== do unit records carry costs under a different key? ===")
civ0 = tk._civs[0]
recs = civ0.get("units", ())
print("  civ[0] units: %d" % len(recs))
sample = [r for r in recs if r.get("costs")][:3]
for r in sample:
    print("  id %-5s costs %s" % (r.get("id"), r.get("costs")))
