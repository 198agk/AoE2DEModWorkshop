"""Does ONE bundle build all three layers of a grant, and does the preview say so?

Before this existed, `build_bundle` applied the CivTechTrees file and the build
panel and then shipped a `.dat` that was byte-identical to the base, while
`changes_dat` read True because an unrelated sentence (`unit.stat villager hp`)
had set `bool(dat_list)`.  A mod that does less than its own manifest claims is
the recurring defect class of this project.

WHY THIS IS A PERMANENT PIN, not a one-off.  The single-intent path
(`Toolkit._build_availability`) and the bundle path (`Toolkit.build_bundle`) are
two separate implementations of the same three layers, and they had already
drifted once -- the bundle path silently omitted the `.dat` half while every fast
suite stayed green, because nothing exercised a bundle that mixed a `.dat`
sentence with an availability grant.  Every future change to either path has to
keep this file passing.

Run: python _probe/test_bundle_dat_half_e2e.py
"""
import contextlib
import io
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A                    # noqa: E402
from aoe2mod.dat import parser as P        # noqa: E402
from aoe2mod.dat import locate as L        # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.game import buildpanel as BP  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
fail = []


def check(name, ok, detail=""):
    print("%-4s %s%s" % ("OK" if ok else "FAIL", name,
                         ("  [%s]" % detail) if detail else ""))
    if not ok:
        fail.append(name)


BUNDLE = [
    {"intent": "unit.stat", "unit": "Villager", "stat": "hit_points", "value": 1000},
    {"intent": "unit.availability", "unit": UNIT, "civ": "British", "action": "grant"},
]

tk = A.open_toolkit(GAME)

# ---------------------------------------------------------------- preview ----
print("== preview ==")
plan = tk.plan_bundle(BUNDLE)
for k in ("edit_count", "dat_half_edit_count", "changes_dat", "dat_is_carrier",
          "mod_contains_dat", "civs_edited", "overlap_count"):
    print("   %-22s %r" % (k, plan.get(k)))
print("   dat_half_refusals       %r" % (plan.get("dat_half_refusals"),))
check("the preview counts the .dat half of the grant",
      plan.get("dat_half_edit_count") == 2, repr(plan.get("dat_half_edit_count")))
check("the preview counts BOTH halves",
      plan.get("edit_count") == plan.get("dat_half_edit_count") + 1701,
      "edit_count=%r (villager hp writes 1701)" % plan.get("edit_count"))
check("changes_dat is true", plan.get("changes_dat") is True)
check("dat_is_carrier is false, because real .dat bytes are written",
      plan.get("dat_is_carrier") is False)
check("no refusal was hidden", plan.get("dat_half_refusals") == [])

# ------------------------------------------------------------------ build ----
print("== build ==")
out = tempfile.mkdtemp(prefix="dsh_bundle_")
man = tk.build_bundle(BUNDLE, out, title="dsh tmp bundle",
                      author="dsh", description="probe", overwrite=True)
for k in ("edit_count", "dat_half_edit_count", "changes_dat", "dat_is_carrier",
          "mod_contains_dat", "dat_file_bytes", "dat_raw_bytes"):
    print("   %-22s %r" % (k, man.get(k)))
check("the build counts the .dat half",
      man.get("dat_half_edit_count") == 2, repr(man.get("dat_half_edit_count")))
check("build's edit_count == preview's",
      man.get("edit_count") == plan.get("edit_count"),
      "%r vs %r" % (man.get("edit_count"), plan.get("edit_count")))
check("the manifest carries the per-half report",
      isinstance(man.get("dat_half"), list) and len(man["dat_half"]) == 1,
      repr(man.get("dat_half"))[:120])

# ----------------------------------------------- the bytes on disk -----------
print("== on disk ==")
dat = man.get("dat")
check("a .dat is on disk", bool(dat) and os.path.isfile(dat), str(dat))
raw, how = P.load_dat(dat)
base, _ = P.load_dat(os.path.join(GAME, "resources", "_common", "dat",
                                  "empires2_x2_p1.dat"))
p = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
check("reparses to the last byte", p.r.pos == len(raw),
      "%d of %d" % (p.r.pos, len(raw)))
check("the .dat really grew (an effect was appended)",
      len(raw) > len(base), "%d vs base %d (+%d)" % (len(raw), len(base),
                                                     len(raw) - len(base)))
_anchor = p.stats["techs"][383]
check("tech 383 was re-pointed at a new effect",
      _anchor["effect_id"] == len(p.stats["effects"]) - 1,
      "effect_id=%r" % _anchor["effect_id"])
_cmds = [tuple(c) for c in p.stats["effects"][_anchor["effect_id"]]["commands"]]
check("the new effect carries the anchor's own commands AND the enable",
      _cmds == [(5, 592, -1, 13, 1.25), (5, 590, -1, 13, 1.25),
                (2, UNIT, 1, -1, 0.0)], repr(_cmds))
check("tech 263 (the age-gated anchor) is untouched",
      p.stats["techs"][263]["effect_id"] == 251)

# the villager edit must have survived the fold
civs, _cs, gv, _tail = L.locate(raw, parser=p)
_brit = next(c for c in civs if c["name"] == "British")
_hp = sorted({u["hit_points"] for u in _brit["units"] if u["id"] == 83})
check("the villager edit survived the fold (both halves in one file)",
      _hp == [1000], repr(_hp))
_u2550 = next(u for u in _brit["units"] if u["id"] == UNIT)
_slot = _u2550["train_locations"][0]["button_id"]
check("the button moved to slot 4", _slot == 4, repr(_slot))

# the two JSON layers
trees = CT.load_trees(out)
check("the tree file has the granted row",
      CT.node_status(trees.get("BRITONS"), UNIT) == "ResearchedCompleted",
      repr(CT.node_status(trees.get("BRITONS"), UNIT)))
if trees.get("BRITONS"):
    print("   tree path: %s" % trees["BRITONS"].get("path"))
_panels = BP.load_all(out)
_pk = None
for k, v in _panels.items():
    if k == "Britons":
        _pk = v
check("the panel file has the grant", _pk is not None)
if _pk:
    _found = None
    for blk in BP.buildings(_pk["obj"], _pk["key"]):
        if blk.get("ID") == 12:
            _found = BP.entries(_pk["obj"], _pk["key"], 12, BP.UNITS_KEY)
    _ids = [e.get("ID") for e in (_found or [])]
    check("Barracks lists unit 2550 in the panel", UNIT in _ids, repr(_ids))

print()
print("BUNDLE DAT HALF: %d failure(s)" % len(fail))
for f in fail:
    print("  * %s" % f)
sys.exit(1 if fail else 0)
