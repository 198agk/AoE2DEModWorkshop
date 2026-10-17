# -*- coding: utf-8 -*-
"""What does art() really return, and what does a 0-pair swap look like from
the caller's side?  (My last probe read a key that does not exist.)"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
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

def rec(uid, ci=1):
    for u in tk._civs[ci]["units"]:
        if u["id"] == uid:
            return u

for uid, label in ((4, "Archer"), (12, "Barracks dark"), (498, "Barracks feudal"),
                   (83, "Villager"), (2550, "Champi Scout")):
    a = idx.art(rec(uid))
    print("%-16s kind=%-6s stem=%-24r" % (label, a.get("kind"), a.get("stem")))
    print("    file     = %r" % a.get("file"))
    print("    tokens   = %s" % (a.get("tokens"),))
    print("    group    = %s" % (a.get("files"),))
    print("    alt idle = %r" % a.get("alternate_idle"))

print()
print("0-pair swap, from the caller's side:")
t, d = idx.art(rec(12)), idx.art(rec(498))
pairs, unmapped, extra = S.plan_swap(t, d)
print("  pairs=%s" % pairs)
print("  unmapped=%s" % unmapped)
print("  extra=%s" % extra)
out, unpaired = S.swap_files(t, d)
print("  swap_files -> %d entries %s" % (len(out), out))

print()
print("real swap:")
t, d = idx.art(rec(4)), idx.art(rec(8))
pairs, unmapped, extra = S.plan_swap(t, d)
print("  pairs:")
for a, b in pairs:
    print("    %-34s <- %s" % (a, b))
print("  unmapped=%s extra=%s" % (unmapped, extra))
out, unpaired = S.swap_files(t, d, GAME)
print("  swap_files with disk check -> %d entries" % len(out))
for k, v in sorted(out.items()):
    print("    %-64s <- %s" % (k, v))
