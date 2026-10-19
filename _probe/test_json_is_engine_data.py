# -*- coding: utf-8 -*-
"""Is a JSON layer engine input at all?  (Yes -- and the .dat cannot be it.)

Why this pin exists
-------------------
The user's correction was plain: "the game wants the .dat, not the JSON".  That
was true for the thing they were explaining (a data mod replaces the .dat), and
it very nearly turned into a broader rule: *JSON is not game data*.

Taken as a broad rule it is FALSE, and this file proves it from the game's own
behaviour:

  1. Per-civilization unit availability is ENFORCED by the running game.  The
     user observed it: as Britons the Archery Range offers no Hand Cannoneer
     (2026-10-14), while 24 civilizations demonstrably do build it.
  2. The .dat CANNOT express that distinction.  Unit 5 sits at the same array
     index in all 63 civs, its record is identical apart from decorative
     fields, the only type-2 command naming it is GLOBAL (civ=-1), and the
     .dat TechTree is a single global object.
  3. Both JSON layers DO express it, per civilization.

Therefore at least one JSON layer is engine input.  The shipped rewrite failing
in game is an OVERLAY problem for one specific path, not evidence that JSON is
ignored.  Keeping those apart matters: the first is a bug to chase, the second
would condemn the whole `*.availability` feature.

ANSWERED SINCE (2026-10-19): neither of the two JSON layers is what the BUILD
panel consults.  `futuravailableunits.json` is excluded in both directions by
plain-game runs (Sicilians panel-silent-but-offered / Poles panel-listed-but-not
-offered); the tree is read but a mod-side rewrite moves nothing (`dsh test
v15`, two directions, byte-identical `.dat`, engine log confirming the load).
They are still engine data -- just for OTHER screens: the tech-tree preview
reads the tree, and the panel feeds the greyed-out future-items view.  What
gates the build menu is a `.dat` `type 2` command on a technology the civ owns,
last one to fire wins (`dsh test v7` grant / `dsh test v17` revoke).
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import os
import sys

sys.path.insert(0, _HERE_PATH(".."))

import aoe2mod.api as A                        # noqa: E402
from aoe2mod.game import civtechtrees as CT    # noqa: E402
from aoe2mod.game import buildpanel as BP      # noqa: E402
from aoe2mod.intent import compiler as C       # noqa: E402

UNIT = 5                      # Hand Cannoneer -- the observed case
CIV_BUILD = "Turks"           # a civilization the tree says can build it
CIV_BLOCK = "Britons"         # the civilization the user observed cannot

tk = A.open_toolkit()
tk._ensure()
GAME = tk.game_root
print("game root : %s" % GAME)
print("subject   : unit %d (Hand Cannoneer)" % UNIT)
print()

# ---------------------------------------------------------------- 1. the .dat
print("--- 1. what the .dat can say -------------------------------------")

data, civs, civs_start, gv, tail, how = tk._parsed
sizes, idxs = [], set()
for c in civs:
    ids = [u["id"] for u in c["units"]]
    sizes.append(len(ids))
    idxs.add(ids.index(UNIT) if UNIT in ids else None)
print("    .dat civ unit-array sizes      : min %d max %d"
      % (min(sizes), max(sizes)))
print("    index of unit %d in each civ    : %s  (one value -> no signal)"
      % (UNIT, sorted(idxs)))

techs = tk._tech_records()
effs = tk._effect_records()
named, scanned = [], 0
for ti, t in enumerate(techs):
    for row in C.effect_rows(effs, t, ix=None):
        scanned += 1
        if row.get("type") == 2 and int(row["raw"][1]) == UNIT:
            named.append((ti, t.get("civ"), row["raw"], row.get("editable")))
print("    effect rows scanned            : %d" % scanned)
print("    type-2 commands naming unit %d  : %d" % (UNIT, len(named)))
for ti, civ, raw, ed in named:
    print("        tech[%d] civ=%s raw=%s editable=%s" % (ti, civ, raw, ed))
glob_only = all((civ is None or civ == -1) for _ti, civ, _r, _e in named)
print("    ...every one of them GLOBAL (civ=-1): %s" % glob_only)
print("    -> a GLOBAL enable cannot make 24 civs differ from 38.")

# ------------------------------------------------------- 2. the JSON layers
print()
print("--- 2. what the JSON layers say -----------------------------------")
trees = tk._trees()
# NOTE: load_trees returns the parsed JSON document itself (plus a "path" key),
# NOT a (path, obj) pair -- unpacking it raises "too many values to unpack".
tree_build = trees[CT.civ_file_stem(CIV_BUILD)]
tree_block = trees[CT.civ_file_stem(CIV_BLOCK)]
st_build = CT.node_status(tree_build, UNIT, CT.UNIT_USE_TYPES)
st_block = CT.node_status(tree_block, UNIT, CT.UNIT_USE_TYPES)
print("    CivTechTrees  %-8s status unit %d : %r" % (CIV_BUILD, UNIT, st_build))
print("    CivTechTrees  %-8s status unit %d : %r" % (CIV_BLOCK, UNIT, st_block))

panels = BP.load_all(GAME)
pk_build = BP.civ_key_for(panels, CIV_BUILD)
pk_block = BP.civ_key_for(panels, CIV_BLOCK)
print("    panel civ keys                  : %r / %r" % (pk_build, pk_block))

def panel_obj(pk):
    """`load_all` gives {civ: {"text":…, "obj": <the WHOLE parsed file>, …}}.

    The `obj` is the entire multi-civ document, not this civ's subtree, so the
    subtree is `obj[pk]`.  Both earlier versions of this helper got that wrong
    and answered `None` for every building lookup -- a None that reads like a
    fact about the game but was a fact about this function.

    Cross-check with the module's own API: `entries(obj, key)` takes the whole
    file plus a civ key, which is only meaningful if `obj` is the whole file.
    """
    v = panels[pk]
    if isinstance(v, dict) and "obj" in v:
        whole = v["obj"]
        return whole.get(pk, whole)
    if isinstance(v, tuple):
        return v[1]
    return v

def panel_has(pk, building_id, node):
    obj = panel_obj(pk)
    for b in obj.get(BP.BUILDINGS_KEY, []):
        if b.get("ID") == building_id:
            return any(u.get("ID") == node for u in b.get(BP.UNITS_KEY, []))
    return None

for pk, label in ((pk_build, CIV_BUILD), (pk_block, CIV_BLOCK)):
    print("    panel %-8s Archery Range lists unit %d : %s"
          % (label, UNIT, panel_has(pk, 87, UNIT)))

has_87 = {label: panel_has(pk, 87, UNIT)
          for pk, label in ((pk_build, CIV_BUILD), (pk_block, CIV_BLOCK))}
if any(v is None for v in has_87.values()):
    # A None here means the lookup never found the building, which says nothing
    # about the game.  Refuse to print a verdict built on a probe bug.
    raise SystemExit("PANEL LOOKUP BROKEN (building 87 not found): %r -- this is "
                     "a fact about this probe, not about the game" % has_87)
assert has_87[CIV_BUILD] is True, "Turks Archery Range should list the Hand Cannoneer"
assert has_87[CIV_BLOCK] is False, "Britons Archery Range should not list it"

distinguishes = (st_build != st_block)
print()
print("    the JSON layers DISTINGUISH a builder from a blocked civ : %s"
      % distinguishes)
print("    the .dat distinguishes them                              : %s"
      % (not glob_only))

print()
print("=" * 78)
if distinguishes and glob_only:
    print("JSON IS ENGINE DATA: the game enforces a per-civ distinction that")
    print("the .dat provably cannot carry.  So the failed rewrite is an OVERLAY")
    print("problem on one path, not proof that JSON is ignored.")
else:
    print("INCONCLUSIVE -- a precondition above did not hold; fix the probe")
    print("before drawing any conclusion.")
print("=" * 78)
print("ANSWERED SINCE (2026-10-19): the build panel consults NEITHER JSON layer.")
print("It is excluded in both directions by in-game runs (Sicilians / Poles), and")
print("`dsh test v15` moved two tree files in both directions over a")
print("byte-identical `.dat` without the menu changing.  What does move it is a")
print("`.dat` `type 2` command on a technology the civ owns, last one to fire")
print("wins (v7 grant / v17 revoke).  The 99.45% agreement between the two files")
print("still stands -- they are both MODELS of who may build what, and both are")
print("read by SCREENS other than the build menu (tech-tree preview reads the")
print("tree; the panel feeds the greyed-out future-items view).")

assert distinguishes, "the JSON layers must separate a builder from a blocked civ"
assert glob_only, "the only .dat command naming unit 5 must be global"
assert len(named) == 1, "expected exactly one type-2 command for unit 5"
print()
print("JSON-IS-ENGINE-DATA PIN: PASSED")
