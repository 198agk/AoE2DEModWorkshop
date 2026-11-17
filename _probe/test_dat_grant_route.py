# -*- coding: utf-8 -*-
r"""PIN: the `.dat`-ONLY route to granting a unit -- and it is already in use.

Eight in-game sessions have not shown the JSON availability write taking effect, so
the `.dat` matters more than ever: it is the ONE layer proven to render (villager
HP 25 -> 1000).  An earlier round concluded the `.dat` cannot express per-civ
availability.  That conclusion examined what the shipped data USES for the units it
tested.  This probe asks a different question -- whether the machinery exists -- and
the answer is yes, and it is already used:

    tech 1363  civ 57 (Muisca)  'Guecha Warrior (make avail)'   type 2, a=2562, b=1
    tech 1375  civ 58 (Mapuche) 'Kona (make avail)'             type 2, a=2566, b=1
    tech 1377  civ 58           'Bolas Rider (make avail)'      type 2, a=2569, b=1
    tech 1388  civ 59 (Tupi)    'Blackwood Archer (make avail)' type 2, a=2579, b=1
    tech 1390  civ 59           'Ibirapema Warrior (make avail)'type 2, a=2582, b=1
    tech 1400  civ 57           'Temple Guard (make avail)'     type 2, a=2586, b=1
    tech 1471/1481  civ 61/62   'Jarl' / 'Jomsviking (make avail)'            b=1

**command type 2 with `a`=unit and `b`=1 is exactly "make this unit available", and
the owning tech's `civ` field names the civilization.**  108 such commands sit on
civ-owned techs.  So `tech.civ` + a type-2 command IS a per-civ unit enable, in
shipped data, for the modern regional units.

That makes a `.dat`-only grant structurally plausible:
  * add/find a tech owned by the TARGET civilization,
  * give it an effect with command `type 2, a=<unit>, b=1`.

Ground truth for `tech.civ` (5 of 6 civ starting-bonus techs match the civ by name)
and the writer's proven ability to synthesise Effects/Techs make this worth stating
precisely.  What is NOT known is whether the engine accepts an ADDED one -- no
shipped data adds to an existing civ -- so it needs its own in-game test.

Run:  python _probe\test_dat_grant_route.py
"""
import os
import _gamepaths as GP
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.intent.compiler as C                        # noqa: E402

GAME = GP.GAME
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
_civs = tk._parsed[1]
names = [c["name"] for c in _civs]
techs = tk._tech_records()
effs = tk._effect_records()

# index the effects by tech
by_tech = {}
for rec in effs:
    by_tech.setdefault(rec.get("index"), []).extend(rec.get("commands") or [])

print("A  'make avail' techs: type 2 with a unit in `a` and b=1")
avails = []
for ti, cmds in sorted(by_tech.items(), key=lambda kv: (kv[0] is None, kv[0])):
    if ti is None or ti >= len(techs):
        continue
    t = techs[ti]
    if not isinstance(t, dict):
        continue
    for c in cmds:
        if c.get("type") == 2 and c.get("b") == 1 and (c.get("a") or -1) > 0:
            avails.append((ti, t.get("civ"), t.get("name"), c.get("a")))
print("     total unit-enable commands (type 2, b=1): %d" % len(avails))
for ti, civ, nm, u in avails:
    owner = names[civ] if isinstance(civ, int) and 0 <= civ < len(names) else civ
    print("        tech %-5s civ=%-6s %-34s unit a=%s" % (ti, owner, str(nm)[:34], u))

print()
print("B  how many of those sit on a CIV-OWNED tech?")
civ_owned = [a for a in avails if isinstance(a[1], int) and a[1] >= 0]
check("some unit-enable commands belong to a specific civilization",
      len(civ_owned) > 0, "civ-owned=%d of %d" % (len(civ_owned), len(avails)))
print("     civ-owned: %d of %d" % (len(civ_owned), len(avails)))
print("     => `tech.civ` + a type-2 command is a PER-CIV unit enable, in shipped")
print("        data.  The earlier 'the .dat cannot do it' conclusion was about the")
print("        units it tested, not about the machinery.")

print()
print("C  ground truth that `tech.civ` names the owning civilization")
BONUS = {223: "Persians", 224: "Aztecs", 225: "Huns",
         226: "Chinese", 227: "Mayans", 228: "Sicilians"}
matched = 0
for ti, want in sorted(BONUS.items()):
    t = techs[ti]
    owner = (names[t["civ"]] if isinstance(t.get("civ"), int)
             and 0 <= t["civ"] < len(names) else t.get("civ"))
    hit = (owner == want)
    matched += hit
    print("     tech %-4s civ=%-12s want=%-12s %s"
          % (ti, owner, want, "MATCH" if hit else "DIFFERS"))
check("at least 5 of 6 civ-bonus techs name their civ", matched >= 5,
      "matched=%d" % matched)
print("     (Mayans differs on spelling only: dat 'Mayan' vs display 'Mayans')")

print()
print("D  what the product can and cannot do today")
_op = getattr(C, "_EFFECT_OPERATION", None) or {}
print("     _EFFECT_OPERATION (the command types the compiler will edit): %d"
      % len(_op))
check("the compiler does NOT edit type 2 today", 2 not in _op)
print("     -> so `unit.availability` cannot express this yet; the refusal ledger")
print("        counts `type 2 Enable/Disable Unit = 192` commands it declines.")
print("     BUT the writer round-trips effects byte-exactly and adding an")
print("     Effect+Tech was proven, so ADDING such a command is a writer question,")
print("     not a format question.")

print()
print("E  the honest boundary")
print("     what this proves: the MACHINERY (`tech.civ` + type-2 b=1) is real and")
print("       already used for regional units in shipped data; the writer can")
print("       synthesise effects/techs.")
print("     what WAS not proven then, and is now: that the engine honours an ADDED")
print("       such command for a civilization that did not ship one.  `dsh test v7`")
print("       (2026-10-16) added exactly that -- a new `type 2` b=1 effect on")
print("       British `tech 383`, whose RequiredTechs are empty -- and the Dark Age")
print("       Barracks offered the Champi Scout.  `dsh test v17` (2026-10-19) did")
print("       the mirror: b=0 on a Castle-age carrier removed it again, and showed")
print("       that when two commands touch one unit the LAST TO FIRE wins.")
print()
print("DAT GRANT ROUTE: command type 2 with b=1, on a tech whose `civ` is the")
print("  target civilization, is a per-civ unit enable the game already uses.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
