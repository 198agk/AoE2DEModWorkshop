# -*- coding: utf-8 -*-
r"""PIN: `aoe2mod.intent.datgrant` builds the `.dat` half of a unit grant.

Two in-game results shaped this file.

`dsh test v5` worked but only after a Castle (user m25909 then m26421):
「A和B依旧没问题，C还是必须建了城堡后，兵营里才会出现蔷琵侦察兵的按钮」. That
report turned out to be pointing at the ANCHOR: v5 hung the enable on tech 263
'Longbow (make avail)', whose `RequiredTechs` is `[102, 266 'Castle built']`. Section
A pins the corrected rule -- the anchor is chosen by `RequiredTechs`, not by name.

Comparing the module against the v5 artifact then exposed a second defect: v5 copied
the anchor effect's existing commands into its new effect BY HAND, and the module did
not, so it silently deleted the British faster-shepherd bonus while reporting ok=True.
Section C pins the carry-over against the SHIPPED bytes rather than against a
written-down tuple.

It also pins the one place where the writer's model is NOT enough -- it costs a
silent failure when assumed:

  * `Parser.stats["civs"][i]["units"][j]` has no `train_locations`, so the button slot
    must be a byte patch (an earlier draft read `u["train_locations"]` there and got
    `None`, then reported `ok=False` for no visible reason).

And it pins the offset rule: offsets are derived on the SERIALIZED stream, because
appending an effect moves the TechTree stage.

Section B and C pin the OPPOSITE decision, which the confirmed recipe forced: the
module does NOT write `EnablingResearch`.  `dsh test v7` wrote no such byte, the field
does not gate (v5 set it, v6 cleared it, both behaved the same in game), and it is
global per unit id -- so pointing it at one civilization's private technology would
claim all 63 are enabled by it.  See `_probe/probe_enabling_scope.py`.
"""
import contextlib
import _gamepaths as GP
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
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.intent import datgrant as DG                  # noqa: E402

GAME = GP.GAME
V5 = os.path.join(HERE, "out_dshtest_v5", "resources", "_common", "dat",
                  "empires2_x2_p1.dat")
UNIT, BLDG, CIV_INDEX = 2550, 12, 1
ANCHOR = 383          # what the module must choose: RequiredTechs == [] -> fires at 0:00
LONGBOW_TECH = 263    # what the NAME rule chose, and what dsh test v5 shipped
TECH = ANCHOR         # kept because this file's sections below were written against it
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, _tail, _how = tk._parsed
TREES = CT.load_trees(GAME)
with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
_c, _c2, _gv, _t = L.locate(data, parser=_p)
brit = next(c for c in _c if c["name"] == "British")

print("A  the module's own helpers")
idx, tech, why = DG.pick_tech(tk._tech_records(), CIV_INDEX)
print("     pick_tech(civ 1) -> %s %r  why=%r"
      % (idx, (tech or {}).get("name"), why))
# The anchor is chosen by `RequiredTechs`, not by the tech's NAME.  That
# distinction is the whole of dsh test v7: the name rule picked 263, whose
# RequiredTechs is [102, 266 'Castle built'], so the user only saw the Barracks
# button after building a Castle (m26421).  Asserting the ANCHOR alone would pass
# for the wrong reason, so this also asserts that the discarded rule really does
# name a different tech -- if a future data update made the name rule agree, the
# third check fails and says so instead of quietly turning the pin into a no-op.
check("it puts the effect on a tech that fires at 0:00", idx == ANCHOR, "got %s" % idx)
check("that tech's RequiredTechs is empty",
      not tech.get("required_techs"), "got %s" % tech.get("required_techs"))
check("the tech whose NAME says 'make avail' is a different, age-gated one",
      LONGBOW_TECH != idx
      and tk._tech_records()[LONGBOW_TECH].get("required_techs") == [102, 266],
      "263 has %s" % tk._tech_records()[LONGBOW_TECH].get("required_techs"))
check("the enable command is (2, unit, 1, -1, 0.0)",
      DG.enable_command(UNIT) == (2, UNIT, 1, -1, 0.0))
_o, _v = DG.connection_offset(data, gv, UNIT)
print("     connection_offset(%d) = %d (value %s)" % (UNIT, _o, _v))
check("the base EnablingResearch is -1", _v == -1, "got %s" % _v)

