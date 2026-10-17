"""Contrast, not presence: for one unit id, diff its per-civ `.dat` record between
a civ whose tree says it CAN build it and a civ whose tree says NotAvailable.

Every field that differs is a candidate for the availability mechanism.  This is
the only shape of test that can find a gate: comparing two civs' records for the
SAME unit, where the answer is known to differ.

The user's correction (m19924) says the game reads the .dat, so if availability is
a dat-side fact it must be visible as a field difference here.  If instead the two
civs' records are byte-identical in every field the parser models, then the gate
is NOT in the unit record and the honest answer is that it lives in the
tech/effect layer -- which is also a dat-side answer, just not a per-civ field.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
dat_civs = tk._civs
trees = CT.load_trees(tk.game_root)

# stem -> dat civ name
by_stem = {}
for c in dat_civs:
    by_stem.setdefault(CT.civ_file_stem(c["name"]), c["name"])


def status_of(stem, unit_id):
    tree = trees.get(stem)
    if tree is None:
        return None
    for row in CT.unit_rows(tree):
        if row.get("Node ID") == unit_id:
            return row.get("Node Status")
    return None


def rec_of(civ_name, unit_id):
    for c in dat_civs:
        if c["name"] != civ_name:
            continue
        for u in c["units"]:
            if u["id"] == unit_id:
                return u
    return None


# Collect (unit_id, stem_yes, stem_no) triples: a unit that some civs can build
# and others are told NotAvailable.  Use the tree as the known-good label; it is
# what the game's own UI is built from.
pairs = {}
for stem in trees:
    for row in CT.unit_rows(trees[stem]):
        nid = row.get("Node ID")
        st = row.get("Node Status")
        if st == "ResearchedCompleted":
            pairs.setdefault(nid, {})["yes"] = stem
        elif st == "NotAvailable":
            pairs.setdefault(nid, {})["no"] = stem

usable = [(nid, d["yes"], d["no"]) for nid, d in pairs.items()
          if "yes" in d and "no" in d]
print("unit ids with both a can-build civ and a NotAvailable civ: %d"
      % len(usable))
print()

# Flatten a record to comparable scalars only (skip offsets / nested lists).
def flat(u):
    out = {}
    for k, v in u.items():
        if k.startswith("_"):
            continue
        if isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v
    return out


diffs = {}
samples = []
for nid, yes, no in usable:
    a = rec_of(by_stem[yes], nid)
    b = rec_of(by_stem[no], nid)
    if a is None or b is None:
        continue
    fa, fb = flat(a), flat(b)
    keys = set(fa) | set(fb)
    d = sorted(k for k in keys if fa.get(k) != fb.get(k))
    for k in d:
        diffs[k] = diffs.get(k, 0) + 1
    if d and len(samples) < 12:
        samples.append((nid, yes, no, [(k, fa.get(k), fb.get(k)) for k in d]))

print("fields that differ between can-build and NotAvailable records")
if not diffs:
    print("  NONE -- the two civs' records for the same unit are identical in "
          "every modelled scalar field.")
else:
    for k, n in sorted(diffs.items(), key=lambda kv: -kv[1]):
        print("  %-28s differs in %d of %d pairs" % (k, n, len(usable)))
print()
for nid, yes, no, d in samples:
    print("unit %d  %s(can) vs %s(NotAvailable)" % (nid, yes, no))
    for k, va, vb in d[:8]:
        print("    %-24s %-14s %-14s" % (k, va, vb))
print()
# Also: is the record present at all in both?  (membership was already shown
# not to separate them, but print it so the reader sees the contrast is real.)
missing = sum(1 for nid, yes, no in usable
              if rec_of(by_stem[yes], nid) is None
              or rec_of(by_stem[no], nid) is None)
print("usable pairs where either civ has no such record at all: %d" % missing)
