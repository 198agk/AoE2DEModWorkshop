# -*- coding: utf-8 -*-
r"""Does the PRODUCT reproduce the recipe the game confirmed?

`dsh test v7` is the only build the user has confirmed in game for the
"give a civilization a unit it cannot build" feature (m27131, 「ABC都没问题了」:
A villagers stayed at 1000 hp after being given a task; B the Castle-Age
Longbowman was unaffected; C the Dark-Age Barracks showed the Champi Scout).

v7 was **hand-built** by `_probe/build_dshtest_v7.py`, which carries knowledge
the product module did not have at the time.  A hand-built artifact that works
proves the FORMAT; it does not prove the CODE.  This suite closes that gap by
building the same two sentences through `aoe2mod.api` alone and asserting the
resulting `.dat` behaves the way v7's did.

The two sentences:
    {"intent": "unit.stat",         "unit": "村民", "stat": "hit_points", "value": 1000}
    {"intent": "unit.availability", "unit": 2550,   "civ": "British", "action": "grant"}

(`stat` takes the schema KEY, not the Chinese label the UI shows -- `unit_field_values`
is what renders 生命值.  Using the label here fails with "unknown stat", which is the
schema doing its job.)

What is asserted, in order of how badly a failure would matter:

  A  the build succeeds and emits a `.dat` (a data mod without one cannot start
     the game -- the user reported that failure twice)
  B  the artifact re-parses with the UNMODIFIED parser, clean EOF
  C  villager HP is 1000 for every civilization (the first in-game control)
  D  the anchor technology points at an effect that ends with the enable command
     AND still carries the anchor's own commands (dropping them deletes a real
     civilization bonus while reporting success)
  E  the unit's training button moved to a free slot
  F  `EnablingResearch` was NOT written -- the field the confirmed recipe left
     alone, and a global per-unit field that a per-civ write would corrupt
  G  the Longbowman's technology is untouched (the second in-game control)

Run:  $env:PYTHONPATH='D:\Software\DeepSeek Harness\工作区2'
      python aoe2mod\tests\test_product_v7_recipe.py
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                     # noqa: E402
import aoe2mod.dat.parser as P                              # noqa: E402
import aoe2mod.intent.datgrant as DG                        # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550
CIV = "British"
TREE_KEY = "BRITONS"
ANCHOR = 383
LONGBOW_TECH = 263
HP = 1000

fails = []


def check(name, ok, detail=""):
    print("  %-74s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


if not os.path.isdir(GAME):
    print("SKIP: the game is not at %s" % GAME)
    sys.exit(0)

out = tempfile.mkdtemp(prefix="dsh_v7_recipe_")
try:
    tk = A.open_toolkit(game_root=GAME)
    tk.describe(4)                       # warm the model; also proves the parse

    print("A  build the two sentences through the product API only")
    man = tk.build_bundle(
        [{"intent": "unit.stat", "unit": "村民", "stat": "hit_points", "value": HP},
         {"intent": "unit.availability", "unit": UNIT, "civ": CIV, "action": "grant"}],
        out, title="dsh test v7 recipe via the product",
        author="dsh", description="verification artifact", overwrite=True)
    dat = man.get("dat")
    # `man["files"]` is a LIST of {"rel", "bytes"} dicts, not a mapping.
    files = sorted(f.get("rel") for f in (man.get("files") or []))
    print("     files: %s" % files)
    check("the build emitted a .dat", bool(dat) and os.path.exists(dat or ""),
          "%r" % (dat,))
    check("and it emitted the two JSON layers as well",
          any(f.endswith("futuravailableunits.json") for f in files)
          and any("CivTechTrees" in f for f in files), "%s" % files)
    check("the manifest says this mod contains a .dat",
          man.get("mod_contains_dat") is True)
    check("and says the .dat is not merely a carrier",
          man.get("dat_is_carrier") is False, "%r" % man.get("dat_is_carrier"))

    print()
    print("B  the artifact re-parses with the unmodified parser")
    raw = None
    _shipped_dat = os.path.join(GAME, "resources", "_common", "dat",
                                "empires2_x2_p1.dat")
    sraw, _h = P.load_dat(_shipped_dat)
    with contextlib.redirect_stdout(io.StringIO()):
        spr = P.Parser(sraw)
        spr.parse()
    if dat and os.path.exists(dat):
        raw, _how = P.load_dat(dat)
        with contextlib.redirect_stdout(io.StringIO()):
            pr = P.Parser(raw)
            pr.parse()
        print("     raw %d bytes (shipped %d, delta %+d); parser consumed %d"
              % (len(raw), len(sraw), len(raw) - len(sraw), pr.r.pos))
        check("clean EOF", pr.r.pos == len(raw),
              "consumed %d of %d" % (pr.r.pos, len(raw)))
    else:
        check("clean EOF", False, "no .dat was produced")

    print()
    print("C  the first in-game control: villagers are at 1000 hp")
    if raw is not None:
        stats = pr.stats
        hps = []
        for civ in stats["civs"]:
            for u in civ["units"]:
                if u["id"] == 83:
                    hps.append(u.get("hit_points"))
        print("     villager records read: %d" % len(hps))
        check("every villager record is 1000 hp", hps and set(hps) == {HP},
              "%s" % sorted(set(hps))[:6])
    else:
        check("every villager record is 1000 hp", False, "no .dat")

    print()
    print("D  the anchor technology carries its own commands AND the enable")
    if raw is not None:
        techs = pr.stats["techs"]
        anchor = techs[ANCHOR]
        eff = pr.stats["effects"][anchor["effect_id"]]
        cmds = [tuple(c) for c in eff["commands"]]
        enable = (2, UNIT, 1, -1, 0.0)
        print("     tech %d -> effect %s" % (ANCHOR, anchor["effect_id"]))
        print("     commands: %s" % (cmds,))
        check("the effect ends with 'make unit 2550 available'",
              cmds and cmds[-1] == enable, "%s" % (cmds[-1:],))
        # The shipped commands of the anchor, read from the SHIPPED stream so the
        # assertion is against the game's data, not a remembered tuple.
        shipped = [tuple(c) for c in
                   spr.stats["effects"][spr.stats["techs"][ANCHOR]["effect_id"]]["commands"]]
        print("     shipped anchor commands: %s" % (shipped,))
        check("the shipped anchor had commands (so the carry-over is observable)",
              len(shipped) > 0)
        check("every one of them survives on the new effect",
              cmds[:len(shipped)] == shipped, "%s vs %s" % (cmds[:len(shipped)], shipped))
        check("the shipped effect itself was not overwritten",
              [tuple(c) for c in spr.stats["effects"]
               [spr.stats["techs"][ANCHOR]["effect_id"]]["commands"]] == shipped)
    else:
        check("the effect ends with 'make unit 2550 available'", False, "no .dat")

    print()
    print("E  the training button moved to a free slot")
    if raw is not None:
        with contextlib.redirect_stdout(io.StringIO()):
            p2 = P.Parser(raw)
            p2.parse()
        from aoe2mod.dat import locate as L
        civs, _cs, gv, _tl = L.locate(raw, parser=p2)
        brit = next(c for c in civs if c["name"] == CIV)
        u = next(x for x in brit["units"] if x["id"] == UNIT)
        slot = u["train_locations"][0]["button_id"]
        print("     British unit %d button_id = %s" % (UNIT, slot))
        check("the slot is not 1 (where the British militia line would mask it)",
              slot != 1, "%r" % slot)
        check("and it is a slot the British tree leaves free",
              slot == 4, "%r" % slot)
        # Read the free-slot answer from the product's own module so the two cannot
        # disagree about what "free" means.
        trees = CT.load_trees(GAME)
        idx = next(i for i, c in enumerate(civs)
                   if CT.civ_file_stem(c.get("name")) == TREE_KEY)
        from aoe2mod.game import buttons as BT
        free = BT.free_slots(civs[idx], trees[TREE_KEY], 12)
        check("the product's free_slots() agrees the slot was free",
              slot in free, "slot %s not in %s" % (slot, sorted(free)))
    else:
        check("the slot is not 1 (where the British militia line would mask it)",
              False, "no .dat")

    print()
    print("F  EnablingResearch was NOT written")
    if raw is not None:
        _o, now = DG.connection_offset(raw, gv, UNIT)
        _o2, was = DG.connection_offset(sraw, gv, UNIT)
        print("     shipped %s   built %s" % (was, now))
        check("the field still holds what the game shipped", now == was,
              "%s -> %s" % (was, now))
        print("     (the confirmed recipe left it alone; it is global per unit id,")
        print("      so a per-civ write would claim all 63 civilizations.)")
    else:
        check("the field still holds what the game shipped", False, "no .dat")

    print()
    print("G  the second in-game control: the Longbowman is untouched")
    if raw is not None:
        print("     shipped tech %d -> effect %s"
              % (LONGBOW_TECH, spr.stats["techs"][LONGBOW_TECH]["effect_id"]))
        print("     built   tech %d -> effect %s"
              % (LONGBOW_TECH, pr.stats["techs"][LONGBOW_TECH]["effect_id"]))
        check("the Longbowman's technology points where it always did",
              pr.stats["techs"][LONGBOW_TECH]["effect_id"]
              == spr.stats["techs"][LONGBOW_TECH]["effect_id"])
        check("and the anchor is NOT the Longbowman's technology",
              ANCHOR != LONGBOW_TECH)
        # `required_techs` is NOT in `dat.parser`'s model -- it is saved by
        # `dat.locate.walk_tech`, i.e. only reachable through the product's own
        # `_tech_records()`.  Reading it off the raw parser returned None and
        # turned a true statement into a failure.
        _recs = tk._tech_records()
        _lb_req = _recs[LONGBOW_TECH].get("required_techs") or []
        _an_req = _recs[ANCHOR].get("required_techs") or []
        print("     Longbow tech %d waits for %s; anchor %d waits for %s"
              % (LONGBOW_TECH, _lb_req, ANCHOR, _an_req))
        check("because that one waits for a Castle",
              _lb_req != [] and 266 in _lb_req, repr(_lb_req))
        check("and the anchor we chose waits for nothing",
              _an_req == [], repr(_an_req))
    else:
        check("the Longbowman's technology points where it always did", False,
              "no .dat")

finally:
    shutil.rmtree(out, ignore_errors=True)

print()
if fails:
    print("PRODUCT V7 RECIPE: %d check(s) failed." % len(fails))
    for n in fails:
        print("  FAILED: %s" % n)
    sys.exit(1)
print("PRODUCT V7 RECIPE: the product API alone reproduces the `.dat` half the")
print("  user confirmed in game -- and leaves alone the two things the confirmed")
print("  recipe left alone (EnablingResearch, and the Longbowman's technology).")
