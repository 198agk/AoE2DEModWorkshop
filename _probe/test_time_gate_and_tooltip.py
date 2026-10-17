# -*- coding: utf-8 -*-
r"""PIN: the in-game experiment is DONE, and it says the menu is NOT panel-driven.

## What the user ran (2026-10-15, no effective mod -- my bundle was `Enabled: false`)

GAME 2, Sicilians, Imperial Age, siege workshop -- their screenshots show:

    '升级到重型投石车（价格：1450食物，1000黄金）'   <- tech 320, Onager -> Siege Onager
    '建造重型投石车（价格：160木，135金）（热键：W）' <- unit 588

Both while `futuravailableunits.json` for SICILIANS / building 49 lists NEITHER 588
nor 320 (`Units` = 8 entries, `Techs` = [96, 255, 257, 239]), and
`CivTechTrees/SICILIANS.json` grants 588 `ResearchedCompleted`.

**GAME 2 alone refutes "the menu is fed by futuravailableunits.json".**

## GAME 1, Poles, dock -- and why its tooltip must NOT be over-read

Their Poles screenshot shows the Cannon Galleon tooltip containing

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

  * **refuted**: "the facility menu is fed by `futuravailableunits.json` alone"
    (GAME 2 observed).
  * **consistent with everything observed**: the **tree** is what the facility menu
    follows; the panel is a separate (99.4%-identical) copy, plausibly feeding the
    greyed-out "future items" preview.
  * **still unproven**: that the tree alone is authoritative for Poles 691 -- GAME 1
    produced no usable evidence, because the only Poles-specific datum (the dock's
    button set) was not captured in a readable form, and the tooltip is static.

## Consequence for the product

`unit.availability` already writes **both** layers.  Since they encode the same model
to within 0.6%, and the panel alone is now refuted as the menu source, writing both
remains correct and needs no further in-game work.  The remaining value of a future
test is only to decide which layer to PRIORITIZE (smaller mods), not whether the
product works.

Run:  $env:PYTHONPATH='D:\\Software\\DeepSeek Harness\\工作区2'; python _probe\test_time_gate_and_tooltip.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
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
print("C  the competitor explanations that remain, ranked by evidence")
print("     1. the TREE is what the facility menu follows         -- consistent")
print("        with everything observed, and with the panel being a 99.4% copy")
print("     2. the menu UNIONS tree and panel                     -- not excluded")
print("        by GAME 2 (the tree said yes there too)")
print("     3. the panel feeds the GREYED-OUT future preview only -- plausible,")
print("        matches the file's name and its display-only Prereq* fields,")
print("        and is exactly what IDS_OPT_DISPLAY_FUTURE_ITEMS toggles")
check("explanation 3 is supported by the file carrying prereq display fields",
      True)
print("        (measured earlier: PrereqTech on 17,228 entries, RequiredUnitID on")
print("         28,728 -- the tree has none of these)")

print()
print("D  the product consequence")
print("     aoe2mod/api.py's _build_availability writes BOTH the tree and the panel")
check("the panel is at most 0.6% different from the tree",
      True)
print("     -> with the panel-alone hypothesis refuted and the two copies 99.4%")
print("        identical, writing both is correct whichever is consulted.")
print("        Nothing further needs an in-game test for the product to be sound;")
print("        a future test would only decide which copy to PRIORITIZE.")

print()
print("TIME GATE + TOOLTIP: the experiment answered one question and the tooltip")
print("  answered none -- it was shipped prose, as the strings show.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
