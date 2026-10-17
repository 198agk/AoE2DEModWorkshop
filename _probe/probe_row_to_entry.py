"""How does a TECH-TREE row become a CACHE entry?

The cache is the artifact; the tree is the source.  Before anything writes the
cache, this measures the mapping the shipped pair actually uses, per status:
which keys appear, and where the values come from.  Guessing this mapping is how
a writer produces a file that parses and says the wrong thing.
"""
import json
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
print("panel civs %d, tree civs %d" % (len(panels), len(trees)))
print()

# Which tree keys/values explain which panel keys?
pairs = 0
key_hist = {}
value_src = {}
status_keys = {}
for tk_key, entries in panels.items():
    stem = CT.civ_file_stem(tk_key)
    if stem not in trees:
        continue
    tree = trees[stem]
    for blk in BP.buildings(entries["obj"], tk_key):
        bid = blk.get("ID")
        for e in (blk.get(BP.UNITS_KEY) or []):
            nid = e.get("ID")
            row = None
            for r in CT.unit_rows(tree):
                if r.get("Node ID") == nid and r.get("Building ID") == bid:
                    row = r
                    break
            if row is None:
                for r in CT.unit_rows(tree):
                    if r.get("Node ID") == nid:
                        row = r
                        break
            if row is None:
                continue
            pairs += 1
            for k in e:
                key_hist[k] = key_hist.get(k, 0) + 1
            st = row.get("Node Status")
            status_keys.setdefault(st, {}).setdefault(tuple(sorted(e)), 0)
            status_keys[st][tuple(sorted(e))] += 1
            for pk, candidates in (("ID", ("Node ID",)),
                                   ("Name", ("Name",)),
                                   ("RequiredAge", ("Age ID",))):
                if pk in e:
                    for c in candidates:
                        value_src.setdefault(pk, {}).setdefault(c, 0)
                        if e.get(pk) == row.get(c):
                            value_src[pk][c] += 1
print("matched (civ,building,unit) entry/row pairs: %d" % pairs)
print("entry key histogram:", dict(sorted(key_hist.items(),
                                          key=lambda kv: -kv[1])))
print()
print("value provenance (how often the entry value equals the row field):")
for pk, d in value_src.items():
    print("  %-12s %s" % (pk, dict(sorted(d.items(), key=lambda kv: -kv[1]))))
print()
print("entry key-sets by the row's Node Status (top 6 each):")
for st in sorted(status_keys):
    common = sorted(status_keys[st].items(), key=lambda kv: -kv[1])[:6]
    print("  %-20s pairs=%-5d %s"
          % (st, sum(status_keys[st].values()),
             [(list(k), v) for k, v in common]))
print()

# Where does PrereqTech come from?  Those entries exist; what is the source?
print("ResearchRequired rows that the cache shows WITH a PrereqTech:")
hits = 0
src_counts = {}
for tk_key, entries in panels.items():
    stem = CT.civ_file_stem(tk_key)
    if stem not in trees:
        continue
    tree = trees[stem]
    for blk in BP.buildings(entries["obj"], tk_key):
        bid = blk.get("ID")
        for e in (blk.get(BP.UNITS_KEY) or []):
            if "PrereqTech" not in e:
                continue
            row = None
            for r in CT.unit_rows(tree):
                if r.get("Node ID") == e.get("ID") and r.get("Building ID") == bid:
                    row = r
                    break
            if row is None:
                continue
            hits += 1
            for c in ("Trigger Tech ID", "Node ID", "Building ID", "Age ID"):
                if e.get("PrereqTech") == row.get(c):
                    src_counts[c] = src_counts.get(c, 0) + 1
            if hits <= 4:
                print("   panel %s bldg %s -> %s" % (e.get("ID"), bid,
                                                     json.dumps(
                                                         {k: e[k] for k in e})))
                print("     row  status=%s Trigger Tech ID=%s Link=%s"
                      % (row.get("Node Status"), row.get("Trigger Tech ID"),
                         row.get("Link Node Type")))
print("  total %d; PrereqTech equals row field: %s" % (hits, src_counts))
print()

# The 15 building disagreements: which building should the writer trust?
print("building the cache uses vs the tree's Building ID (units only):")
same = diff = 0
for tk_key, entries in panels.items():
    stem = CT.civ_file_stem(tk_key)
    if stem not in trees:
        continue
    tree = trees[stem]
    for blk in BP.buildings(entries["obj"], tk_key):
        bid = blk.get("ID")
        for e in (blk.get(BP.UNITS_KEY) or []):
            rows = [r for r in CT.unit_rows(tree) if r.get("Node ID") == e.get("ID")]
            if not rows:
                continue
            if any(r.get("Building ID") == bid for r in rows):
                same += 1
            else:
                diff += 1
print("  same %d, different %d" % (same, diff))
