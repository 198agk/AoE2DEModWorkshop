# -*- coding: utf-8 -*-
r"""PIN: `button_id` in the .dat is a CHAIN index, not a grid slot.

`train_locations` entries are `{train_time, unit_id, button_id}` where `unit_id` is
the training building.  Reading `button_id` as "the slot number" is wrong -- the
shipped data shows the militia upgrade line sharing ONE value:

    BRITONS barracks (12), from the .dat:
        button_id 1:  74 Militia, 75 Man-at-Arms, 77 Long Swordsman,
                      473 Two-Handed Swordsman, 567 Champion  <- all one group
        button_id 2:  93 Spearman, 358 Pikeman, 359 Halberdier
        button_id 3:  882 Condottiero
        button_id 4:  751/752/753 Eagle line, 759/761 Huskarl, 1699 Flemish,
                      1901/1903 Fire Lancer, 2110/2111 Greek, 2703/2704 Varangian

So a button in the command grid is a **chain** (one button cycles through the
upgrades), and `button_id` names the chain.  This also gives the real shape of the
tree-vs-panel question: the Jurchens disagreement is that the TREE marks only
Militia available while the PANEL lists the whole chain.

Second finding in the same data: the .dat's barracks list contains units that no
civilization in this tree has a row for at all -- other civs' unique units
(361 Nordic Swordsman, 894 Eastern Swordsman, 1974/1976 Swordsman, ...).  The .dat
is a SUPERSET; the tree and the panel each narrow it, in different ways.
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

# button_id per unit at barracks 12, from a playable civ
# `tk._parsed` is the TUPLE `(data, civs, civs_start, gv, tail, how)`, so
# `_parsed[1:3]` is `(civs, civs_start)` -- the second element is an int and
# `civ.get` raised `AttributeError: 'list' object has no attribute 'get'`.
# Index the tuple once, then slice the civ list.
CIVS = tk._parsed[1] or []
GROUPS = defaultdict(set)
for civ in CIVS[1:3]:
    for u in civ.get("units") or []:
        uid = u.get("id")
        if uid is None:
            continue
        for t in (u.get("train_locations") or []):
            if t.get("unit_id") == 12 and t.get("button_id") is not None:
                GROUPS[t["button_id"]].add(uid)

print("A  barracks (12) button groups in the .dat")
for b in sorted(GROUPS):
    print("   button_id %-3s -> %d units: %s"
          % (b, len(GROUPS[b]), sorted(GROUPS[b])[:12]))

MILITIA = {74, 75, 77, 473, 567}
check("the whole militia upgrade line shares ONE button_id",
      any(MILITIA <= g for g in GROUPS.values()),
      "groups: %s" % {k: sorted(v)[:8] for k, v in GROUPS.items()})
check("so button_id is a CHAIN index, not a per-unit grid slot",
      max(len(g) for g in GROUPS.values()) > 3,
      "largest group has %d units" % max(len(g) for g in GROUPS.values()))
check("the spear line shares a different single button_id",
      any({93, 358, 359} <= g for g in GROUPS.values()),
      "groups: %s" % {k: sorted(v)[:8] for k, v in GROUPS.items()})

print()
print("B  the .dat is a SUPERSET of what any one civ can build")
btree = trees["BRITONS"]
in_tree = {r.get("Node ID") for r in CT.unit_rows(btree)}
all_drawn = set().union(*GROUPS.values())
never = sorted(all_drawn - in_tree)
print("   units the .dat trains at barracks 12 : %d" % len(all_drawn))
print("   of those, in BRITONS' tree rows      : %d" % len(all_drawn & in_tree))
print("   in no BRITONS tree row at all        : %d" % len(never))
check("most of the .dat's barracks list is not in one civ's tree",
      len(never) > len(all_drawn & in_tree),
      "in-tree %d vs not %d" % (len(all_drawn & in_tree), len(never)))

print()
print("C  the Jurchens disagreement, expressed in chains")
jt = trees["JURCHENS"]
obj = panels[BP.panel_path_for(GAME, "Jurchens")[1]]["obj"]
panel_ids = set()
for blk in BP.buildings(obj, "Jurchens"):
    for e in (blk.get(BP.UNITS_KEY) or []):
        panel_ids.add(e.get("ID"))
print("   militia chain (button 1), per layer:")
for uid in sorted(MILITIA):
    st = CT.node_status(jt, uid, CT.UNIT_USE_TYPES)
    print("      unit %-6s tree=%-18s panel=%-8s"
          % (uid, st, "listed" if uid in panel_ids else "silent"))
check("the tree offers only Militia while the panel lists the whole chain",
      CT.node_status(jt, 74, CT.UNIT_USE_TYPES) == "ResearchedCompleted"
      and CT.node_status(jt, 77, CT.UNIT_USE_TYPES) == "NotAvailable"
      and 77 in panel_ids)

print()
print("BUTTON SLOTS: button_id is a chain index; one grid button cycles the")
print("  upgrades of its group.  The .dat is a superset; tree and panel each")
print("  narrow it differently.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
