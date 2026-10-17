"""★★★ Does the .dat's effect layer reproduce the rosters every player knows?

The user (m19924) says the game reads empires2_x2_p1.dat.  Two earlier attempts
to put the gate in the unit record were refuted:
  * membership in the civ's unit array  -> every tree row is present (3,115/3,115)
  * the per-civ record body             -> identical apart from the civ index and
                                           nested `_off_*` byte offsets (a probe bug:
                                           I filtered `_` only at the TOP level, so
                                           nested offsets made identical records look
                                           different in 43/43 pairs)

What DID reproduce real rosters is the effect layer: tech[263] is owned by British
and enables unit 8 (Longbowman); tech[16]/[446] are owned by Goths and enable unit
41 (Huskarl).  That is exactly AoE2 as players know it.

So test it properly, on facts that cannot be wrong, and be explicit about the
prediction being made:

    unit is available to civ C  <=>  C owns a type-2 enable for the unit
                                 OR (a GLOBAL enable exists AND C owns no disable)
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, tail, _how = tk._parsed
techs = L.locate_techs(data, tail, gv)
effects, _ = L.locate_effects(data)
names = [c["name"] for c in civs]

own_enable = defaultdict(set)     # unit -> {civ}
own_disable = defaultdict(set)
glob_enable = defaultdict(int)
glob_disable = defaultdict(int)

for t in techs:
    owner = t.get("civ", -1)
    for r in C.effect_rows(effects, t, fanout=None, ix=None):
        if r["type"] != 2:
            continue
        _ty, unit, b = r["raw"][0], r["raw"][1], r["raw"][2]
        if b not in (0, 1):
            continue
        civ_name = names[owner] if 0 <= owner < len(names) else None
        if b == 1:
            (own_enable if civ_name else glob_enable)[unit].add(civ_name) \
                if civ_name else glob_enable.__setitem__(unit, glob_enable[unit] + 1)
        else:
            if civ_name:
                own_disable[unit].add(civ_name)
            else:
                glob_disable[unit] = glob_disable[unit] + 1

def available(unit, civ):
    if civ in own_disable.get(unit, ()):
        return False
    if civ in own_enable.get(unit, ()):
        return True
    return glob_enable.get(unit, 0) > 0

# Facts no AoE2 player would dispute, and that need no JSON to observe.
UNIQUE = [(8, "Longbowman", "British"), (41, "Huskarl", "Goths"),
          (755, "Tarkan", "Huns"), (692, "Berserk", "Vikings"),
          (725, "Jaguar Warrior", "Aztecs"), (291, "Samurai", "Japanese"),
          (46, "War Elephant", "Persians"), (282, "Mameluke", "Saracens"),
          (40, "Cataphract", "Byzantine"), (25, "Teutonic Knight", "Teutons"),
          (73, "Chu Ko Nu", "Chinese"), (281, "Throwing Axeman", "French")]
BASE = [(83, "Villager"), (4, "Archer"), (74, "Militia"), (13, "Fishing Ship")]

print("=== unique units: enabled ONLY for their own civilization ===")
ok = bad = 0
for uid, label, owner in UNIQUE:
    en = sorted(own_enable.get(uid, ()))
    g = glob_enable.get(uid, 0)
    others = [c for c in en if c != owner]
    verdict = "OK" if (owner in en and not others) else "??"
    if verdict == "OK":
        ok += 1
    else:
        bad += 1
    print("  %-4d %-18s owner=%-12s civ-owned enable=%-22s global=%d  %s"
          % (uid, label, owner, str(en)[:22], g, verdict))
print("  -> %d of %d match the known owner exactly" % (ok, ok + bad))
print()

print("=== base units: available to everyone ===")
for uid, label in BASE:
    civs_with = [c for c in names[:8] if available(uid, c)]
    print("  %-4d %-14s available to first 8 civs: %d/8  global_enable=%d"
          % (uid, label, len(civs_with), glob_enable.get(uid, 0)))
print()

# Complement: a unit the .dat says is global -- who does it say is blocked?
print("=== Hand Cannoneer (5): the global-enable unit ===")
blk = sorted(own_disable.get(5, ()))
print("  global enable count: %d" % glob_enable.get(5, 0))
print("  civs with a civ-owned DISABLE: %d  %s" % (len(blk), blk[:20]))
n_avail = sum(1 for c in names if available(5, c))
print("  civs the model says CAN build it: %d of %d" % (n_avail, len(names)))
