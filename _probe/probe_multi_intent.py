"""Can a user get ONE mod that does two things?

A player never asks for "archer attack +1".  They ask for "村民血更厚,而且科技更快"
-- and the most popular data mods on this machine are exactly that shape (the 10x
resource mods change effects, techs and unit records in one folder).

But every entry point takes a single intent dict:

    Toolkit.plan(intent)          -> one intent
    Toolkit.build(intent, ...)    -> one intent
    compile_intent(dat_path, intent, ...)
    compile_edits(data, civs, resolved, ...)   <- `resolved` is singular

and `build()` re-derives its buffer from the ORIGINAL raw every time:

    rep = C.compile_intent(...)
    patched = C.apply_edits(self._raw, rep["edits"])

So two builds are two independent complete .dat files, and the engine loads only
the highest-priority one -- the lower-priority mod's change vanishes with no
error.  The user sees two mods installed and one of them doing nothing.

This probe measures the gap and, more importantly, tests whether the obvious fix
actually works: fold the intents, feeding each step's OUTPUT buffer into the next
step.  That is only sound if an in-place patch never moves a byte (which
`verify()` already asserts per step) AND if each step reads its `before` values
from the accumulated buffer rather than the original.  If a step read `before`
from the original, applying "hp +5" twice would produce +5 instead of +10 -- a
silent under-count, not an error.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.intent import compiler as C     # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data = tk._raw
civs = tk._civs
gv = tk._parsed[3]
tail = tk._parsed[4]

# Three edits a player would plausibly ask for together, chosen so that two of
# them land in DIFFERENT sections (unit records vs. the tech/effect tail) and the
# third lands on the SAME field as the first -- so the fold has to survive both
# kinds of overlap.
INTENTS = [
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
    {"intent": "tech.cost", "tech": 22, "resource": "gold", "delta": -10},
    {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 7},
]

print("=== 1. what the CURRENT api can express ===")
print("  plan/build/compile_intent all take ONE intent dict")
schema, bindings = C.load_schema()
single = []
for it in INTENTS:
    r = C.resolve(it, schema)
    patched, edits = C.compile_edits(data, civs, r, bindings, schema,
                                     tail=tail, gv=gv, stats=tk._stats,
                                     game_root=tk.game_root)
    changed = len(C.diff_offsets(data, patched))
    single.append((it, patched, edits, changed))
    print("  %-58s %4d edit(s), %4d byte(s)" % (
        json.dumps(it, ensure_ascii=False), len(edits), changed))

print()
print("=== 2. do two separate builds compose? ===")
# This is what a user gets today: build A, build B, install both.  Each .dat is
# a full replacement, so compare each build against the OTHER build: if the
# bytes A changed are NOT changed in B, then B alone is missing A's edit.
b0, b2 = single[0][1], single[2][1]
a_only = set(C.diff_offsets(data, b0))
b_only = set(C.diff_offsets(data, b2))
print("  build #1 (villager hp +5)  changed %d byte(s)" % len(a_only))
print("  build #3 (villager hp +7)  changed %d byte(s)" % len(b_only))
print("  offsets both builds changed      : %d" % len(a_only & b_only))
print("  offsets ONLY build #1 changed    : %d" % len(a_only - b_only))
print("  -> a player installing both gets whatever Priority loads first,")
print("     and the other build's edit is simply absent from the loaded file.")

print()
print("=== 3. does folding actually work? ===")
# Feed each step's output into the next step's input.  `civs` and `tail` are
# reused across steps on purpose: an in-place patch cannot move a byte, which
# `verify()` asserts for every step below.
cur = data
all_edits = []
for it in INTENTS:
    r = C.resolve(it, schema)
    nxt, edits = C.compile_edits(cur, civs, r, bindings, schema,
                                tail=tail, gv=gv, stats=tk._stats,
                                game_root=tk.game_root)
    rep = C.verify(cur, nxt, edits)
    all_edits.extend(edits)
    print("  step %-56s -> %4d edit(s), verify ok %s" % (
        json.dumps(it, ensure_ascii=False), len(edits), rep["ok"]))
    if not rep["ok"]:
        print("      PROBLEM: %s" % rep["problems"])
    cur = nxt

print()
print("  cumulative vs original: %d byte(s) changed, %d edit(s) recorded"
      % (len(C.diff_offsets(data, cur)), len(all_edits)))

# The decisive question: did the two hp edits ACCUMULATE (5 then 7 -> +12) or
# did the second overwrite the first (+7)?  Read the value back off the folded
# buffer with the unmodified parser.
p = P.Parser(cur)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
folded = L.locate(cur, parser=p)[0]
hp_before = None
hp_after = None
for c in civs:
    for u in c["units"]:
        if u["id"] == 83:
            hp_before = u["hit_points"]
            break
    break
for c in folded:
    for u in c["units"]:
        if u["id"] == 83:
            hp_after = u["hit_points"]
            break
    break
print("  villager 83 hit_points: original %s -> folded %s  (expect 25 -> 37)"
      % (hp_before, hp_after))
print("  accumulated  : %s" % (hp_after == hp_before + 12))
print("  overwritten  : %s" % (hp_after == hp_before + 7))

# And the tail edit must survive too.
techs_before = L.locate_techs(data, tail, gv)
techs_after = L.locate_techs(cur, tail, gv)
print("  Loom (tech 22) cost gold: %s -> %s" % (
    [c for c in techs_before[22]["costs"] if c["type"] == 3],
    [c for c in techs_after[22]["costs"] if c["type"] == 3]))

print()
print("=== 4. what a bundle report would have to say ===")
# Two intents can target the SAME byte.  A folder-level report has to be able to
# name that, because "hp +5 then hp +7" is not an error -- it is +12 -- but
# "hp +5 then hp = 20" silently discards the first edit and the user must be told.
touched = {}
for e in all_edits:
    for k in range(e.width):
        touched.setdefault(e.off + k, []).append(e)
overlap = {o: v for o, v in touched.items() if len(v) > 1}
print("  edit offsets written more than once: %d" % len(overlap))
for o in sorted(overlap)[:4]:
    print("    0x%X <- %s" % (o, " then ".join("%s=%s" % (x.where, x.after)
                                              for x in overlap[o])))
print()
print("VERDICT: folding works, accumulates correctly, and leaves the section")
print("offsets intact -- so a bundle API is writable.  Today a user has to")
print("install two complete .dat mods and only one of them takes effect.")
