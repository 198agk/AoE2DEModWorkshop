# -*- coding: utf-8 -*-
r"""smoke8: grant a unit to the British by editing THEIR OWN shipped 'make avail' tech.

## Why this beats smoke7

smoke7 APPENDED a new civ-owned tech.  `aoe2mod/dat/writer.py:739` hardcodes the
unmodeled scaffolding for a `_new` tech (`w.i16(0); w.i16(0); w.u8(0)` for the three
`ResearchResourceCost` slots), so an appended tech gets `costs[].type = 0` where every
shipped 'make avail' tech has **-1** -- a deviation I could not remove from the model.

smoke8 does an **in-place** edit instead, on a record the game already ships:

    tech 263  civ 1 (British)  'Longbow (make avail)'
    effect 251  commands = [(type 2, a=8, b=1, c=-1, d=0.0)]

`a=8` is the Longbowman -- and unit 8's `EnablingResearch` is exactly tech 263, owned
by exactly the British, the only civilization that can build Longbowmen.  So this is a
per-civ unit gate the engine demonstrably honours.

## The design, and why it is the strongest one yet

    1  keep the shipped command, ADD one:  (2, 2550, 1)   -> Champi Scout available
    2  CONTROL A: villager hit_points -> 1000             (proven to render)
    3  CONTROL B: the Longbowman must STILL appear in the British CASTLE

Control B is what makes this decisive.  It shares the very effect being edited, so:

    Longbowman still there + Champi Scout appears -> type-2 grants an ADDED unit
    Longbowman still there + no Champi Scout      -> the effect is read, and type 2
                                                     does NOT grant a new unit this way
    Longbowman GONE                               -> something else broke; unreadable

No JSON at all.  One `.dat`.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.writer as W                             # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_smoke8")
TITLE = "aoe2mod Smoke8 Inplace Avail"
TECH = 263                    # British '(Longbow) make avail'
EFFECT = 251
UNIT = 2550                   # Champi Scout
LONGBOW = 8

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]

print("A  the target is real and is the pattern we want")
techs0 = L.locate_techs(data, tail, gv)
effs0 = L.locate_effects(data)[0]
t0 = techs0[TECH]
e0 = next(r for r in effs0 if r.get("index") == EFFECT)
print("     tech %d: civ=%s (%s) name=%r effect_id=%s"
      % (TECH, t0.get("civ"), names[t0.get("civ")], t0.get("name"),
         t0.get("effect_id")))
print("     effect %d commands: %s" % (EFFECT, e0.get("commands")))
print("     costs: %s" % [{k: v for k, v in c.items() if not k.startswith("_")}
                          for c in (t0.get("costs") or [])])
print("     research_locations: %s"
      % [{k: v for k, v in l.items() if not k.startswith("_")}
         for l in (t0.get("research_locations") or [])])
assert t0.get("civ") == 1, "the tech must belong to the British"
assert [c.get("a") for c in e0.get("commands") or []] == [LONGBOW], \
    "effect 251 must be the single Longbowman enable"

print()
print("B  parse, then make the edit the writer can actually do safely")
with contextlib.redirect_stdout(io.StringIO()):
    p = P.Parser(data)
    try:
        p.parse()
    except SystemExit:
        pass
stats = p.stats

# THREE candidate edits were measured before choosing:
#   1. ADD a command to the existing effect 251   -> writer delta +3,061,463 and
#      34,740 model-vs-raw mismatches, then the re-parse died with
#      `struct.error: bad char in struct format`.  An in-place LENGTH change breaks
#      the verbatim replay, so that route is out.
#   2. APPEND a new TECH and give it the command  -> works, but `write_tech`'s `_new`
#      branch hardcodes the three `ResearchResourceCost` slots as zero, so the tech
#      gets `costs[].type = 0` where every shipped 'make avail' tech has -1.
#   3. APPEND a new EFFECT and repoint an existing civ-owned tech's `effect_id` at it
#      -> delta +40, 2 mismatches (the effect count and that one i16), clean re-parse.
#      Option 3 keeps the shipped tech's bytes (so no scaffolding is synthesised) and
#      keeps the shipped effect intact.
new_effect = {
    "name": "SMOKE8 Longbow + Champi Scout",
    # the SHIPPED command first (unit 8, the Longbowman), then the grant
    "commands": [(2, LONGBOW, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)],
    "_new": True,
}
stats["effects"].append(new_effect)
stats["effect_count"] = len(stats["effects"])
new_idx = len(stats["effects"]) - 1
old_idx = stats["techs"][TECH]["effect_id"]
stats["techs"][TECH]["effect_id"] = new_idx
print("     appended effect %d = %r" % (new_idx, new_effect["name"]))
print("     tech %d (%r) effect_id: %s -> %s"
      % (TECH, stats["techs"][TECH].get("name"), old_idx, new_idx))
print("     effect %d (the shipped Longbow enable) is left untouched" % old_idx)

print()
print("C  CONTROL A, in the same file: villager hit points -> 1000")
_changed = 0
for c in stats["civs"]:
    for u in c.get("units") or []:
        if u.get("id") == 83 and u.get("hit_points") != 1000:
            u["hit_points"] = 1000
            _changed += 1
print("     villager records set to 1000: %d" % _changed)
assert _changed, "the control must be present or a negative result is unreadable"

print()
print("D  serialise and re-parse with the UNMODIFIED parser")
out, rep = W.serialize_dat(stats, raw=data, gv=gv)
print("     raw bytes: %d (base %d, delta %+d)"
      % (len(out), len(data), len(out) - len(data)))
print("     model!=raw: %s group(s)" % rep.get("model_vs_original_mismatches"))
with contextlib.redirect_stdout(io.StringIO()):
    p2 = P.Parser(out)
    p2.parse()
print("     consumed %d of %d; clean EOF: %s"
      % (p2.r.pos, len(out), p2.r.pos == len(out)))
assert p2.r.pos == len(out), "the written .dat must parse to exactly its own length"
# and prove the edit through the SAME reader the product uses
_c2, _cs2, _gv2, tail2 = L.locate(out, parser=p2)
techs2 = L.locate_techs(out, tail2, _gv2)
e2 = next(r for r in L.locate_effects(out)[0] if r.get("index") == new_idx)
print("     tech %d now points at effect %s" % (TECH, techs2[TECH].get("effect_id")))
print("     that effect's commands: %s"
      % [(c.get("type"), c.get("a"), c.get("b")) for c in e2.get("commands")])
assert techs2[TECH].get("effect_id") == new_idx
_units = [c.get("a") for c in e2.get("commands")]
assert LONGBOW in _units and UNIT in _units, "both commands must survive"

print()
print("E  emit: ONE .dat, no JSON")
info = E.make_info(TITLE, author="aoe2mod",
                   description="SMOKE8: British's own 'make avail' tech also grants "
                               "unit %d; villager hp 1000 as control" % UNIT)
man = E.emit_data_mod(OUT, out, info, base_dir=GAME, overwrite=True)
for root, _d, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("     %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))
print("     changes_dat=%s" % man.get("changes_dat"))

print()
print("SMOKE8 READY: %s" % OUT)
print("  CONTROL A : a villager's hit points read 1000")
print("  CONTROL B : the British CASTLE still offers the 长弓兵 (Longbowman)")
print("  TEST      : the British BARRACKS, DARK AGE -> is there a 蔷琵侦察兵?")
