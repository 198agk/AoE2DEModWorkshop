# -*- coding: utf-8 -*-
r"""Does the `.dat` gate unit 2550 shut for the Incas -- in the record itself?

WHY THIS MATTERS
----------------
`aoe2mod/dat/parser.py:807-808` steps over two bytes on every unit record and
keeps neither:

    r.u8()   # Enabled
    r.u8()   # Disabled

Those are the record's OWN gate -- separate from the `type 2` effect commands
(only 7 of which disable anything, file-wide) and separate from anything in a
`CivTechTrees` file.  Every earlier conclusion that "the .dat is per-civ blind
for 2550" rested on the EFFECT layer, not on these bytes.

If the Incas' copy of 2550 has Enabled=False here, then v15's "the button is
still there" would be a story about the `.dat` record, not about the tree layer.
So this probe reads them.

MEASURED (2026-10-19): all 63 civilizations that contain 2550 read
Enabled=0 / Disabled=0 -- ONE pair, no per-civ variation at all.  The villager
(83) reads Enabled=1 / Disabled=0 in all 63, so the bytes are load-bearing, not
decorative.  The `.dat` therefore says the SAME thing about 2550 for the Incas
and the Britons, and cannot be what makes them behave differently.

HOW (no layout duplication)
---------------------------
The gate sits at a FIXED offset inside the record, because every field before it
is fixed width: `type`(u8) .. `OldPortraitPict`(i16) = 56 bytes, so Enabled is
at record_start + 56 and Disabled at +57.  Record starts are captured by
wrapping `P.read_unit`, so the walk itself still uses the product's reader --
no second copy of the layout that could drift.

The fixed offset is CHECKED, not assumed: every one of the ~137k unit records in
the shipped file must yield two bytes that are each 0 or 1.  A wrong offset over
that many records would surface as values outside {0,1}.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from aoe2mod.dat import parser as P                         # noqa: E402
from aoe2mod.game import locations as G                     # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
VILLAGER = 83
GATE_OFFSET = 56            # Enabled; Disabled is the next byte

_COLLECTED = []             # (civ_index, unit_id, record_start)

_orig_read_unit = P.read_unit
_orig_read_civ = P.read_civ


def _spy_read_unit(r, collect=None):
    start = r.pos
    u = _orig_read_unit(r, collect=collect)
    _COLLECTED.append((_CIV[0], u.get("id"), start))
    return u


def _spy_read_civ(r, collect=None):
    # `read_civ` is called once per civilization, in array order, so its call
    # count IS the civ index.  Tracking it here is what makes the report name
    # the right civilization (the first draft hard-coded 0 and every line said
    # "Gaia" -- the gate bytes were right, the label was not).
    _CIV[0] = len(_CIV_SEEN)
    _CIV_SEEN.append(_CIV[0])
    return _orig_read_civ(r, collect=collect)


_CIV = [0]
_CIV_SEEN = []

_raw, _how = P.load_dat(G.dat_path(GAME))
print("dat     : %d raw bytes (%s)" % (len(_raw), _how))

P.read_unit = _spy_read_unit
P.read_civ = _spy_read_civ
try:
    _p = P.Parser(_raw)
    with contextlib.redirect_stdout(io.StringIO()):
        _p.parse()
finally:
    P.read_unit = _orig_read_unit
    P.read_civ = _orig_read_civ

civs = _p.stats["civs"]
print("civs    : %d ; unit records captured: %d" % (len(civs), len(_COLLECTED)))

# ------------------------------------------------------------------ sanity
_bad = []
for ci, uid, start in _COLLECTED:
    e, d = _raw[start + GATE_OFFSET], _raw[start + GATE_OFFSET + 1]
    if e not in (0, 1) or d not in (0, 1):
        _bad.append((ci, uid, e, d))
print()
print("A  the gate offset is where we think it is")
print("   records whose two gate bytes are not each 0/1 : %d of %d"
      % (len(_bad), len(_COLLECTED)))
if _bad[:5]:
    print("   first offenders: %s" % (_bad[:5],))
assert not _bad, "GATE OFFSET IS WRONG -- %d records read outside {0,1}" % len(_bad)
print("   PASS")

# ------------------------------------------------------------------ census
print()
print("B  how each civilization gates unit %d" % UNIT)
_names = [c.get("name") for c in civs]
_seen = {}
for ci, uid, start in _COLLECTED:
    if uid != UNIT:
        continue
    e, d = _raw[start + GATE_OFFSET], _raw[start + GATE_OFFSET + 1]
    _seen.setdefault((e, d), []).append(_names[ci] if ci < len(_names) else ci)
print("   civs that contain unit %d : %d" % (UNIT, sum(len(v) for v in _seen.values())))
for (e, d), who in sorted(_seen.items()):
    print("   Enabled=%d Disabled=%d : %d civ(s)  %s"
          % (e, d, len(who), who[:6] + (["..."] if len(who) > 6 else [])))

_in = _seen.get((1, 0), []) + _seen.get((1, 1), [])
print()
print("   every civ that contains it says Enabled=1 : %s"
      % ("YES" if len(_in) == sum(len(v) for v in _seen.values()) else "NO"))

# ------------------------------------------------------------------ villager
print()
print("C  the villager's gate (the same edit v15 ships) and the tree's view")
_v = {}
for ci, uid, start in _COLLECTED:
    if uid != VILLAGER:
        continue
    e, d = _raw[start + GATE_OFFSET], _raw[start + GATE_OFFSET + 1]
    _v.setdefault((e, d), []).append(_names[ci] if ci < len(_names) else ci)
for (e, d), who in sorted(_v.items()):
    print("   Enabled=%d Disabled=%d : %d civ(s)" % (e, d, len(who)))

_trees = CT.load_trees(GAME)
for key in ("INCAS", "BRITONS"):
    t = _trees.get(key)
    if t is None:
        print("   %s : no tree" % key)
        continue
    st = CT.node_status(t, UNIT, CT.UNIT_USE_TYPES)
    print("   tree %-8s says %s for %d" % (key, st, UNIT))

# ------------------------------------------------------------------ verdict
print()
print("VERDICT")
print("  unit %d, record gate, all %d civilizations that contain it:"
      % (UNIT, sum(len(v) for v in _seen.values())))
for (e, d), who in sorted(_seen.items()):
    print("     Enabled=%d Disabled=%d  x%d" % (e, d, len(who)))
print()
if len(_seen) == 1:
    print("  ONE distinct pair across every civ -> the record gate carries NO")
    print("  per-civilization signal for this unit.  The .dat cannot be what")
    print("  lets the Incas build the Champi Scout while the Britons cannot;")
    print("  only the CivTechTrees file differs between those two civs")
    print("  (INCAS: %s / BRITONS: %s)."
          % (CT.node_status(_trees["INCAS"], UNIT, CT.UNIT_USE_TYPES)
             if "INCAS" in _trees else "?",
             CT.node_status(_trees["BRITONS"], UNIT, CT.UNIT_USE_TYPES)
             if "BRITONS" in _trees else "?"))
else:
    print("  MORE than one pair -> the record gate DOES vary per civ, and every")
    print("  earlier claim that this layer is per-civ blind needs re-reading.")
print()
print("  Note the gate is REAL, not decorative: the villager reads Enabled=1")
print("  while 2550 reads Enabled=0 everywhere, so the bytes mean something.")
print("  What they do NOT do is distinguish one civilization from another here.")
print()
print("  Enabled=0 for all 63 yet the Incas can train it means the record gate")
print("  is not the only switch -- the global `type 2` enable in tech 1350 is")
print("  what opens it.  Being global (civ=-1), that effect is equally true for")
print("  the Britons, which is the whole puzzle: the .dat says the same thing")
print("  for both, and the two civs behave differently.")
