# -*- coding: utf-8 -*-
r"""PIN: the menu is NOT panel-driven.  It is ALSO not tree-driven alone (v15).

## What the user ran (2026-10-15, no effective mod -- my bundle was `Enabled: false`)

GAME 2, Sicilians, Imperial Age, siege workshop -- their screenshots show:

    '升级到重型投石车（价格：1450食物，1000黄金）'   <- tech 320, Onager -> Siege Onager
    '建造重型投石车（价格：160木，135金）（热键：W）' <- unit 588

Both while `futuravailableunits.json` for SICILIANS / building 49 lists NEITHER 588
nor 320 (`Units` = 8 entries, `Techs` = [96, 255, 257, 239]), and
`CivTechTrees/SICILIANS.json` grants 588 `ResearchedCompleted`.

**GAME 2 alone refutes "the menu is fed by futuravailableunits.json".**

## GAME 1, Poles, dock -- ANSWERED 2026-10-18 (this used to say "no usable evidence")

The user re-ran GAME 1 against the shipped game and reported the decisive fact
directly: **the Polish dock has NO Elite Cannon Galleon upgrade button.**

That closes the half GAME 2 left open, because the panel is now excluded from
BOTH directions:

    panel lists 691 in Units AND 376 in Techs   -> the button should exist
    the user saw no button                      -> **the panel is NOT sufficient**

Together with GAME 2 (panel silent, button existed -> the panel is NOT necessary),
`futuravailableunits.json` is now excluded as the source of the facility menu.

## ⚠️ 2026-10-19: "so the tree supplies it" was WRONG -- v15 refuted that

This file used to continue "...and the tree is the only layer consistent with
every observation", which was an overreach: excluding one layer is not evidence
for another.  `dsh test v15` tested it directly.

`_probe/build_dshtest_v15.py` shipped **two `CivTechTrees/<CIV>.json` files and
nothing else** -- the `.dat` was a byte-identical carrier (sha256 asserted), the
panel was untouched, and both trees were asserted chain-closed (Incas loses 2550
with its whole chain `[2550, 2552, 2554, 2588]`, Britons gains a 2550 row in the
Dark Age Barracks).  The same mod also carried a `.dat` edit already proven to
render in game (villagers 25 -> 1000 hp), so "did the mod load?" was answerable.

The user's reading: **the villagers were 1000 hp (the control worked) and
NEITHER tree change showed up** -- Incas still had the Champi Scout, Britons
still did not.  The mod demonstrably loaded (`MainLog.txt` shows `Enabling mod`),
so the JSON was written, mounted, and still not read by the facility menu.

**The only layer this project has ever observed moving that menu is a `.dat`
byte**: `dsh test v5` (2026-10-16) changed British unit 2550's
`train_location.ButtonID` 1 -> 4 -- one byte -- and the button appeared, because
slot 1 was already full with the five-unit militia line.  `dsh test v16`
(2026-10-19) isolates that: two `.dat` bytes, no JSON layer touched at all.

Side note on the old screenshot: the Poles cannon-galleon tooltip containing
`升级：升级到精锐炮舰` is still not evidence of anything -- see below.

## Why that Poles tooltip must NOT be over-read

The user's first Poles screenshot showed the Cannon Galleon tooltip containing

    升级：升级到精锐炮舰

while Poles' **tree** marks 691 `NotAvailable`.  Read naively, that would say the
dock offers an upgrade the tree refuses -- i.e. the menu unions the layers.

**It does not.**  That sentence is literal shipped string text (line 6914 of
`resources/zh/strings/key-value/key-value-strings-utf8.txt`, string id 26287):

    26287 "建造<b>炮舰<b> (<cost>)\n...<GREY><i>升级：升级到精锐炮舰 (码头)；攻击力，
           射程，护甲，速度，费用，生产速度 (大学)；...<i><DEFAULT>..."

It is **unit 420's own help string**, chosen by the unit record's help id, so it is
identical for every civilization that has unit 420.  The `<GREY>` markup marks it as
greyed-out boilerplate.  There is a sibling for the upgraded unit (id 26573,
`建造精锐炮舰`), whose text says only `升级：攻击力，射程，...` -- no unit name.

**So the string proves nothing about whether the upgrade is reachable.**  This is the
fourth time in this investigation that shipped text was mistaken for behaviour.

## The honest state of the answer

  * **refuted, both directions**:
      - not NECESSARY: GAME 2 -- panel silent on 588/320, both were on screen.
      - not SUFFICIENT: GAME 1 -- panel lists 691 and 376, no button appeared.
    Therefore `futuravailableunits.json` does not supply the facility menu.
  * **REFUTED 2026-10-19**: "the tree is what the menu follows".  v15 wrote only
    the two tree files (byte-identical `.dat` carrier, panel untouched, chains
    asserted closed) and NEITHER side moved in game.  The mod loaded.  See the
    header of this file.
  * **ALSO REFUTED 2026-10-19**: "the `.dat` button slot alone is enough".  v16
    sent one `.dat`, no JSON at all, exactly two bytes (British 2550 slot 1->4,
    Incas 2550 gate `Disabled` 0->1), verified byte-exact and mounted by the
    engine -- and the user reported neither side changed.  So v5's single byte
    was the last missing byte of a set that already carried the `type 2` enable
    effect; the slot decides WHICH CELL a granted unit lands in, not whether it
    is granted at all.
  * **the only PROVEN ingredient**: the `.dat` `type 2` enable command
    (`a=<unit>, b=1`) hung on a civilization-owned free technology -- `dsh test
    v5/v6/v7`, and what the product's `datgrant` recipe writes.  `dsh test v17`
    (2026-10-19) asks the mirror question: whether `type 2, b=0` can DISABLE a
    unit for one civilization (the shipped precedent is Armenians/Georgians
    losing the Lumber Camp via `tech 932/940` -> `effect 944`).
  * **what the panel presumably does**: a separate 99.4%-identical copy, plausibly
    feeding the greyed-out "future items" preview (`widgetui\futuravailableunits.json`
    is an 81-byte redirect stub naming this exact file, so the engine does read it).

## Consequence for the product

`unit.availability` writes **both** JSON layers plus the `.dat` half, in BOTH
directions.  Given that neither JSON layer has ever been observed moving the
facility menu on its own, **the `.dat` half is the part that actually works** and
the JSON halves are the part whose effect is still unproven.  That inverts the
earlier reading: `grant` writes `.dat` and has an in-game result (v7, Champi Scout
in the Dark Age Barracks), and since 2026-10-19 so does `revoke` (v17, the Champi
Scout gone from the Castle Age).

**2026-10-19 follow-up**: v16 showed the `.dat` half is not reducible to the button
slot either -- grant needs the `type 2` enable command, which is exactly what
`datgrant` writes.  So `grant` is coherent: two written bytes plus the enable
effect.  **v17 filled the revoke hole**: `type 2, b=0` does gate the menu, and the
ordering rule is part of the result -- the same disable hung on a 0:00 carrier
LOST to the global enable, and on a Castle-Age carrier it WON.

Run:  python _probe\test_time_gate_and_tooltip.py
"""
import os
import _gamepaths as GP
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

