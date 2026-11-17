# -*- coding: utf-8 -*-
r"""Find an EXISTING British-owned tech whose effect can be repurposed IN PLACE.

Why: `write_tech` for a `_new` record hardcodes the unmodeled scaffolding
(`aoe2mod/dat/writer.py:739`: `w.i16(0); w.i16(0); w.u8(0)` for the three
`ResearchResourceCost` slots), so an appended tech gets `costs[].type = 0` where every
shipped 'make avail' tech has **-1**.  The dict I hand the model cannot override it.

An IN-PLACE edit avoids that entirely: it reuses a shipped record's exact bytes and
changes only the fields the model carries.  In-place edits are also the path already
proven to work (“攻击力 +2 → 恰好 126 字节改变”, villager HP 25→1000).

So look for a civilization-owned (civ == 1, British) tech that:
  * is NOT referenced by any tree row anyone needs (so repurposing is harmless), and
  * has an effect whose command list I can rewrite to `(2, unit, 1, -1, 0.0)`.

Prefer a tech whose effect currently has exactly one command, and whose own
`research_locations` already look like the 'make avail' pattern.
"""
import os
import _gamepaths as GP
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
CIV = 1                       # British
UNIT = 2550

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
civs = tk._parsed[1]
names = [c["name"] for c in civs]
techs = tk._tech_records()
effs = {rec.get("index"): rec for rec in tk._effect_records()}
trees = CT.load_trees(GAME)

print("A  candidate techs: civ == %d (%s)" % (CIV, names[CIV]))
cands = []
for ti, t in enumerate(techs):
    if not isinstance(t, dict) or t.get("civ") != CIV:
        continue
    rec = effs.get(t.get("effect_id"))
    cmds = (rec or {}).get("commands") or []
    cands.append((ti, t, cmds))
print("     civ-owned techs for %s: %d" % (names[CIV], len(cands)))
for ti, t, cmds in cands[:40]:
    print("     tech %-5s effect=%-5s locs=%-28s cmds=%d %s"
          % (ti, t.get("effect_id"), str(t.get("research_locations"))[:28],
             len(cmds), [c.get("type") for c in cmds][:6]))

print()
print("B  which of them are referenced by the British tree (avoid those)")
brit = trees["BRITONS"]
in_tree = set()
for r in CT.rows_of(brit):
    if r.get("Use Type") == "Tech" and r.get("Node ID") is not None:
        in_tree.add(r.get("Node ID"))
print("     British tree Tech rows: %d" % len(in_tree))
free = [(ti, t, cmds) for ti, t, cmds in cands if ti not in in_tree]
print("     civ-owned techs NOT in the British tree: %d" % len(free))
for ti, t, cmds in free[:30]:
    print("     tech %-5s name=%-34s effect=%-5s cmds=%s"
          % (ti, str(t.get("name"))[:34], t.get("effect_id"),
             [(c.get("type"), c.get("a"), c.get("b")) for c in cmds][:4]))

print()
print("C  the best targets: a free tech whose effect has ONE command")
one = [(ti, t, cmds) for ti, t, cmds in free if len(cmds) == 1]
print("     count: %d" % len(one))
for ti, t, cmds in one[:20]:
    c = cmds[0]
    print("     tech %-5s %-38s effect %-5s cmd=(%s, a=%s, b=%s, c=%s, d=%s)"
          % (ti, str(t.get("name"))[:38], t.get("effect_id"), c.get("type"),
             c.get("a"), c.get("b"), c.get("c"), c.get("d")))

print()
print("D  and a 'make avail' tech for British specifically would be ideal --")
print("   is there one already? (civ 1 with a type-2 command)")
for ti, t, cmds in cands:
    if any(c.get("type") == 2 for c in cmds):
        print("     tech %-5s %-38s cmds=%s"
              % (ti, str(t.get("name"))[:38],
                 [(c.get("type"), c.get("a"), c.get("b")) for c in cmds]))
