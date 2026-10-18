# -*- coding: utf-8 -*-
r"""PIN: which `.dat` edits the writer can do safely -- measured, not assumed.

smoke8 needed to extend a shipped effect with one more command, and THREE routes were
tried.  Two of them fail in ways that are silent until you measure the output, so the
comparison is pinned here rather than left in a build script.

    route 1  ADD a command to an existing effect (in-place length change)
             -> delta +3,061,463 bytes, 34,740 model-vs-raw mismatches, and the
                re-parse dies with `struct.error: bad char in struct format`.
                `write_effect` writes `len(commands)` records with no notion of the
                original byte span, so anything after the record shifts and the
                verbatim replay desynchronises.
    route 2  APPEND a new Tech carrying the command
             -> serialises cleanly, BUT `write_tech`'s `_new` branch hardcodes the
                three `ResearchResourceCost` slots as zero (`writer.py:739`), while
                every shipped 'make avail' tech has `costs[].type == -1`
                (`_probe/probe_inplace_target.py`: 901 of 1510 techs use `(-1,-1,-1)`).
                The model dict cannot override it, so the record deviates from the
                pattern it imitates.
    route 3  APPEND a new Effect and repoint an EXISTING civ-owned tech's `effect_id`
             -> delta +40, exactly 2 mismatches (the effect count and that i16),
                clean re-parse.  CHOSEN.

Route 3 also keeps the shipped tech's bytes untouched, so no scaffolding is
synthesised at all.

And the subject it edits is the strongest one available: `tech 263
'Longbow (make avail)'`, `civ == 1` (British), whose effect 251 is
`[(type 2, a=8, b=1)]` -- unit 8's `EnablingResearch` is 263, and the British are the
only civ that can build Longbowmen.  So it is a per-civ unit gate the engine
demonstrably honours, which is exactly the mechanism smoke8 reuses.

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_dat_edit_routes.py
"""
import contextlib
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
import aoe2mod.dat.writer as W                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TECH = 263          # British '(Longbow) make avail'
UNIT = 2550         # Champi Scout
LONGBOW = 8
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
techs0 = L.locate_techs(data, tail, gv)
effs0 = L.locate_effects(data)[0]


def _fresh():
    with contextlib.redirect_stdout(io.StringIO()):
        p = P.Parser(data)
        p.parse()
    return p.stats


def _ser(mutate):
    st = _fresh()
    mutate(st)
    out, rep = W.serialize_dat(st, raw=data, gv=gv)
    return out, rep, st


def _reparses(out):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            p = P.Parser(out)
            p.parse()
        return p.r.pos == len(out), p.r.pos
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, exc)


print("A  the subject is the per-civ gate the engine already honours")
t263 = techs0[TECH]
e251 = next(r for r in effs0 if r.get("index") == 251)
print("     tech %d: civ=%s (%s) name=%r effect_id=%s"
      % (TECH, t263.get("civ"), names[t263.get("civ")], t263.get("name"),
         t263.get("effect_id")))
print("     effect 251 commands: %s"
      % [(c.get("type"), c.get("a"), c.get("b")) for c in e251.get("commands")])
check("the tech belongs to the British", t263.get("civ") == 1)
check("its effect enables the Longbowman (unit 8)",
      [c.get("a") for c in e251.get("commands")] == [LONGBOW])

print()
print("B  route 1 (in-place length change) is UNSAFE -- measured")
def r1(st):
    st["effects"][251]["commands"] = list(st["effects"][251]["commands"]) + [
        (2, UNIT, 1, -1, 0.0)]
o1, rep1, _ = _ser(r1)
ok1, why1 = _reparses(o1)
print("     bytes %d (delta %+d), mismatches %d, reparse clean: %s"
      % (len(o1), len(o1) - len(data), rep1["model_vs_original_mismatches"], ok1))
if not ok1:
    print("     reparse failure: %s" % str(why1)[:90])
check("route 1 changes far more bytes than the edit warrants",
      abs(len(o1) - len(data)) > 1000, "delta=%+d" % (len(o1) - len(data)))
check("and it does NOT re-parse", not ok1)

