import _gamepaths as GP
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused diagnostics on the three suspicious semantic flags:
  (a) 5000 graphics with negative SLP -- exactly 5000 is a suspiciously round number
  (b) 5733 empty unit names
  (c) 601 tech Civ indices out of 0..62 -- presumably the -1 sentinel
plus an INDEPENDENT ground-truth check: known AoE2 DE unit stats by unit ID."""

import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

data, how = P.load_dat(GP.DAT)
p = P.Parser(data)
s = p.parse()
print()

gs = s["graphics"]
neg = [g for g in gs if g["slp"] < 0]
print("(a) negative-SLP graphics: %d ; value histogram: %r"
      % (len(neg), dict(collections.Counter(g["slp"] for g in neg).most_common(6))))
print("    their file field empty? %r" % collections.Counter(g["file"] == "" for g in neg))
print("    their name field empty? %r" % collections.Counter(g["name"] == "" for g in neg))
print("    their layer histogram: %r" % dict(collections.Counter(g["layer"] for g in neg)))
print("    their delta counts: %r"
      % dict(collections.Counter(len(g["deltas"]) for g in neg).most_common(6)))
print("    ALL-parse SLP histogram (most common): %r"
      % dict(collections.Counter(g["slp"] for g in gs).most_common(8)))

all_units = [u for c in s["civs"] for u in c["units"]]
empties = [u for u in all_units if not u["name"]]
print("\n(b) empty-name units: %d of %d" % (len(empties), len(all_units)))
print("    their Type histogram: %r" % dict(collections.Counter(u["type"] for u in empties)))
print("    their hp: %r" % dict(collections.Counter(u["hit_points"] for u in empties).most_common(5)))
print("    their id range: %d..%d" % (min(u["id"] for u in empties), max(u["id"] for u in empties)))
print("    per-civ count (first 6): %r" % [sum(1 for u in c["units"] if not u["name"]) for c in s["civs"][:6]])

civs = [t["civ"] for t in s["techs"]]
print("\n(c) tech Civ value histogram (first 10): %r" % dict(collections.Counter(civs).most_common(10)))
print("    min=%d max=%d ; count of -1 = %d ; out of [-1,62] = %d"
      % (min(civs), max(civs), sum(1 for v in civs if v == -1),
         sum(1 for v in civs if not (-1 <= v < len(s["civs"])))))

# --- independent ground truth: known AoE2 DE base stats by unit ID ----------
KNOWN_IDS = {
    4:   ("ARCHR (Archer)",              30),
    7:   ("Skirmisher",                  30),
    8:   ("Longbowman",                  35),
    38:  ("Knight",                     100),
    74:  ("Militia",                     40),
    75:  ("Man-at-Arms",                 45),
    83:  ("Villager",                    25),
    93:  ("Spearman",                    45),
    448: ("SCOUT (Scout Cavalry)",       45),
    546: ("Light Cavalry",               60),
    751: ("Eagle Scout",                 50),
}
civ0 = s["civs"][0]
byid = {u["id"]: u for u in civ0["units"]}
print("\n(indep) civ[0] name=%r  units=%d" % (civ0["name"], len(civ0["units"])))
print("(indep) known AoE2 DE unit stats from unit ID:")
hits = 0
for uid, (label, expect_hp) in sorted(KNOWN_IDS.items()):
    u = byid.get(uid)
    if u is None:
        print("    id=%-4d %-28s -> ABSENT" % (uid, label))
        continue
    mark = "OK " if u["hit_points"] == expect_hp else "MISMATCH"
    if u["hit_points"] == expect_hp:
        hits += 1
    print("    id=%-4d %-28s -> name=%-14r hp=%-6d expected_hp=%-6d %s"
          % (uid, label, u["name"], u["hit_points"], expect_hp, mark))
print("(indep) %d/%d known-HP IDs match exactly" % (hits, len(KNOWN_IDS)))

# names of a few units by id, to see the internal naming convention
print("\n(indep) internal names for ids 0..16 in civ[0]:")
for u in civ0["units"][:17]:
    print("    id=%-4d name=%-18r type=%-3d hp=%d" % (u["id"], u["name"], u["type"], u["hit_points"]))
