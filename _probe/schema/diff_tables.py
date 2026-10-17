"""Diff the freshly generated probe tables against the copies inside the package.

Read-only.  Reports, per table, how many entries the new (DE-branch) generation
shares with the shipped copy, which entries changed, and which keys exist only
in the old copy (those are the entries the wrong branch contributed).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

TABLES = ("effect_command_types", "effect_attributes", "armor_classes")
SUBS = ("types", "attributes", "classes")

for name in TABLES:
    new_p = os.path.join(HERE, name + ".json")
    old_p = os.path.join(ROOT, "aoe2mod", "schema", name + ".json")
    new = json.load(open(new_p, encoding="utf-8"))
    try:
        old = json.load(open(old_p, encoding="utf-8"))
    except Exception as exc:                                 # pragma: no cover
        print("---", name, "OLD MISSING:", exc)
        continue
    print("---", name)
    for sub in SUBS:
        if sub not in new:
            continue
        nn, oo = new[sub], (old.get(sub) or {})
        print("  entries new %d | old %d" % (len(nn), len(oo)))
        same = sum(1 for k in nn if oo.get(k) == nn[k])
        print("  identical %d of %d" % (same, len(nn)))
        diffs = [(k, oo.get(k), nn[k]) for k in sorted(nn, key=int) if oo.get(k) != nn[k]]
        print("  changed %d" % len(diffs))
        for d in diffs:
            print("     %-5s old=%-46r new=%r" % d)
        only = sorted((k for k in oo if k not in nn), key=int)
        print("  only-in-old %s" % only)
        for k in only:
            print("     %-5s old=%r" % (k, oo[k]))
