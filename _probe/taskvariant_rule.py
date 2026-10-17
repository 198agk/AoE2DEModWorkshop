"""Is there a GENERAL rule for task variants, or is the naming convention the
only handle?

The naming rule (VM*/VF*) works for villagers but is an internal-name heuristic,
and internal names are known to be unreliable in this dat.  This tests three
candidate general rules against the CONFIRMED villager set (the user saw the
engine swap 村民 -> 建筑者, so 83 and 118 are ground truth) plus the whole
29-unit live family:

  R1 icon_id     : the same player-facing thing draws the same button icon
  R2 sort_number : the same thing sorts together in the UI
  R3 t50 signature: same combat profile

A rule is only usable if it (a) groups the whole family and (b) does not sweep
up unrelated units.
"""
import collections
import os
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod import api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
by = {}
for c in tk._civs:
    for u in c["units"]:
        by.setdefault(u["id"], u)

# live villager family: type 70, class 4, the ones that actually carry hp
VILL = sorted(i for i, u in by.items()
              if (u.get("name") or "").startswith(("VM", "VF"))
              and u.get("type") == 70 and u.get("class") == 4)
print("live villager family (type70 class4 VM*/VF*): %d -> %s" % (len(VILL), VILL))
print()

for field in ("icon_id", "sort_number", "name"):
    vals = collections.Counter(by[i].get(field) for i in VILL)
    print("R  %-12s distinct values across family: %d  %s"
          % (field, len(vals), dict(list(vals.items())[:6])))
print()

for field in ("icon_id", "sort_number"):
    print("=== %s as the key: does it group the family without over-reaching? ===" % field)
    groups = collections.defaultdict(list)
    for i, u in by.items():
        if u.get("type") == 70 and u.get("class") == 4:
            groups[u.get(field)].append(i)
    tot = 0
    for k, ids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(ids) < 2:
            continue
        covered = sorted(set(ids) & set(VILL))
        tot += len(ids)
        print("   %-10s size %-4d  family-covered %-3d  ids %s"
              % (k, len(ids), len(covered), ids[:12]))
    print("   ids in non-singleton type70/class4 groups: %d (family is %d)" % (tot, len(VILL)))
    print()

print("=== the real question: which OTHER units share the family's icon_id? ===")
ic = collections.Counter(by[i].get("icon_id") for i in VILL)
print("   family icon_id histogram:", dict(ic))
for k, _ in ic.most_common(3):
    same = sorted(i for i, u in by.items() if u.get("icon_id") == k)
    print("   icon_id %-6s total %-4d  includes family %-3d  outsiders: %s"
          % (k, len(same), len(set(same) & set(VILL)),
             [x for x in same if x not in VILL][:14]))
