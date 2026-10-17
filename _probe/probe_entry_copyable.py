"""Can a new cache entry be copied from another civ's shipped entry?

If a node id carries the SAME RequiredAge / RequiredUnitID / gate keys in every
civ that lists it, then copying a donor entry is safe and the writer never has to
invent a field.  If they vary, the entry has to be built from the tree row and the
copy rule would silently ship the donor's numbers.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
panels = BP.load_all(tk.game_root)

per = {}
for key, rec in panels.items():
    obj = rec["obj"]
    for blk in BP.buildings(obj, key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            per.setdefault(e.get("ID"), []).append((key, e))

print("distinct unit node ids in the cache: %d" % len(per))
varying = {}
for nid, lst in per.items():
    for field in ("RequiredAge", "Name"):
        vals = {e.get(field) for _k, e in lst}
        if len(vals) > 1:
            varying.setdefault(field, []).append((nid, len(lst), sorted(
                str(v) for v in vals)[:5]))
    extra = {tuple(sorted(k for k in e if k not in BP.ENTRY_KEYS)) for _k, e in lst}
    if len(extra) > 1:
        varying.setdefault("extra keys", []).append((nid, len(lst),
                                                     sorted(extra)[:3]))
for field, rows in varying.items():
    print("  %-12s varies for %d node ids   e.g. %s"
          % (field, len(rows), rows[:4]))
if not varying:
    print("  nothing varies -- a donor entry could be copied verbatim")
print()

# For nodes that DO vary in RequiredAge, is the donor entry's value the modal one?
print("if we copy the FIRST civ's entry, how often is RequiredAge the modal one?")
ok = bad = 0
examples = []
for nid, lst in per.items():
    ages = [e.get("RequiredAge") for _k, e in lst]
    if len(set(ages)) <= 1:
        continue
    modal = max(set(ages), key=ages.count)
    if lst[0][1].get("RequiredAge") == modal:
        ok += 1
    else:
        bad += 1
        if len(examples) < 6:
            examples.append((nid, lst[0][0], lst[0][1].get("RequiredAge"), modal,
                             sorted(set(str(a) for a in ages))))
print("  modal %d, not modal %d" % (ok, bad))
for e in examples:
    print("    %s" % (e,))
