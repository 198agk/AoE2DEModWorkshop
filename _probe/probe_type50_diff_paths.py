"""What are the 3 `type50` differences and the 1 `icon_id` difference?

The pin's assertion said "only `civ` may differ" and it failed, which is the
assertion doing its job.  Two possibilities, and they mean opposite things:

  * noise -- an `_`-prefixed key nested one level deeper than strip_offsets
             reaches (e.g. inside a list of dicts inside a dict), or a field
             that legitimately tracks civ (like `civ` itself);
  * signal -- a real per-civ gameplay difference, which would be the first
             candidate gate found inside the unit record.

Print the exact paths that differ, so the classification is read off the data
rather than guessed.
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
civs = tk._civs
trees = CT.load_trees(tk.game_root)
by_stem = {}
for c in civs:
    by_stem.setdefault(CT.civ_file_stem(c["name"]), c["name"])


def rec(civ_name, uid):
    for c in civs:
        if c["name"] == civ_name:
            for u in c["units"]:
                if u["id"] == uid:
                    return u
    return None


def strip_offsets(v):
    if isinstance(v, dict):
        return {k: strip_offsets(x) for k, x in v.items() if not k.startswith("_")}
    if isinstance(v, list):
        return [strip_offsets(x) for x in v]
    return v


def walk_diff(a, b, path, out):
    """Record the FULL PATH of every difference, not just the top-level key."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            walk_diff(a.get(k), b.get(k), path + "." + str(k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, "len %d vs %d" % (len(a), len(b))))
        for i, (x, y) in enumerate(zip(a, b)):
            walk_diff(x, y, "%s[%d]" % (path, i), out)
    elif a != b:
        out.append((path, "%r vs %r" % (a, b)))


pairs = {}
for stem, tax in trees.items():
    for row in CT.unit_rows(tax):
        st = row.get("Node Status")
        nid = row.get("Node ID")
        if st == "ResearchedCompleted":
            pairs.setdefault(nid, {})["yes"] = stem
        elif st == "NotAvailable":
            pairs.setdefault(nid, {})["no"] = stem
usable = [(n, d["yes"], d["no"]) for n, d in pairs.items()
          if "yes" in d and "no" in d]

hits = defaultdict(list)
for uid, yes, no in usable:
    a = strip_offsets(rec(by_stem[yes], uid))
    b = strip_offsets(rec(by_stem[no], uid))
    out = []
    walk_diff(a, b, "", out)
    for path, detail in out:
        if path.lstrip(".") == "civ":
            continue
        hits[path.split("[")[0]].append((uid, by_stem[yes], by_stem[no], path, detail))

print("non-civ difference paths over %d pairs:" % len(usable))
for k, rows in sorted(hits.items(), key=lambda kv: -len(kv[1])):
    print("\n  %s   (%d occurrences)" % (k, len(rows)))
    for uid, yes, no, path, detail in rows[:6]:
        print("     unit %-5d %s(can) vs %s(no)   %s"
              % (uid, yes, no, detail))
        print("            at %s" % path)
if not hits:
    print("   NONE -- the only difference is the civ index")
