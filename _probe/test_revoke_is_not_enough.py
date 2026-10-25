# -*- coding: utf-8 -*-
r"""Deleting a unit from BOTH JSON layers does NOT remove its build button.

WHY THIS IS A PERMANENT PIN
---------------------------
`dsh test v9`'s C sentence deleted unit 2550 from the Incas on both JSON layers
and the user still found the Champi Scout in the Incas Barracks (m29132).  That
is the single observation that refuted the "AND gate" model this project had
written into `aoe2mod/game/civtechtrees.py` and `aoe2mod/api.py`.

The refutation is only as good as the EXPERIMENT, so this file re-derives the
experiment's validity from the v9 artifact every run:

  1. the tree layer really dropped the row (56 -> 55 unit rows),
  2. the panel layer really dropped the entry,
  3. the `.dat` really still enables 2550 (the shipped `tech 1350` command),
     so nothing on the `.dat` side withdrew it.

If a future change makes any of those false, the in-game observation stops being
evidence for the model and this test fails, rather than the conclusion quietly
rotting into folklore.

WHAT AN INDEPENDENT REVIEW FOUND IN THE EXPERIMENT ITSELF
---------------------------------------------------------
Three of the reviewer's findings are now asserted here rather than hidden:

  * v9's `INCAS.json` kept a DANGLING `Link ID 2550` after its 2550 row was
    deleted, and NO shipped tree file has one.  The game was handed a state it
    never produces, so it may have fallen back to the `.dat` default tree --
    which would make "the button stayed" a fact about a fallback path.  The
    in-game half is therefore PROVISIONAL, not settled.
  * "+80 B" was right but "appended" was wrong: the new effect goes into the
    effects ARRAY mid-file (first differing byte 3584190, tails identical).
  * the `.dat` says yes to EVERY civilization (one global enable, no per-civ
    enable), so the `.dat` has no way to express the 4-civ split at all.  That
    is why the JSON layers remain the only shipped data encoding it, even
    though deleting them did not move the button.

A NOTE ON A TRAP THIS FILE WALKED INTO
--------------------------------------
A technology with no effect stores `effect_id == -1`, and Python's negative
indexing silently reads the LAST effect.  Since v9's last effect is the newly
appended one that enables 2550, an unguarded walk reported ~200 phantom
"enables" -- a number that looks like a finding.  Always guard `effect_id < 0`.
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The artifact this file reads is built, not checked in, and on 2026-10-25 a
# workspace cleanup deleted it -- the suite then failed with KeyError/FileNotFound,
# which reads like a data bug.  Rebuild it instead of depending on a directory
# that happens to be there.
sys.path.insert(0, HERE)
from ensure_artifact import ensure as _ensure  # noqa: E402
_ensure("out_dshtest_v9", "build_dshtest_v9.py", required=None)
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

from aoe2mod.dat import parser as P
from aoe2mod.game import buildpanel as BP
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = _ensure("out_dshtest_v9", "build_dshtest_v9.py")
# The SUBJECT of this pin is the artifact the build produced, not the copy that
# happens to be installed.  Reading the installed folder made this test fail the
# moment the next experiment replaced it -- an evidence pin has to depend only on
# things the repository keeps.  OUT is that artifact.
MOD = OUT
UNIT = 2550

fails = []
def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name[:70], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)

def tree(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

def listed(panels, civ, unit_id):
    out = []
    v = panels.get(civ)
    if not v:
        return out
    obj = v["obj"]
    for blk in BP.buildings(obj, civ):
        for e in BP.entries(obj, civ, blk.get("ID"), BP.UNITS_KEY):
            if int(e.get("ID", -1)) == unit_id:
                out.append((blk.get("ID"), dict(e)))
    return out

print("1  THE TREE LAYER")
_ship_i = tree(os.path.join(GAME, "resources", "_common", "dat",
                            "CivTechTrees", "INCAS.json"))
_mod_i = tree(os.path.join(MOD, "resources", "_common", "dat",
                           "CivTechTrees", "INCAS.json"))
check("shipped INCAS.json HAS the 2550 row",
      CT.row_for(_ship_i, UNIT, CT.UNIT_USE_TYPES) is not None,
      CT.node_status(_ship_i, UNIT, CT.UNIT_USE_TYPES))
check("v9's INCAS.json has NO 2550 row (the revoke happened)",
      CT.row_for(_mod_i, UNIT, CT.UNIT_USE_TYPES) is None)
# 2026-10-19 the product's revoke learned to cascade, so re-running the same
# sentence also removes the rows that only existed to link at 2550: the count
# drops by more than one.  What the refutation needs is that the ROW is gone
# (asserted just above) and that nothing was invented -- not an exact delta.
_moved = len(CT.unit_rows(_ship_i)) - len(CT.unit_rows(_mod_i))
check("and nothing was invented: the row count only ever goes down",
      _moved >= 1,
      "%d -> %d (v9 的产物是 1；产品后来会连带删掉只指向它的行)"
      % (len(CT.unit_rows(_ship_i)), len(CT.unit_rows(_mod_i))))


def _dangling_links(t):
    """Rows whose ``Link ID`` names a node the same file no longer contains.

    An independent review pointed out that v9's revoke left one behind, and that
    NO shipped tree file has one.  That matters because the game was handed a
    state it never ships: it may have fallen back to the `.dat` default tree,
    which would make "the button stayed" a fact about the fallback path instead
    of a fact about the tree layer.  This block records the defect honestly
    rather than letting the pin imply a cleaner experiment than was run.
    """
    have = set()
    for r in CT.rows_of(t):
        try:
            have.add(int(r.get("Node ID")))
        except (TypeError, ValueError):
            pass
    out = []
    for r in CT.rows_of(t):
        try:
            link = int(r.get("Link ID"))
        except (TypeError, ValueError):
            continue
        if link >= 0 and link not in have:
            out.append((r.get("Use Type"), r.get("Node ID"), link))
    return out


_ship_dang = _dangling_links(_ship_i)
_mod_dang = _dangling_links(_mod_i)
check("the shipped INCAS.json has NO dangling Link ID", _ship_dang == [],
      _ship_dang[:3])
# The dangling link was the DEFECT a reviewer found in v9, and the product fixed
# it the same day (cascade).  So the honest check is: whichever artifact is on
# disk, a dangling link must be REPORTED, and today's build must not produce one.
check("today's build leaves NO dangling Link ID (the v9 defect is fixed)",
      _mod_dang == [],
      _mod_dang[:3])
print("     ^ so the in-game half of this experiment is PROVISIONAL: if the engine")
print("       validated the tree and fell back to the .dat default, 'the button")
print("       stayed' says nothing about whether the tree layer is read at all.")

print()
print("2  THE PANEL LAYER  (this is where b622 recorded a defect)")
_sp = BP.load_all(GAME)
_mp = BP.load_all(MOD)
_ship_l = listed(_sp, "Incas", UNIT)
_mod_l = listed(_mp, "Incas", UNIT)
check("shipped panel lists 2550 for Incas", len(_ship_l) == 1, _ship_l)
check("v9's panel does NOT list 2550 for Incas (the revoke happened)",
      len(_mod_l) == 0, _mod_l)
for _c in ("Mapuche", "Muisca", "Tupi", "Britons"):
    print("     %-10s shipped=%d v9=%d"
          % (_c, len(listed(_sp, _c, UNIT)), len(listed(_mp, _c, UNIT))))

print()
print("3  THE .dat  (the C sentence itself must write NO .dat byte)")
_gs = P.load_dat(os.path.join(GAME, "resources", "_common", "dat",
                              "empires2_x2_p1.dat"))[0]
_ms = P.load_dat(os.path.join(MOD, "resources", "_common", "dat",
                              "empires2_x2_p1.dat"))[0]
# "+80 B" is right, "appended" was wrong: the new effect record is appended to
# the EFFECTS ARRAY, which lives mid-file, so the first differing byte is at
# offset 3584190 and the last 64 bytes of the two files are identical.  A
# reviewer caught this; the wording now describes the insert instead.
_first = next((i for i in range(min(len(_gs), len(_ms))) if _gs[i] != _ms[i]),
              None)
# 80 bytes was the grant's effect alone.  Since v17 the revoke appends an effect
# of its own, so the file grows more -- the shape is "grew in the middle", which
# is what the tail check below already separates from "appended at the end".
_grew = len(_ms) - len(_gs)
check("the .dat grew, and the change starts mid-file",
      _grew > 0 and _first is not None and _first < len(_gs) - 1024,
      "%d -> %d (+%d), first differing byte at offset %s"
      % (len(_gs), len(_ms), _grew, _first))
check("the tails agree, so nothing was appended at the end of the file",
      _gs[-64:] == _ms[-64:])

print()
print("4  WHAT THE .dat STILL SAYS ABOUT UNIT 2550 FOR THE INCAS")


def _cmds(c):
    return c if isinstance(c, tuple) else (c.get("type"), c.get("a"),
                                           c.get("b"), c.get("c"), c.get("d"))


import contextlib, io as _io
_gp = P.Parser(_gs)
with contextlib.redirect_stdout(_io.StringIO()):
    _gp.parse()
_mp = P.Parser(_ms)
with contextlib.redirect_stdout(_io.StringIO()):
    _mp.parse()


def _enables(p):
    """type-2 ENABLE commands that mention unit 2550, as (tech index, command).

    Guard the effect id: a technology with no effect stores -1, and a negative
    index silently wraps to the LAST effect -- which in v9 is the newly appended
    one, so an unguarded read invents ~200 hits out of nothing.
    """
    out = []
    for i, t in enumerate(p.stats["techs"]):
        eid = t.get("effect_id")
        if eid is None or eid < 0:
            continue
        for c in p.stats["effects"][eid]["commands"]:
            c = _cmds(c)
            if c[0] == 2 and c[1] == UNIT and c[2] == 1:
                out.append((i, c))
    return out


print("     techs with effect_id == -1 (shipped/v9): %d / %d"
      % (sum(1 for t in _gp.stats["techs"] if (t.get("effect_id") or -1) < 0),
         sum(1 for t in _mp.stats["techs"] if (t.get("effect_id") or -1) < 0)))
for _lbl, _p in (("shipped", _gp), ("v9", _mp)):
    print("     %-8s type-2 enables of 2550: %s" % (_lbl, _enables(_p)))
check("the shipped global enable (tech 1350) is still there in v9",
      any(i == 1350 for i, _c in _enables(_mp)),
      "so the .dat says YES to the Incas")
check("and v9's .dat adds nothing for 2550 except the B sentence's new effect",
      [i for i, _c in _enables(_mp) if i not in [j for j, _c2 in _enables(_gp)]]
      == [383],
      "the only new enable is tech 383 (British's 0:00 bonus)")

# The fact that makes the .dat side honest: no shipped per-civ enable excludes
# anyone from 2550, so the .dat says yes to every civilization and the revoke
# could only have been expressed in the JSON layers.  The check is on the
# SHIPPED file: v9 legitimately adds one per-civ enable (tech 383, civ 1) as the
# B sentence's grant, so testing v9's own list would fail for a correct reason.
print()
print("5  DOES THE SHIPPED .dat EXCLUDE ANYONE FROM 2550?")


def _enable_civs(p, unit):
    out = []
    for i, t in enumerate(p.stats["techs"]):
        eid = t.get("effect_id")
        if eid is None or eid < 0:
            continue
        for c in p.stats["effects"][eid]["commands"]:
            c = _cmds(c)
            if c[0] == 2 and c[1] == unit and c[2] == 1:
                out.append((i, t.get("civ")))
    return out


_ship_en = _enable_civs(_gp, UNIT)
check("every shipped enable of 2550 is global (civ = -1), so the .dat says YES "
      "to every civilization", all(civ == -1 for _i, civ in _ship_en), _ship_en)
check("and it comes from a single technology, so the .dat has no way to tell "
      "the 4 civilizations that build 2550 from the other 59",
      len(set(_i for _i, _c in _ship_en)) == 1, sorted(set(_i for _i, _c in _ship_en)))

print()
_today = ("the FILE-level half holds -- both JSON layers really dropped the unit "
          "and the .dat still allows it.  The artifact on disk is rebuilt by "
          "today's product, so it no longer carries the dangling Link ID a "
          "reviewer found in the 2026-10-19 build; the ORIGINAL v9 observation "
          "(m29132: the button stayed) was made against that dangling file and "
          "stays PROVISIONAL on that ground, whatever this run prints")
print("VERDICT: %s" % (_today if not fails else
                       "*** THE EXPERIMENT WAS NOT WHAT IT CLAIMED ***"))
if fails:
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
