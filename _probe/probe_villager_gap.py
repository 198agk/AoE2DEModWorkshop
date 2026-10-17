# -*- coding: utf-8 -*-
"""For the villager family, which pictures would a sheep donor actually replace,
and which moments would still show a human?  This decides whether family
expansion alone is enough."""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A
from aoe2mod.dat import families as F
from aoe2mod.game import sprites as S

tk = A.open_toolkit()
tk._ensure()
ix = tk._reskin_art()
civs = tk._parsed[1]
F.warm(tk._stats, game_root=tk.game_root)
fams = F.build_families(civs)

recs = {}
for civ in civs:
    for u in civ["units"]:
        recs.setdefault(u["id"], u)

sheep = ix.art(recs[594])
print("donor 594 Sheep animations: %r" % (sorted(sheep["tokens"]),))
print()

ids = sorted(fams.get(83) or [83])
print("=== each villager family member vs the sheep donor ===")
rows = []
for uid in ids:
    a = ix.art(recs.get(uid))
    if not a or a.get("kind") != "loose":
        continue
    target_keys = set(a["tokens"])
    donor_keys = set(sheep["tokens"])
    covered = sorted(target_keys & donor_keys)
    left = sorted(target_keys - donor_keys)
    pairs, unmapped, extra = S.plan_swap(a, sheep)
    gm = S.grid_mismatches(a, sheep, pairs)
    rows.append((uid, a["stem"], len(pairs), left, gm))
    print("  %-6d %-24s pairs=%d covered=%d left=%r"
          % (uid, a["stem"], len(pairs), len(covered), left))
    if gm:
        print("           grid mismatch: %s"
              % ", ".join("%s %s vs %s" % (g["animation"], g["target"], g["donor"])
                          for g in gm))

print()
allleft = collections.Counter()
for _u, _s, _p, left, _g in rows:
    for t in left:
        allleft[t] += 1
print("=== animations the sheep donor cannot supply, across the family ===")
for t, n in allleft.most_common():
    print("  %-14s needed by %d family member(s)" % (t, n))
print()
print("files a family-wide sheep reskin would write: %d"
      % sum(2 * p for _u, _s, p, _l, _g in rows))

print()
print("=== which DONORS do have the work/carry animations? ===")
need = ("work", "carry", "task", "seed", "underwater")
have = collections.defaultdict(set)
for uid, u in recs.items():
    a = ix.art(u)
    if not a or a.get("kind") != "loose":
        continue
    ks = set(a["tokens"])
    for n in need:
        if n in ks:
            have[n].add(a["stem"])
for n in need:
    print("  %-12s %d stem(s): %r" % (n, len(have[n]), sorted(have[n])[:8]))

print()
print("=== donors that cover ALL of the villager's animations ===")
full = set()
for uid in ids:
    a = ix.art(recs.get(uid))
    if a and a.get("kind") == "loose":
        full |= set(a["tokens"])
print("  the family needs: %r" % (sorted(full),))
cands = []
for uid in sorted(recs):
    a = ix.art(recs[uid])
    if not a or a.get("kind") != "loose":
        continue
    if full <= set(a["tokens"]):
        cands.append((uid, a["stem"]))
print("  %d unit(s) cover all of them: %r" % (len(cands), cands[:12]))
