"""Does the semantic index close the last 2 cases of the entry-synthesis rule?

`probe_panel_entry_synth.py` scored four rules against the 402 shipped
(civ, node) cache entries whose tree row is NOT ResearchedCompleted.  R3 (donor
entry verbatim + `RequiredAge` from the target's own `Age ID`) reproduced 400.

The 2 misses are both Chronicles renames -- ATHENIANS calls unit 5
`Gastraphetes` where everyone else says `Hand Cannoneer`, SPARTANS calls unit
2140 `Octeres`.  The semantic index carries `Entity.civ_variants` (it was built
to explain exactly the 118 ids that resolve to different names under different
civs), so the question is whether consulting it is enough to close the gap.

R5 = R3 + `Name` from the semantic index's per-civ variant when there is one.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.semantic.index import index as sem_index  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
panels = BP.load_all(tk.game_root)
trees = CT.load_trees(tk.game_root)
sem = sem_index()

# --- what shape is civ_variants?  print before using it. -------------------
ent = sem.get("unit", 5)
print("Entity.civ_variants for unit 5: %r" % (getattr(ent, "civ_variants", None),))
ent2 = sem.get("unit", 2140)
print("Entity.civ_variants for unit 2140: %r"
      % (getattr(ent2, "civ_variants", None),))
print()

pool = collections.defaultdict(list)
for key, rec in panels.items():
    for blk in BP.buildings(rec["obj"], key):
        for e in (blk.get(BP.UNITS_KEY) or []):
            pool[e.get("ID")].append((key, blk.get("ID"), e))


def _frozen(entry):
    return tuple(sorted((k, repr(v)) for k, v in entry.items()))


def row_of(stem, node_id):
    tree = trees.get(stem)
    return CT.row_for(tree, node_id, CT.UNIT_USE_TYPES) if tree else None


def pick(node_id, exclude, ready):
    cands = [c for c in pool.get(node_id, []) if c[0] != exclude]
    if not cands:
        return None
    fit = [c for c in cands if ready(c[0])] or cands
    freq = collections.Counter(_frozen(c[2]) for c in fit)
    return min(fit, key=lambda c: (-freq[_frozen(c[2])], c[0]))


def variant_name(node_id, civ_key):
    """The name this civ uses for this node, if the index records a variant.

    `civ_variants` is ``{string_id: {en, zh, civs: [...]}}`` -- the civs sit in a
    list INSIDE each variant, not as the outer key.  Reading the outer key as a
    civ name finds nothing and silently reports "no variant", which is exactly
    the shape of bug this project keeps paying for.
    """
    e = sem.get("unit", node_id)
    v = getattr(e, "civ_variants", None)
    if not isinstance(v, dict):
        return None
    want = CT.civ_file_stem(civ_key)
    for val in v.values():
        if not isinstance(val, dict):
            continue
        for c in (val.get("civs") or []):
            if CT.civ_file_stem(c) == want:
                return val.get("en")
    return None


cases = 0
agree = collections.Counter()
for key in sorted(panels):
    stem = CT.civ_file_stem(key)
    tree = trees.get(stem)
    if tree is None:
        continue
    for row in CT.unit_rows(tree):
        nid = row.get("Node ID")
        if row.get("Node Status") == "ResearchedCompleted":
            continue
        shipped = None
        for bk, _bid, e in pool.get(nid, []):
            if bk == key:
                shipped = e
                break
        if shipped is None:
            continue
        cases += 1

        def _ready(ck, _n=nid):
            r = row_of(CT.civ_file_stem(ck), _n)
            return bool(r) and r.get("Node Status") == "ResearchedCompleted"

        got = pick(nid, key, _ready)
        if got is None:
            continue
        r3 = dict(got[2])
        if row.get("Age ID") is not None:
            r3["RequiredAge"] = row["Age ID"]
        if r3 == shipped:
            agree["R3"] += 1
        r5 = dict(r3)
        vn = variant_name(nid, key)
        if vn:
            r5["Name"] = vn
        if r5 == shipped:
            agree["R5"] += 1
        if r5 != shipped:
            diff = {k: (shipped.get(k), r5.get(k))
                    for k in set(shipped) | set(r5)
                    if shipped.get(k) != r5.get(k)}
            print("  MISS  %s %s  variant=%r  %s" % (key, nid, vn, diff))

print()
print("cases: %d" % cases)
for k in ("R3", "R5"):
    print("   %s reproduces the shipped entry : %d / %d  (%.1f%%)"
          % (k, agree[k], cases, 100.0 * agree[k] / max(cases, 1)))