print()
print("B  apply_grant reproduces v5 -- same edits, same slot")
out, rep = DG.apply_grant(_p.stats, data, gv, CIV_INDEX, brit, TREES["BRITONS"],
                          UNIT, TECH, BLDG, trees=TREES)
print("     ok=%s node_type=%s slot=%s bytes_changed=%s"
      % (rep.get("ok"), rep.get("node_type"), rep.get("button_slot"),
         rep.get("bytes_changed")))
for e in rep.get("edits", []):
    print("        %s" % e)
check("it succeeded", rep.get("ok") is True, "%s" % rep.get("reason"))
check("it chose slot 4 -- the shipped RegionalUnit convention, and what v5 used",
      rep.get("button_slot") == 4, "got %s" % rep.get("button_slot"))
check("the donor's Node Type was found despite the target having no row",
      rep.get("node_type") == "RegionalUnit", "got %s" % rep.get("node_type"))
check("exactly 1 byte changed (the button; EnablingResearch is deliberately not written)",
      rep.get("bytes_changed") == 1, "got %s" % rep.get("bytes_changed"))
check("the base EnablingResearch was -1", rep["enabling_research"]["was"] == -1)
check("and the module reports it as NOT written",
      rep["enabling_research"].get("written") is False
      and rep["enabling_research"].get("now") == rep["enabling_research"]["was"],
      str(rep.get("enabling_research")))
check("the button was 1 before", rep["button"]["was"] == 1)

print()
print("C  the result parses, and says what v5 said")
with contextlib.redirect_stdout(io.StringIO()):
    p2 = P.Parser(out)
    p2.parse()
check("clean EOF", p2.r.pos == len(out), "%s of %s" % (p2.r.pos, len(out)))
_c3, _, _gv3, _t3 = L.locate(out, parser=p2)
b3 = next(c for c in _c3 if c["name"] == "British")
u3 = next(u for u in b3["units"] if u["id"] == UNIT)
print("     British unit %d button_id = %s" % (UNIT, u3["train_locations"][0]["button_id"]))
check("the button slot is 4", u3["train_locations"][0]["button_id"] == 4)
_e, _ev = DG.connection_offset(out, gv, UNIT)
print("     EnablingResearch = %s" % _ev)
# ★ NOT `== TECH`.  The confirmed recipe (dsh test v7) wrote no EnablingResearch
# byte, and the corpus has no example of a unit pointing at a foreign civ's private
# tech (probe_enabling_scope.py section D measured 0).  Asserting the module writes
# the anchor here would re-assert a write the game never confirmed.
check("EnablingResearch is left at the shipped value", _ev == -1, "got %s" % _ev)
# The write decision, stated as a byte fact rather than as a flag: exactly one byte of
# the serialized stream moved, and it is the button.  `rep["bytes_changed"]` already
# says 1 in section B; this re-derives it from the patched stream itself, so a module
# that started patching the connection again would fail here even if it kept reporting
# `written: False`.
_boff, _bnow = DG.button_offset(out, gv, CIV_INDEX, UNIT, BLDG)
print("     button byte at %d = %s" % (_boff, _bnow))
check("the button byte really changed on the stream", _bnow == 4, "got %s" % _bnow)
_new_cmds = [tuple(c) for c in p2.stats["effects"][rep["effect"]["index"]]["commands"]]
print("     new effect %d commands = %s" % (rep["effect"]["index"], _new_cmds))
check("the new effect ends with the enable command",
      _new_cmds[-1] == (2, UNIT, 1, -1, 0.0), str(_new_cmds))
# ★ The carry-over is checked against the SHIPPED anchor effect, read from the base
# stream -- not against a written-down tuple.  Re-pointing a tech at a fresh
# single-command effect REPLACES what that tech did; on this anchor that would
# silently delete the British faster-shepherd bonus while reporting ok=True.
_shipped_cmds = [tuple(c) for c in _p.stats["effects"][rep["effect"]["was"]]["commands"]]
print("     shipped anchor effect %s = %s" % (rep["effect"]["was"], _shipped_cmds))
check("the anchor effect was not empty (so the carry-over is observable)",
      len(_shipped_cmds) > 0, str(_shipped_cmds))