print("A  the tooltip sentence is SHIPPED TEXT, not generated behaviour")
STR = os.path.join(GAME, "resources", "zh", "strings", "key-value",
                   "key-value-strings-utf8.txt")
lines = open(STR, "rb").read().decode("utf-8-sig", "replace").splitlines()
hit = None
for ln in lines:
    if ln.startswith("26287 "):
        hit = ln
        break
check("string 26287 is unit 420's help text", hit is not None and "炮舰" in hit)
if hit:
    check("and it literally contains the upgrade sentence the screenshot showed",
          "升级：升级到精锐炮舰" in hit, "line=%r" % hit[:120])
    check("the sentence is inside <GREY> markup -- greyed boilerplate",
          "<GREY>" in hit)
    print("     %r" % hit[:190])
_sib = next((ln for ln in lines if ln.startswith("26573 ")), None)
check("the upgraded unit has a sibling help string with NO unit name in it",
      _sib is not None and "升级：攻击力" in _sib and "精锐炮舰" not in
      _sib.split("\\n")[2] if _sib else False, "sibling=%r" % (_sib or "")[:120])
print("     -> it is a property of the UNIT, so it is identical in every civ that")
print("        has unit 420.  It cannot show whether an upgrade is reachable.")

print()
print("B  GAME 2 observed, restated against both files")
o = panels[BP.panel_path_for(GAME, "Sicilians")[1]]["obj"]
pu, pt = set(), set()
for blk in BP.buildings(o, "Sicilians"):
    if blk.get("ID") == 49:
        pu = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
        pt = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
print("     panel Units at the siege workshop : %s" % sorted(pu))
print("     panel Techs at the siege workshop : %s" % sorted(pt))
check("the panel does NOT list unit 588", 588 not in pu)
check("the panel does NOT list tech 320 (its upgrade)", 320 not in pt)
check("the tree DOES grant 588 ResearchedCompleted",
      CT.node_status(trees["SICILIANS"], 588, CT.UNIT_USE_TYPES)
      == "ResearchedCompleted")
