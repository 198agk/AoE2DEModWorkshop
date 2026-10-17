# -*- coding: utf-8 -*-
"""Two correctness questions before the reskin recipe is wired:

  A  plan_swap returns 0 pairs SILENTLY when the animations do not overlap.
     How many real unit pairs hit that, and does the caller see anything?
  B  the second int16 (alternate idle) -- does it ever point at a DIFFERENT
     art group?  If so, copying only the standing group leaves half a unit.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import collections
import os
import sys

ROOT = _HERE_PATH()
sys.path.insert(0, ROOT)
import aoe2mod.api as A
from aoe2mod.game import sprites as S

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
tk._ensure()
idx = S.art_index(GAME, tk._stats["graphics"])

print("=" * 78)
print("B  alternate idle: does the pair ever name a second, different group?")
print("=" * 78)
same = other = unset = 0
examples = []
seen = set()
for c in tk._civs:
    for u in c.get("units", ()):
        sg = u.get("standing_graphic")
        if not sg:
            continue
        a = idx.art(u)
        if not a or a.get("kind") != "loose":
            continue
        alt = a.get("alternate_idle")
        if not alt:
            unset += 1
            continue
        gid = sg[1]
        ag = idx.stem_of(gid)
        if ag == a.get("stem"):
            same += 1
        else:
            other += 1
            key = (u["id"], a.get("stem"), ag)
            if key not in seen and len(examples) < 12:
                seen.add(key)
                examples.append(key)
print("  alternate idle unset (-1)          : %d" % unset)
print("  set, SAME group as the standing art: %d" % same)
print("  set, a DIFFERENT group             : %d" % other)
for uid, st, ag in examples:
    print("    unit %-5d standing %-22r alternate %r" % (uid, st, ag))

print()
print("=" * 78)
print("A  zero-pair swaps: are they reachable, and are they refused?")
print("=" * 78)
arts = {}
for c in tk._civs:
    for u in c.get("units", ()):
        if u.get("id") in arts:
            continue
        a = idx.art(u)
        if a and a.get("kind") == "loose":
            arts[u["id"]] = a
print("  units with loose art: %d" % len(arts))

# how many DISTINCT art groups, and how many pairwise swaps are empty
groups = collections.defaultdict(list)
for uid, a in arts.items():
    groups[a["stem"]].append(uid)
print("  distinct art groups : %d" % len(groups))

# sample: for each of a handful of real targets, how many donors give 0 pairs
subjects = [4, 8, 74, 83, 93, 12, 498, 2550, 66, 594, 41, 448]
for uid in subjects:
    if uid not in arts:
        print("  unit %-5d (no loose art)" % uid)
        continue
    t = arts[uid]
    tt = set(t.get("tokens") or {})
    empty = []
    for did, d in arts.items():
        if did == uid:
            continue
        if not (tt & set(d.get("tokens") or {})):
            empty.append(did)
    try:
        pairs, unmapped, extra = S.plan_swap(t, arts[74])
        n74 = len(pairs)
    except S.SpriteError:
        n74 = "refused"
    print("  target %-5d tokens=%-2d  donors with ZERO overlap: %5d / %d  (vs unit 74 -> %s pairs)"
          % (uid, len(tt), len(empty), len(arts) - 1, n74))

print()
print("  does swap_files report the emptiness anywhere?")
for uid in (12,):
    t = arts[uid]
    for did in (498,):
        out, unpaired = S.swap_files(t, arts[did])
        print("    unit %d <- unit %d -> %d entries, unpaired=%s"
              % (uid, did, len(out), unpaired))
        print("    ^ a caller sees an EMPTY DICT, which reads as 'nothing to do',")
        print("      not as 'these two have no animation in common'.")