print()
print("C  route 2 (append a tech) serialises, but deviates on `costs`")
def r2(st):
    idx = len(st["effects"])
    st["effects"].append({"name": "pin-route2",
                          "commands": [(2, LONGBOW, 1, -1, 0.0),
                                       (2, UNIT, 1, -1, 0.0)],
                          "_new": True})
    st["effect_count"] = len(st["effects"])
    st["techs"].append({"civ": 1, "effect_id": idx, "type": 0, "icon_id": -1,
                        "name": "pin-route2-tech",
                        "research_locations": [(-1, 0, 0, -1)],
                        "_new": True})
    st["tech_count"] = len(st["techs"])
o2, rep2, _ = _ser(r2)
ok2, _why2 = _reparses(o2)
print("     bytes %d (delta %+d), reparse clean: %s"
      % (len(o2), len(o2) - len(data), ok2))
check("route 2 re-parses cleanly", ok2)
# read back what costs the appended tech actually got
with contextlib.redirect_stdout(io.StringIO()):
    _p2 = P.Parser(o2)
    _p2.parse()
_o_civs, _o_cs, _o_gv, _o_tail = L.locate(o2, parser=_p2)
_o_techs = L.locate_techs(o2, _o_tail, _o_gv)
_new = _o_techs[-1]
_types = [c.get("type") for c in (_new.get("costs") or [])]
print("     the appended tech's costs types: %s" % _types)
print("     a shipped 'make avail' tech's costs types: %s"
      % [c.get("type") for c in (t263.get("costs") or [])])
check("route 2's tech deviates: costs[].type is 0 where shipped ones use -1",
      bool(_types) and all(x == 0 for x in _types)
      and all(c.get("type") == -1 for c in (t263.get("costs") or [])))

print()
print("D  route 3 (append an effect, repoint the tech) is SAFE -- and is what smoke8 uses")
def r3(st):
    idx = len(st["effects"])
    st["effects"].append({"name": "pin-route3",
                          "commands": [(2, LONGBOW, 1, -1, 0.0),
                                       (2, UNIT, 1, -1, 0.0)],
                          "_new": True})
    st["effect_count"] = len(st["effects"])
    st["techs"][TECH]["effect_id"] = idx
o3, rep3, _ = _ser(r3)
ok3, _why3 = _reparses(o3)
print("     bytes %d (delta %+d), mismatches %d, reparse clean: %s"
      % (len(o3), len(o3) - len(data), rep3["model_vs_original_mismatches"], ok3))
check("route 3's delta is tiny (an effect + one i16)", 0 < len(o3) - len(data) < 200,
      "delta=%+d" % (len(o3) - len(data)))
check("route 3 re-parses cleanly", ok3)
check("route 3 touches only 2 field groups", rep3["model_vs_original_mismatches"] == 2,
      "mismatches=%s" % rep3["model_vs_original_mismatches"])
with contextlib.redirect_stdout(io.StringIO()):
    _p3 = P.Parser(o3)
    _p3.parse()
_o3c, _o3cs, _o3gv, _o3tail = L.locate(o3, parser=_p3)
_o3techs = L.locate_techs(o3, _o3tail, _o3gv)
_o3effs = L.locate_effects(o3)[0]
_newidx = _o3techs[TECH]["effect_id"]
_newcmd = next(r for r in _o3effs if r.get("index") == _newidx)
print("     tech %d now points at effect %s, whose commands are %s"
      % (TECH, _newidx, [(c.get("type"), c.get("a"), c.get("b"))
                         for c in _newcmd.get("commands")]))
check("the tech points at the new effect", _newidx != 251)
check("both the shipped Longbow enable and the new grant are present",
      sorted(c.get("a") for c in _newcmd.get("commands")) == sorted([LONGBOW, UNIT]))
check("the shipped effect 251 is left untouched",
      [c.get("a") for c in next(r for r in _o3effs
                                if r.get("index") == 251).get("commands")]
      == [LONGBOW])

print()
print("DAT EDIT ROUTES: appending an effect and repointing a civ-owned tech is the")
print("  only one of the three that changes ~40 bytes and still re-parses; an")
print("  in-place length change desynchronises the verbatim replay, and an appended")
print("  TECH cannot match the shipped `costs` pattern.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