print()
print("     The user's screenshots show the game offering BOTH the upgrade to")
print("     重型投石车 and the unit 重型投石车 in that workshop.")
print("     => the facility menu is NOT fed by the panel alone.  REFUTED.")

print()
print("B2 GAME 1 observed 2026-10-18 -- the OTHER direction: panel says YES")
_o = panels[BP.panel_path_for(GAME, "Poles")[1]]["obj"]
_pk = BP.civ_key_for(panels, "POLES")
_blk = BP.building_block(_o, _pk, 45)
_pu = {e.get("ID") for e in (_blk.get(BP.UNITS_KEY) or [])}
_pt = {e.get("ID") for e in (_blk.get(BP.TECHS_KEY) or [])}
check("the panel lists unit 691 at the Poles' dock", 691 in _pu, "Units=%s"
      % sorted(_pu))
check("the panel lists upgrade tech 376 at the Poles' dock", 376 in _pt,
      "Techs=%s" % sorted(_pt))
check("the tree marks unit 691 NotAvailable",
      CT.node_status(trees["POLES"], 691, CT.UNIT_USE_TYPES) == "NotAvailable")
check("the tree has NO row for tech 376 at all",
      CT.row_for(trees["POLES"], 376, CT.TECH_USE_TYPES) is None)
print("     The user looked at the Polish dock in the shipped game and saw NO")
print("     Elite Cannon Galleon upgrade button.")
print("     => a panel that lists the unit AND its upgrade tech did not produce a")
print("        button.  The panel is NOT SUFFICIENT either.")
print("     => with GAME 2 (not necessary) this excludes the panel BOTH ways.")

print()
print("C  the competitor explanations that remain, ranked by evidence")
print("     1. the .dat type 2 ENABLE command is the working ingredient -- PROVEN")
print("        v5/v6/v7: hung on a civ-owned free tech, the Dark Age Barracks")
print("        showed the Champi Scout.  But the BUTTON SLOT alone is NOT enough")
print("        (v16: two bytes, one .dat, no JSON -> neither side moved)")
print("     2. the TREE is what the facility menu follows           -- REFUTED")
print("        2026-10-19 by dsh test v15: two tree files only, mod loaded,")
print("        neither side changed in game")
print("     3. the menu UNIONS tree and panel                     -- refuted for the")
print("        panel half by GAME 1 (the union would have shown the button)")
print("     4. the panel feeds the GREYED-OUT future preview only -- plausible,")
print("        matches the file's name and its display-only Prereq* fields,")
print("        and is exactly what IDS_OPT_DISPLAY_FUTURE_ITEMS toggles")
# The tree DOES carry `Prerequisite IDs` / `Prerequisite Types` (data/link
# fields); what it lacks is the PANEL's display-only gate fields.  Test for
# those exact names, not the "Prereq" prefix, or the tree's own link fields
# make the assertion false.
_PANEL_PREQ_DISPLAY = ("PrereqTech", "PrereqIconSet", "PrereqIconIndex",
                       "PrereqStyle", "PrereqStringID")
_tree_prereq = any(k in _PANEL_PREQ_DISPLAY for t in trees.values()
                   for r in CT.rows_of(t) for k in r)
check("the tree carries no Prereq* display field (only the panel does)",
      not _tree_prereq)
_panel_prereq = sum(1 for blk in BP.buildings(o, "Sicilians")
                    for e in (blk.get(BP.UNITS_KEY) or [])
                    + (blk.get(BP.TECHS_KEY) or [])
                    if any(k.startswith("Prereq") for k in e))
check("the panel entries carry Prereq* display fields",
      _panel_prereq > 0, "Sicilians prereq entries: %d" % _panel_prereq)

print()
print("D  the product consequence")
print("     aoe2mod/api.py's _build_availability writes BOTH the tree and the panel")
print("     [note] the panel-vs-tree agreement (99.4%) is pinned by "
      "_probe/test_panel_tree_agreement.py, not re-derived here")
print("     -> neither JSON layer has ever been observed moving the facility menu")
print("        on its own; the .dat half is the part with an in-game result (v7).")
print("        Writing both stays correct, but the panel is the least supported")
print("        of the three layers -- keep it only for the greyed-out preview.")

print()
print("TIME GATE + TOOLTIP: the tooltip answered nothing (shipped prose).  The two")
print("  game observations together exclude the panel both as necessary (GAME 2)")
print("  and as sufficient (GAME 1).  They do NOT prove the tree -- dsh test v15")
print("  (2026-10-19) wrote only the tree files, the mod loaded, and neither side")
print("  changed in game.  The .dat `type 2` enable command is the only proven")
print("  ingredient -- and v16 showed the button slot WITHOUT that command is")
print("  not enough either (two bytes, no JSON, neither side moved).")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
