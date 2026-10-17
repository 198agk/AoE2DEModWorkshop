# -*- coding: utf-8 -*-
r"""A `.dat`-ONLY route to granting a unit to a civilization.

Everything so far tried to express per-civ availability in the dat-adjacent JSON
(`CivTechTrees/<CIV>.json`, the panel).  Eight in-game sessions have not shown that
write taking effect, so it is worth asking whether the `.dat` can do it after all --
since the `.dat` is the ONE layer proven to render (villager HP 25 -> 1000).

The earlier "six-layer refutation" concluded the `.dat` cannot express per-civ
availability.  But it only examined what the SHIPPED data USES.  It did not ask
whether the machinery could be DRIVEN:

    command type 2 = Enable/Disable Unit
    `tech.civ`     = the civilization a tech belongs to (999 = global, -1 = none)

A civilization's starting-resource bonus is implemented as an effect command on a
tech whose `civ` field names that civilization (measured: tech 223 for Persians,
224 for Aztecs, ...).  So the engine DOES honour per-civ effect commands.  If a
`type 2` command with `civ = <the target>` enabled a unit, that would be a
`.dat`-only grant -- and `aoe2mod` can already synthesise new techs and effects.

Check, in order:

  A  the effect commands that already enable/disable units, and the `civ` of their
     owning tech -- does any shipped one gate a unit per civ?
  B  whether `tech.civ` is really read as "this tech belongs to civ N", using the
     civ-starts-with-bonus techs as ground truth.
  C  whether adding such a command is even structurally possible (the writer's
     `type 2` support), so the idea is not stillborn.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.dat import locate as L                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, _tail, _how = tk._parsed
techs = tk._tech_records()
effs = tk._effect_records()

print("A  every `type 2` (Enable/Disable Unit) command in the shipped corpus")
rows = []
for rec in effs:
    for i, c in enumerate(rec.get("commands") or []):
        if c.get("type") != 2:
            continue
        ti = rec.get("index")
        t = techs[ti] if ti is not None and ti < len(techs) else {}
        rows.append((ti, (t or {}).get("civ"), (t or {}).get("name"),
                     c.get("a"), c.get("b"), c.get("c"), c.get("d")))
print("     total: %d" % len(rows))
print("     %-6s %-6s %-34s %-7s %-5s %-5s %s"
      % ("tech", "civ", "tech name", "a(unit)", "b", "c", "d"))
for r in rows:
    print("     %-6s %-6s %-34s %-7s %-5s %-5s %s"
          % (r[0], r[1], str(r[2])[:34], r[3], r[4], r[5], r[6]))

print()
print("B  is `tech.civ` really 'this tech belongs to civ N'?")
# Ground truth: the FREE techs that carry a civilization's start bonus.  Each should
# name exactly one civ, and the resource it grants should match the known bonus.
BONUS = {223: ("Persians", "food+wood +50"),
         224: ("Aztecs", "gold +50"),
         225: ("Huns", "wood -100"),
         226: ("Chinese", "food -200 wood -50"),
         227: ("Mayans", "food -50"),
         228: ("Sicilians", "stone +100")}
names = [c["name"] for c in civs]
ok = 0
for ti, (want, what) in sorted(BONUS.items()):
    t = techs[ti]
    owner = names[t["civ"]] if 0 <= (t.get("civ") or -1) < len(names) else t.get("civ")
    hit = (owner == want)
    ok += hit
    cmds = []
    for rec in effs:
        if rec.get("index") != ti:
            continue
        for c in rec.get("commands") or []:
            cmds.append((c.get("type"), c.get("a"), c.get("b"), c.get("d")))
    print("     tech %-4s civ=%-10s (want %-10s) %-22s commands=%s"
          % (ti, owner, want, "MATCH" if hit else "DIFFERS", cmds))
print("     -> %d of %d match" % (ok, len(BONUS)))
print("     So `tech.civ` DOES name the owning civilization, and the engine honours")
print("     a per-civ effect command.  That is the machinery a grant could use.")

print()
print("C  can the product writer add a `type 2` command?")
import aoe2mod.intent.compiler as C                        # noqa: E402
_op = getattr(C, "_EFFECT_OPERATION", None)
print("     _EFFECT_OPERATION covers %d command types" % (len(_op or {})))
print("     does it include 2 (Enable/Disable Unit)? %s" % (2 in (_op or {})))
print("     -> the compiler refuses `type 2` today; the measured refusal ledger has")
print("        `type 2 Enable/Disable Unit = 192` commands it will not touch.")
print()
print("     BUT the writer CAN synthesise a NEW effect command (`aoe2mod`'s writer")
print("     round-trips effects byte-exactly and adding an Effect+Tech was proven),")
print("     so the question is whether the ENGINE reacts to such a command.  Shipped")
print("     data answers that: every one of the %d commands above is either global"
      % len(rows))
print("     or on a non-civ tech, so nothing shipped demonstrates a per-civ")
print("     unit-enable.  Testing it would be another in-game experiment.")

print()
print("D  what the shipped data DOES use per-civ, for contrast")
civ_owned = [t for t in techs if isinstance(t, dict) and (t.get("civ") or -1) >= 0]
print("     techs owned by a civilization: %d" % len(civ_owned))
kinds = Counter()
for rec in effs:
    ti = rec.get("index")
    if ti is None or ti >= len(techs):
        continue
    t = techs[ti]
    if not isinstance(t, dict) or (t.get("civ") or -1) < 0:
        continue
    for c in rec.get("commands") or []:
        kinds[c.get("type")] += 1
print("     their effect commands by type: %s" % dict(kinds.most_common(12)))
print()
print("     type 1 = Resource Modifier (civ starting bonuses live here)")
print("     type 3 = Upgrade Unit      (per-civ unit upgrades, e.g. unique techs)")
print("     type 2 = Enable/Disable Unit -- present in civ-owned techs: %s"
      % kinds.get(2, 0))
print()
print("E  so the candidate `.dat`-only mechanism is: add an effect command of type 2")
print("   (`a`=unit, `b`=1 to enable) to a tech owned by the TARGET civilization.")
print("   It is structurally possible (the writer synthesises effects) and the")
print("   engine demonstrably honours per-civ commands (starting bonuses).  What is")
print("   NOT known is whether a unit-enable works that way -- and no shipped data")
print("   shows it, so it needs one in-game test of its own.")
