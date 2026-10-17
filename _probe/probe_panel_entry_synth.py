"""How do you BUILD a cache entry that is not in the shipped file yet?

`probe_grant_entry_needs.py` showed that for 963 of 967 grant cases some other
civ's cache already holds an entry for that node, so the writer should COPY
rather than invent.  That leaves the question those numbers cannot answer: copy
it HOW?

The oracle is shipped, not invented.  402 (civ, node) pairs exist in a cache
while the tree calls them NOT ResearchedCompleted (391 ResearchRequired + 11
NotAvailable).  For each of those the shipped entry is a real answer, so a
candidate rule can be scored against it exactly: does the rule, given only the
tree row and the OTHER civs' entries, reproduce the bytes the file actually has?

Rules scored:
  R1  donor entry verbatim
  R2  donor entry, `Name` taken from the target's own tree row
  R3  donor entry, `RequiredAge` taken from the target's own tree row (Age ID)
  R4  R2 + R3

The donor is chosen by the same discipline as `civtechtrees.donor_row`: a civ
whose tree row for this node is ResearchedCompleted first, then the most common
variant, then name order (so the result never depends on dict iteration order).
"""
import collections
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

# every shipped cache entry, keyed by node id
pool = collections.defaultdict(list)
for key, rec in panels.items():
    for blk in BP.buildings(rec["obj"], key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            pool[e.get("ID")].append((key, blk.get("ID"), e))


def _frozen(entry):
    return tuple(sorted((k, repr(v)) for k, v in entry.items()))


def pick_donor(node_id, exclude_civ, ready):
    """(key, building_id, entry) -- ranked like civtechtrees.donor_row."""
    cands = [c for c in pool.get(node_id, []) if c[0] != exclude_civ]
    if not cands:
        return None
    ready_donors = [c for c in cands if ready(c[0])]
    use = ready_donors or cands
    freq = collections.Counter(_frozen(c[2]) for c in use)
    return min(use, key=lambda c: (-freq[_frozen(c[2])], c[0]))


def row_of(civ_key, node_id):
    stem = CT.civ_file_stem(civ_key)
    tree = trees.get(stem)
    if tree is None:
        return None
    return CT.row_for(tree, node_id, CT.UNIT_USE_TYPES)


def ready(civ_key):
    row = row_of(civ_key, None) if False else None  # placeholder, unused
    return False


cases = 0
agree = {"R1": 0, "R2": 0, "R3": 0, "R4": 0}
disagree_samples = []
no_donor = 0
for stem in sorted(trees):
    key = BP.civ_key_for(panels, stem)
    if key is None:
        continue
    for row in CT.unit_rows(trees[stem]):
        nid = row.get("Node ID")
        if row.get("Node Status") == "ResearchedCompleted":
            continue
        shipped = None
        for bkey, bid, e in pool.get(nid, []):
            if bkey == key:
                shipped = e
                break
        if shipped is None:
            continue          # absent from the cache: nothing to score against
        cases += 1

        def _is_ready(ck, _nid=nid):
            r = row_of(ck, _nid)
            return bool(r) and r.get("Node Status") == "ResearchedCompleted"

        got = pick_donor(nid, key, _is_ready)
        if got is None:
            no_donor += 1
            continue
        _dkey, _dbid, dentry = got
        variants = {"R1": dict(dentry)}
        v2 = dict(dentry)
        if row.get("Name") is not None:
            v2["Name"] = row["Name"]
        variants["R2"] = v2
        v3 = dict(dentry)
        if row.get("Age ID") is not None:
            v3["RequiredAge"] = row["Age ID"]
        variants["R3"] = v3
        v4 = dict(v3)
        if row.get("Name") is not None:
            v4["Name"] = row["Name"]
        variants["R4"] = v4
        for name, v in variants.items():
            if v == shipped:
                agree[name] += 1
        if variants["R3"] != shipped and len(disagree_samples) < 12:
            diff = {}
            for k in set(shipped) | set(variants["R3"]):
                if shipped.get(k) != variants["R3"].get(k):
                    diff[k] = (shipped.get(k), variants["R3"].get(k))
            disagree_samples.append((stem, nid, row.get("Name"),
                                     row.get("Age ID"), diff))

print("cases where the cache already lists a non-RC node: %d" % cases)
print("   no donor entry anywhere to copy from               : %d" % no_donor)
print()
for k in ("R1", "R2", "R3", "R4"):
    print("   %s reproduces the shipped entry : %d / %d  (%.1f%%)"
          % (k, agree[k], cases, 100.0 * agree[k] / max(cases, 1)))
print()
print("   R4 disagreements (shipped vs R4) -- first %d:"
      % len(disagree_samples))
for s in disagree_samples:
    print("     %s" % (s,))
