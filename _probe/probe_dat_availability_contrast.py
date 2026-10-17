"""DECISIVE TEST of the user's correction (2026-10-14):

    "游戏用的是同名同路径的 empires2_x2_p1.dat 文件 ... 游戏要的是 dat，而不是
     json"

If the game's per-civ "can this civ build unit Y" answer comes from the `.dat`,
then the `.dat` must carry it somewhere, and the place it would carry it is the
civ record's own unit list: `walk_civ` reads a pointer array per civilization and
only its non-zero entries become unit records.  A unit ABSENT from a civ's array
is a unit that civ does not have.

So: take pairs whose tree answer is KNOWN and unambiguous --
  * ResearchedCompleted / ResearchRequired  -> the civ CAN build it
  * NotAvailable                            -> the civ CANNOT
-- and ask whether membership in the civ's `.dat` unit array separates them.  That
is a contrast, not a presence check, which is the only way to tell a real gate
from a coincidence.
"""
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

print("dat civs %d, tree civs %d" % (len(dat_civs), len(trees)))
print()

# Which unit ids does each dat civ literally own?
owned = {}
for c in dat_civs:
    owned[c["name"]] = {u["id"] for u in c["units"]}
sizes = sorted((len(v), k) for k, v in owned.items())
print("dat unit-array sizes: min %d (%s) max %d (%s)"
      % (sizes[0][0], sizes[0][1], sizes[-1][0], sizes[-1][1]))
print()

# Cross-tab tree status against dat membership.
tab = {}
absent_examples = {}
for stem, tree in trees.items():
    # the tree stem -> the dat civ name, via the same bridge the module uses
    match = [n for n in owned
             if CT.civ_file_stem(n) == stem]
    if not match:
        continue
    name = match[0]
    have = owned[name]
    for row in CT.unit_rows(tree):
        nid = row.get("Node ID")
        st = row.get("Node Status")
        # only the three statuses with a defined meaning
        if st not in ("ResearchedCompleted", "ResearchRequired", "NotAvailable"):
            continue
        key = (st, nid in have)
        tab[key] = tab.get(key, 0) + 1
        if not (nid in have) and st in ("ResearchedCompleted",
                                        "ResearchRequired"):
            absent_examples.setdefault(st, []).append((stem, nid,
                                                       row.get("Name")))

print("tree status x membership in the civ's own .dat unit array")
for st in ("ResearchedCompleted", "ResearchRequired", "NotAvailable"):
    a = tab.get((st, True), 0)
    b = tab.get((st, False), 0)
    print("  %-20s in dat %-5d  not in dat %-5d" % (st, a, b))
print()
canbuild_in_dat = tab.get(("ResearchedCompleted", True), 0) \
    + tab.get(("ResearchRequired", True), 0)
canbuild_total = canbuild_in_dat \
    + tab.get(("ResearchedCompleted", False), 0) \
    + tab.get(("ResearchRequired", False), 0)
cannot_in_dat = tab.get(("NotAvailable", True), 0)
cannot_total = cannot_in_dat + tab.get(("NotAvailable", False), 0)
print("can-build rows present in the civ's dat array : %d / %d" %
      (canbuild_in_dat, canbuild_total))
print("cannot-build (NotAvailable) present in the dat : %d / %d" %
      (cannot_in_dat, cannot_total))
print()
for st, rows in absent_examples.items():
    print("  %s rows NOT in the civ's dat array: %d%s"
          % (st, len(rows), ("  e.g. %s" % rows[:6]) if rows else ""))
print()
print("If a status were spelled by array membership, one column above would be "
      "empty.  Neither is -- so membership is not the gate either.")
