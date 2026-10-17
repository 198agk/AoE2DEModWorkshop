"""List-aware contrast: my earlier per-civ record diff compared SCALARS only, so
it could not see a difference sitting inside `attributes` / `type50` / `costs`.

Given the user's correction (m19924: the game reads the .dat), the remaining
question is whether "can civ X build unit Y" is a per-civ difference INSIDE the
unit record.  Print the record's key shape, then diff every field including
lists, between a civ that can build a unit and one that cannot.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402
import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
dat_civs = tk._civs
trees = CT.load_trees(tk.game_root)
by_stem = {}
for c in dat_civs:
    by_stem.setdefault(CT.civ_file_stem(c["name"]), c["name"])

# Show the full key set of one unit record, so we know what there is to compare.
sample = None
for c in dat_civs:
    for u in c["units"]:
        if u["id"] == 41:
            sample = u
            break
    if sample:
        break
print("unit 41 record keys:")
for k in sorted(sample.keys()):
    v = sample[k]
    kind = type(v).__name__
    if isinstance(v, list):
        kind = "list[%d]" % len(v)
    elif isinstance(v, dict):
        kind = "dict[%d]" % len(v)
    print("   %-32s %s" % (k, kind))
print()

pairs = {}
for stem in trees:
    for row in CT.unit_rows(trees[stem]):
        st = row.get("Node Status")
        if st == "ResearchedCompleted":
            pairs.setdefault(row.get("Node ID"), {})["yes"] = stem
        elif st == "NotAvailable":
            pairs.setdefault(row.get("Node ID"), {})["no"] = stem
usable = [(n, d["yes"], d["no"]) for n, d in pairs.items()
          if "yes" in d and "no" in d]


def rec(civ_name, uid):
    for c in dat_civs:
        if c["name"] == civ_name:
            for u in c["units"]:
                if u["id"] == uid:
                    return u
    return None


def canon(u):
    out = {}
    for k, v in u.items():
        if k.startswith("_"):
            continue
        out[k] = v
    return json.dumps(out, sort_keys=True, default=str)


diffs = {}
for uid, yes, no in usable:
    a = rec(by_stem[yes], uid)
    b = rec(by_stem[no], uid)
    if a is None or b is None:
        continue
    ja, jb = json.loads(canon(a)), json.loads(canon(b))
    for k in set(ja) | set(jb):
        if ja.get(k) != jb.get(k):
            diffs[k] = diffs.get(k, 0) + 1

print("FULL-record (incl. lists) differences over %d can/cannot pairs:" % len(usable))
for k, n in sorted(diffs.items(), key=lambda kv: -kv[1]):
    print("   %-28s differs in %d/%d" % (k, n, len(usable)))
if not diffs:
    print("   NONE")