check("every command the anchor effect had survives on the new one",
      _new_cmds[:len(_shipped_cmds)] == _shipped_cmds, str(_new_cmds))
check("the anchor's effect is left intact underneath",
      [tuple(c) for c in p2.stats["effects"][rep["effect"]["was"]]["commands"]]
      == _shipped_cmds)
check("the British tech points at it",
      p2.stats["techs"][ANCHOR]["effect_id"] == rep["effect"]["index"])

print()
print("D  and how it differs from v5 -- deliberately, and in exactly two ways")
if os.path.exists(V5):
    vraw, _ = P.load_dat(V5)
    with contextlib.redirect_stdout(io.StringIO()):
        pv = P.Parser(vraw)
        pv.parse()
    _cv, _, _gvv, _tv = L.locate(vraw, parser=pv)
    bv = next(c for c in _cv if c["name"] == "British")
    uv = next(u for u in bv["units"] if u["id"] == UNIT)
    _ov, _ev2 = DG.connection_offset(vraw, gv, UNIT)
    print("     module : button=%s EnablingResearch=%s effect=%s tech->%s"
          % (u3["train_locations"][0]["button_id"], _ev,
             rep["effect"]["index"], p2.stats["techs"][ANCHOR]["effect_id"]))
    print("     dsh v5 : button=%s EnablingResearch=%s effect=%s tech->%s"
          % (uv["train_locations"][0]["button_id"], _ev2,
             pv.stats["techs"][LONGBOW_TECH]["effect_id"],
             LONGBOW_TECH))
    check("the two agree on the button slot",
          u3["train_locations"][0]["button_id"]
          == uv["train_locations"][0]["button_id"])
    # ★ v5 wrote tech 263 into the connection.  263's RequiredTechs is [102, 266],
    # but the Castle gate the user hit (m26421) came from the EFFECT's anchor, not
    # from this field -- v6 cleared the field to -1 and the Castle gate survived.
    # `dsh test v7` wrote no EnablingResearch byte at all and worked at 0:00.  So the
    # module must leave the field alone; asserting it writes the anchor here would
    # re-assert a write the game never confirmed.
    check("v5 wrote the connection, the module does not",
          _ev2 == LONGBOW_TECH and _ev == -1,
          "v5=%s module=%s" % (_ev2, _ev))
    check("and the age-gated anchor is exactly the one that needs a Castle",
          tk._tech_records()[LONGBOW_TECH].get("required_techs") == [102, 266],
          str(tk._tech_records()[LONGBOW_TECH].get("required_techs")))
    # v5 put its new effect at the END of the array.  Filtering by content alone
    # finds more than one, because the SHIPPED data already carries the same command:
    # effect 1350 belongs to tech 1350 'Champi Scout (Make avail)', the anchor the
    # game itself uses for the Incas.  So pick the highest index -- the appended one.
    _v5_new = [i for i, e in enumerate(pv.stats["effects"])
               if (2, UNIT, 1, -1, 0.0) in [tuple(c) for c in (e.get("commands") or [])]]
    print("     dsh v5's effects carrying the enable: %s  (the shipped one is the "
          "game's own tech 1350)" % _v5_new)
    check("the enable command exists in v5 and the highest index is the appended one",
          bool(_v5_new) and max(_v5_new) == len(pv.stats["effects"]) - 1,
          str(_v5_new))
    check("both effects end with the same enable command",
          _v5_new and [tuple(c) for c in pv.stats["effects"][max(_v5_new)]["commands"]][-1:]
          == [tuple(c) for c in p2.stats["effects"][rep["effect"]["index"]]["commands"]][-1:])
else:
    print("     (v5 artifact not on disk -- skipped)")

print()
print("DAT GRANT: the product module reproduces the `.dat` half the game confirmed,")
print("  and differs from `dsh test v5` in exactly the two ways the in-game reports")
print("  required: the anchor fires at 0:00 (m26421), and EnablingResearch is left")
print("  alone, as the confirmed recipe `dsh test v7` left it.  The button is a byte")
print("  patch, not convenience -- the writer's model does not carry train_locations.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
