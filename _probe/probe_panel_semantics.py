"""Is the cache's absence itself a statement?  And what are the Name mismatches?

Two questions the writer's correctness depends on:
  A. Does the cache omit rows the tree lists as NotAvailable?  If a NotAvailable
     row is still listed, the file carries no status and a set_status edit has
     nothing to write there.
  B. Where the entry's Name differs from the row's Name, which one is right?
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
panels = BP.load_all(tk.game_root)
trees = CT.load_trees(tk.game_root)

print("A  per-status: how many tree unit rows the cache lists, and misses")
tally = {}
misses = {}
for stem, tree in trees.items():
    key = BP.civ_key_for(panels, stem)
    if key is None:
        continue
    obj = panels[key]["obj"]
    listed = {}
    for blk in BP.buildings(obj, key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            listed[e.get("ID")] = blk.get("ID")
    for row in CT.unit_rows(tree):
        st = row.get("Node Status")
        nid = row.get("Node ID")
        t = tally.setdefault(st, {"present": 0, "absent": 0})
        if nid in listed:
            t["present"] += 1
        else:
            t["absent"] += 1
            if st in ("NotAvailable", "ResearchRequired"):
                misses.setdefault(st, []).append((stem, nid, row.get("Name")))
for st in sorted(tally):
    print("   %-20s %s" % (st, tally[st]))
print()
for st in ("NotAvailable", "ResearchRequired"):
    rows = misses.get(st, [])
    print("   %s rows the cache omits: %d%s"
          % (st, len(rows), ("  e.g. " + str(rows[:6])) if rows else ""))
print()

print("B  entry Name vs row Name")
diff = []
for stem, tree in trees.items():
    key = BP.civ_key_for(panels, stem)
    if key is None:
        continue
    obj = panels[key]["obj"]
    rows = {}
    for r in CT.unit_rows(tree):
        rows.setdefault(r.get("Node ID"), r)
    for blk in BP.buildings(obj, key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            r = rows.get(e.get("ID"))
            if r and e.get("Name") != r.get("Name"):
                diff.append((stem, e.get("ID"), e.get("Name"), r.get("Name"),
                             r.get("Name String ID")))
print("   mismatching entries: %d of 3122" % len(diff))
for d in diff[:12]:
    print("     %-14s id=%-5s cache=%r row=%r string_id=%s" % d)
print()

print("C  RequiredAge: entry vs row Age ID, where they differ")
bad = []
for stem, tree in trees.items():
    key = BP.civ_key_for(panels, stem)
    if key is None:
        continue
    obj = panels[key]["obj"]
    rows = {}
    for r in CT.unit_rows(tree):
        rows.setdefault(r.get("Node ID"), r)
    for blk in BP.buildings(obj, key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            r = rows.get(e.get("ID"))
            if r and r.get("Age ID") is not None \
                    and e.get("RequiredAge") != r.get("Age ID"):
                bad.append((stem, e.get("ID"), e.get("RequiredAge"),
                            r.get("Age ID")))
print("   mismatching RequiredAge: %d" % len(bad))
for d in bad[:12]:
    print("     %-14s id=%-5s cache=%s row=%s" % d)
