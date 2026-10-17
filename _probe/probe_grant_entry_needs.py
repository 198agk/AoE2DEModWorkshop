"""What does the writer need for a GRANT?  The exact cases a user can ask for.

For every (civ, node) that `availability.plan` would accept, the write has to add
a cache entry.  Two things decide whether that is easy:
  A. does the civ's cache have the building block the TREE row names?
  B. is there a donor civ whose shipped cache entry for this node can be copied
     verbatim (so the writer never invents a Name or a gate field)?
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402
from aoe2mod.intent import availability as AV  # noqa: E402

tk = A.open_toolkit()
panels = BP.load_all(tk.game_root)
trees = CT.load_trees(tk.game_root)

# donor cache entries keyed by node id -> (civ_key, building_id, entry)
donors = {}
for key, rec in panels.items():
    for blk in BP.buildings(rec["obj"], key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            donors.setdefault(e.get("ID"), []).append((key, blk.get("ID"), e))

cases = 0
no_block = 0
no_donor_entry = 0
donor_entry_has_gate = 0
samples = []
for stem in sorted(trees):
    key = BP.civ_key_for(panels, stem)
    if key is None:
        continue
    obj = panels[key]["obj"]
    blocks = {b.get("ID") for b in BP.buildings(obj, key)}
    for r in CT.unit_rows(trees[stem]):
        nid = r.get("Node ID")
        st = r.get("Node Status")
        if st == "ResearchedCompleted":
            continue
        cases += 1
        bid = r.get("Building ID")
        if bid not in blocks:
            no_block += 1
            if len(samples) < 6:
                samples.append(("no block", stem, nid, bid, st))
        d = donors.get(nid)
        if not d:
            no_donor_entry += 1
            if len(samples) < 12:
                samples.append(("no donor entry", stem, nid, bid, st))
        else:
            # prefer a donor whose tree row is ResearchedCompleted
            good = None
            for ck, cbid, e in d:
                dst = CT.node_status(trees.get(CT.civ_file_stem(ck), {}), nid,
                                     CT.UNIT_USE_TYPES)
                if dst == "ResearchedCompleted":
                    good = (ck, cbid, e)
                    break
            if good is None:
                if len(samples) < 18:
                    samples.append(("no resolved donor", stem, nid, bid, st))
            else:
                gate = [k for k in good[2] if k in BP.GATE_KEYS]
                if gate:
                    donor_entry_has_gate += 1
                    if len(samples) < 24:
                        samples.append(("donor gate", stem, nid, bid, st, gate,
                                        good[0]))
print("grant-acceptable (civ, node) cases: %d" % cases)
print("  civ cache lacks the tree row's building block : %d" % no_block)
print("  no civ's cache lists this node at all         : %d" % no_donor_entry)
print("  a resolved donor entry still carries a gate    : %d"
      % donor_entry_has_gate)
print()
for s in samples:
    print("   %s" % (s,))
print()
print("  -> the writer needs a synthesised entry only for %d case(s)"
      % no_donor_entry)
