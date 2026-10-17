# -*- coding: utf-8 -*-
"""Shape of the effect command types `tech.effect` still refuses.

The resource-modifier family (1/6) was just wired up.  Before wiring another
family, measure each one the same way: what do its four slots actually hold,
and would a user recognise the thing being edited?

Refused families left, by count (from probe_effect_type_gap.py, rerun below):
    type 3    Upgrade Unit               424
    type 102  Disable Tech               269
    type 2    Enable/Disable Unit        192
    type 101  Tech Cost Modifier         175
    type 0    Attribute Modifier (Set)   124   <- in the table; refused for a
    type 4/5  Attribute Modifier          36      DIFFERENT reason (unnamed attr)
    type 103  Tech Time Modifier          71
    type 8    Modify Tech                 52
    type 7    Spawn Unit                   35
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.dat import locate as L                         # noqa: E402
from aoe2mod.intent import compiler as C                    # noqa: E402

tk = A.open_toolkit()
tk._ensure()
raw = tk._raw
tail, gv = tk._parsed[4], tk._parsed[3]

techs = L.locate_techs(raw, tail, gv)
effects, effects_start = L.locate_effects(raw)

UNIT_IDS = set()
for _c in tk._civs:
    for _u in (_c.get("units") or ()):
        UNIT_IDS.add(_u.get("id"))

# the interesting ones: the "what can this civ build / research" family, plus
# the tech-modifier family, plus Upgrade Unit
WATCH = [2, 102, 8, 18, 3, 101, 103, 7, 0, 4, 5]

# one pass over every command of every tech
shapes = collections.defaultdict(list)          # type -> list of (tech_ix, cmd_ix, cmds)
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        continue
    for ci, c in enumerate(effects[eid].get("commands") or ()):
        ty = c.get("type")
        if ty in WATCH:
            shapes[ty].append((ti, ci, t, c))

print("effect commands across %d techs : %d" % (len(techs), sum(
    len(effects[t.get("effect_id")].get("commands") or ())
    for t in techs if t.get("effect_id") is not None
    and 0 <= t.get("effect_id") < len(effects))))

by_tech = collections.defaultdict(set)
for ti, t in enumerate(techs):
    eid = t.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        continue
    for ci, c in enumerate(effects[eid].get("commands") or ()):
        if c.get("type") in WATCH:
            by_tech[ti].add(c.get("type"))
print("techs touched by a watched family : %d" % len(by_tech))

# how many techs have NO editable command today -- the population a new family
# would unlock.  editable is decided by effect_rows, so ask it directly.
# NOTE: effect_rows' `ix` is the SEMANTIC index (it does ix.get("unit", a)),
# not a tech index -- passing the tech index raises AttributeError.  The other
# probes pass None; that only costs target_label, which is not read here.
no_edit = 0
for ti, t in enumerate(techs):
    rows = C.effect_rows(effects, t, ix=None)
    if not any(r.get("editable") for r in rows):
        no_edit += 1
print("techs with no editable command today : %d of %d" % (no_edit, len(techs)))

for ty in WATCH:
    items = shapes.get(ty, ())
    if not items:
        continue
    label = (items[0][3].get("_type_label") or "")
    print("")
    print("=== type %d  (%d commands, %d techs) ===" % (
        ty, len(items), len({x[0] for x in items})))
    for slot in ("a", "b", "c", "d"):
        vals = collections.Counter(x[3].get(slot) for x in items)
        common = vals.most_common(6)
        print("   %s: distinct %-5d top %s" % (slot, len(vals), common))
    # does slot D resolve to a real unit / tech id?
    us = {x[3].get("d") for x in items}
    units = {x[3].get("d") for x in items
             if isinstance(x[3].get("d"), int) and x[3].get("d") in UNIT_IDS}
    print("   slot d hits a unit id: %d of %d distinct d values" % (len(units), len(us)))
    ti, ci, t, c = items[0]
    print("   sample tech[%d] %s cmd %d -> a=%r b=%r c=%r d=%r"
          % (ti, (t.get("name") or "")[:38], ci,
             c.get("a"), c.get("b"), c.get("c"), c.get("d")))
    # who owns it
    civs = collections.Counter(t.get("civ") for _, _, t, _ in items)
    print("   owner civ field: %s" % civs.most_common(5))
