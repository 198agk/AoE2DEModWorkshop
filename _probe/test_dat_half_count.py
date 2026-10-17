# -*- coding: utf-8 -*-
r"""PIN: the schema's declared `.dat` write count equals what the recipe does.

## Why the number is declared instead of measured

`unit.availability`'s preview (`api._plan_availability`) has to report
`edit_count`, and after the `.dat` half was wired in (2026-10-16) that number is
no longer 0.  Measuring it would mean RUNNING the recipe, and `apply_grant`
serialises the whole 93 MB `.dat`: 25 s on this machine, against 9 s for a whole
preview.  A preview that takes 35 s is not a preview.

So `intents.json` declares `compile.dat_half.write_operations = 2`, and this pin
exists so the declaration cannot drift from the code in silence.  That is the
same contract as the label tables and the option lists: a promise in the schema
is checked against the artifact that fulfils it.

Two write operations, and the count is a property of the RECIPE, not of the data:

  1. one new Effect record carrying the anchor's own commands plus the enable
     command, and the anchor technology re-pointed at it;
  2. one `UnitConnection.EnablingResearch` patch plus one training `ButtonID`
     byte -- two byte writes on the serialised stream, reported as ONE edit
     because they are the same step and either both happen or neither does.

## What this pin would catch

`apply_grant` gaining a third edit (say, also touching the tech's cost) while the
schema still says 2 -- at which point the preview under-reports the work.  And the
reverse: the schema raised to 3 while the recipe does 2, which over-reports.
Either way `plan()` would promise something `build()` does not deliver, which is
the defect class this project already fixed twice.

Run:  $env:PYTHONPATH=D:\Software\AI\帝国项目; python _probe\test_dat_half_count.py
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.intent import compiler as C                   # noqa: E402
from aoe2mod.intent import datgrant as DG                  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT, BLDG, CIV_INDEX = 2550, 12, 1
CIV_KEY = "BRITONS"
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


print("A  the schema declares a count, and says why it is declared")
intents_schema, _bindings = C.load_schema()
spec = intents_schema["intents"]["unit.availability"]
_dh = (spec.get("compile") or {}).get("dat_half") or {}
DECLARED = _dh.get("write_operations")
check("dat_half declares write_operations", DECLARED is not None,
      json.dumps(_dh, ensure_ascii=False)[:200])
check("it is a positive integer", isinstance(DECLARED, int) and DECLARED > 0,
      repr(DECLARED))
check("and it explains that the count is declared rather than measured, "
      "because measuring it costs a 25 s serialisation",
      "serialis" in (_dh.get("write_operations_note") or "").lower(),
      repr(_dh.get("write_operations_note"))[:120])
check("the note names this pin, so a reader can find the other half of the "
      "contract",
      "test_dat_half_count" in (_dh.get("write_operations_note") or ""),
      repr(_dh.get("write_operations_note"))[:200])

print()
print("B  the recipe really performs that many write operations")
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, _tail, _how = tk._parsed
trees = CT.load_trees(GAME)
with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
_c, _c2, _gv, _t = L.locate(data, parser=_p)
brit = next(c for c in _c if c["name"] == "British")
techs = tk._tech_records()
tech_index, anchor, why = DG.pick_tech(techs, CIV_INDEX)
check("an anchor was found", tech_index is not None, why)
# ★ The stats handed to apply_grant are the LIVE toolkit's, and apply_grant
# appends an Effect to `stats["effects"]`.  Copy first: this pin must not leave
# the shared model one effect longer than the data it describes -- an earlier
# draft did exactly that and made every later probe in the same process read a
# phantom effect.
stats = dict(tk._stats)
stats["effects"] = list(tk._stats["effects"])
stats["techs"] = list(tk._stats["techs"])
stats["techs"][tech_index] = dict(tk._stats["techs"][tech_index])
out, rep = DG.apply_grant(stats, data, gv, CIV_INDEX, brit, trees[CIV_KEY],
                          UNIT, tech_index, BLDG, trees=trees)
ACTUAL = len(rep.get("edits") or ())
print("     anchor %s %r -> %d edit(s)" % (tech_index, (anchor or {}).get("name"),
                                           ACTUAL))
for e in rep.get("edits") or ():
    print("        %s" % e)
check("the recipe succeeded", rep.get("ok") is True, str(rep.get("reason")))
check("the declared count equals the recipe's own edit count",
      DECLARED == ACTUAL, "declared %r, recipe did %r" % (DECLARED, ACTUAL))

print()
print("C  the count is a property of the RECIPE, not of this one target")
# A second, unrelated grant -- a different unit into a different civilization --
# must report the same number.  If the count were target-dependent, the single
# schema declaration could not describe it and the design would be wrong, not
# just the number.
UNIT2, BLDG2, CIV2 = 692, 82, 21          # Berserk, into whichever civ index 21 is
_idx2, _anc2, _why2 = DG.pick_tech(techs, CIV2)
check("the second civilization has an anchor too", _idx2 is not None, _why2)
if _idx2 is not None:
    _civs2 = tk._civs
    _rec2 = _civs2[CIV2]
    _trees2 = trees
    _key2 = CT.civ_file_stem(_rec2["name"])
    _row2, _inh2 = CT.row_for(_trees2[_key2], UNIT2, CT.UNIT_USE_TYPES), None
    if _row2 is None:
        _dn, _dr = CT.donor_row(_trees2, UNIT2, CT.UNIT_USE_TYPES)
        _row2, _inh2 = _dr, _dn
    _bldg2 = (_row2 or {}).get("Building ID") or BLDG2
    stats2 = dict(tk._stats)
    stats2["effects"] = list(tk._stats["effects"])
    stats2["techs"] = list(tk._stats["techs"])
    stats2["techs"][_idx2] = dict(tk._stats["techs"][_idx2])
    _out2, _rep2 = DG.apply_grant(stats2, data, gv, CIV2, _rec2, _trees2[_key2],
                                  UNIT2, _idx2, _bldg2, trees=_trees2)
    ACTUAL2 = len(_rep2.get("edits") or ())
    print("     %s unit %d at building %s (donor %s) -> %d edit(s)"
          % (_key2, UNIT2, _bldg2, _inh2, ACTUAL2))
    check("a different unit in a different civilization reports the same count",
          ACTUAL2 == ACTUAL, "got %r vs %r" % (ACTUAL2, ACTUAL))

print()
print("D  and the preview reports the declared number WITHOUT running the recipe")
# The whole reason for the declaration.  Measured: `plan()` is ~9 s and
# `_dat_grant_half()` is ~25 s, so a preview that ran the recipe would be ~35 s.
plan = tk.plan({"intent": "unit.availability", "unit": UNIT, "civ": "British",
                "action": "grant"})
check("the plan reports the declared count",
      plan.get("edit_count") == DECLARED,
      "plan %r vs declared %r" % (plan.get("edit_count"), DECLARED))
check("and the plan says the `.dat` will be edited",
      plan.get("changes_dat") is True and plan.get("dat_is_carrier") is False,
      json.dumps({k: plan.get(k) for k in ("changes_dat", "dat_is_carrier")}))
# The revoke has no verified recipe, so the DECLARATION must not claim one --
# otherwise the preview would promise a `.dat` write the build refuses to make.
_rev = tk.plan({"intent": "unit.availability", "unit": 692, "civ": "Vikings",
                "action": "revoke"})
check("a revoke reports zero, because it has no verified `.dat` recipe",
      _rev.get("edit_count") == 0 and _rev.get("changes_dat") is False,
      json.dumps({k: _rev.get(k) for k in ("edit_count", "changes_dat",
                                           "dat_is_carrier")}))

print()
print("DAT HALF COUNT: the schema's declared `.dat` write count is the recipe's own")
print("  count, for two unrelated targets, and the preview reports it without")
print("  paying 25 s to run the recipe.  The number is a contract, not a guess.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
