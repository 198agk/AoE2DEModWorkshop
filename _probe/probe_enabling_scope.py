# -*- coding: utf-8 -*-
r"""Does the module write a field the confirmed recipe did NOT write?

## What raised the question

`dsh test v7` is the recipe the user confirmed in game (m27131).  Its build
script (`_probe/build_dshtest_v7.py`) asserts `unit 2550 EnablingResearch = -1`
in the shipped data and only patches it if it is not -1 -- so on this target v7
wrote NO EnablingResearch byte.  Its only byte patch is the training button.

`aoe2mod.intent.datgrant.apply_grant` USED to write it unconditionally:

    struct.pack_into("<i", patched, eoff, tech_index)     # EnablingResearch <- anchor

So the module wrote 4 bytes more than the confirmed recipe.  **The write has been
removed**, and this pin asserts it stays removed while the button byte stays.

## Why the field is more dangerous than it looks

`TechTree.UnitConnection.EnablingResearch` lives on the CONNECTION.  There are far
fewer connections than unit ids, so it is a GLOBAL, PER-UNIT field -- not a
per-civilization one.  `tech_index` is a technology owned by the TARGET
civilization (383 is `civ = 1`, British).  Writing it therefore points every
civilization's copy of unit 2550 at one civ's private technology.

## What settles it: the two in-game observations

  v5 wrote EnablingResearch = 263 (British, the age-gated anchor)  -> button
     appeared, though only after a Castle (the age gate came from the effect).
  v6 cleared it to -1                                              -> no change.
  v7 left it shipped (-1) and used tech 383 for the effect         -> worked at 0:00.

So for the target civilization the field is irrelevant in both directions.  What
the corpus must then answer is whether writing it can HURT somebody else: does any
shipped unit point its EnablingResearch at a technology owned by a civilization
that is not a builder of that unit?

Run:  $env:PYTHONPATH=D:\Software\AI\帝国项目; python _probe\probe_enabling_scope.py
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
import aoe2mod.dat.parser as P                             # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.intent import datgrant as DG                  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
V7 = os.path.join(HERE, "out_dshtest_v7", "resources", "_common", "dat",
                  "empires2_x2_p1.dat")
fails = []


def check(name, ok, detail=""):
    print("  %-74s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def connections(raw, gv):
    """Every TechTree UnitConnection, keyed by unit id.

    Field order copied verbatim from the production walk in
    `aoe2mod/intent/datgrant.py:145-177` -- the same code that produced
    `enabling_research {'was': -1}` for unit 2550 in the end-to-end run.  Hand
    rolling a shorter skip yields 20 connections with garbage values: the age and
    building records are variable length, so an approximate skip desynchronises.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv)
    r.pos = stage[1] + 7 * 4
    n_ages, n_bldg = r.u8(), r.u8()
    n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(n_ages):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(n_bldg):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    out = {}
    for _ in range(n_units):
        uid = r.i32(); r.u8()
        r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); r.i32()
        r.i32()
        o = r.pos
        en = r.i32()
        out[uid] = {"offset": o, "enabling_research": en}
    return out


print("A  the shipped distribution of EnablingResearch")
tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, _tail, _how = tk._parsed
conn = connections(data, gv)
_neg = [u for u, c in conn.items() if c["enabling_research"] == -1]
_pos = sorted(u for u, c in conn.items() if c["enabling_research"] != -1)
print("     unit connections: %d   (=1 per unit id, so the field is global)")
print("     EnablingResearch == -1 : %d" % len(_neg))
print("     EnablingResearch >= 0  : %d   %s" % (len(_pos), _pos[:20]))
check("the census matches the production reader's unit count",
      len(conn) == 266, "%d connections" % len(conn))
check("unit 2550 (the confirmed target) ships as -1",
      conn[2550]["enabling_research"] == -1,
      "%r" % (conn.get(2550, {}).get("enabling_research"),))
check("v7's byte patch for 2550 was therefore a no-op, as its script asserts",
      conn[2550]["enabling_research"] == -1)
check("and -1 is the ordinary case, not an oddity",
      len(_neg) * 2 > len(conn), "%d of %d" % (len(_neg), len(conn)))

print()
print("B  what v7's artifact actually contains")
if os.path.exists(V7):
    vraw, _ = P.load_dat(V7)
    vconn = connections(vraw, gv)
    print("     v7      unit 2550 EnablingResearch = %s"
          % vconn[2550]["enabling_research"])
    print("     shipped unit 2550 EnablingResearch = %s"
          % conn[2550]["enabling_research"])
    check("v7 left it exactly as shipped -- the confirmed recipe wrote no such byte",
          vconn[2550]["enabling_research"] == conn[2550]["enabling_research"],
          "%s vs %s" % (vconn[2550]["enabling_research"],
                        conn[2550]["enabling_research"]))
else:
    print("     (v7 artifact not on disk -- skipped)")

print()
print("C  what the module does now")
techs = tk._tech_records()
idx, anchor, why = DG.pick_tech(techs, 1)                 # civ index 1 = British
_off, _was = DG.connection_offset(data, gv, 2550)
print("     pick_tech(civ 1) -> %s %r" % (idx, (anchor or {}).get("name")))
print("     connection_offset(2550) -> offset %d, shipped value %s" % (_off, _was))
print("     module source patches exactly one byte:")
with io.open(os.path.join(ROOT, "aoe2mod", "intent", "datgrant.py"),
             encoding="utf-8") as _fh:
    _src = _fh.read()
_packs = [ln.strip() for ln in _src.splitlines()
          if "struct.pack_into" in ln and not ln.strip().startswith("#")]
print("       %d struct.pack_into call(s): %s" % (len(_packs), _packs))
check("the offset this probe read is the one the module reports",
      _off == conn[2550]["offset"], "%d vs %d" % (_off, conn[2550]["offset"]))
check("the anchor is a real technology and not what the field already holds",
      idx is not None and idx != _was, "would be %s over %s" % (idx, _was))
check("the module no longer writes EnablingResearch at all",
      not any("eoff" in ln for ln in _packs),
      "still patching with eoff: %s" % _packs)
check("...while the button byte is still written (it is load-bearing)",
      any(ln.strip().startswith("patched[boff]") for ln in _src.splitlines()),
      "button patch removed too -- that would break the recipe")
check("and the report says so, rather than staying silent",
      '"written": False' in _src, "'written': False missing from the report")

print()
print("D  can that hurt a civilization other than the target?")
trees = CT.load_trees(GAME)
_offenders = []
for uid, c in conn.items():
    en = c["enabling_research"]
    if en == -1 or uid not in _pos:
        continue
    if not (0 <= en < len(techs)):
        continue
    owner = (techs[en] or {}).get("civ")
    if owner is None or owner < 0:
        continue                                            # global tech: applies to all
    tree = trees.get(CT.civ_file_stem(civs[owner].get("name")))
    if tree is None:
        continue
    if not CT.can_build(tree, uid):
        _offenders.append((uid, en, techs[en].get("name"), civs[owner].get("name")))
print("     connections whose enabling technology is owned by a civilization that")
print("     cannot build the unit -- the exact shape the removed write created:")
print("       %d  %s" % (len(_offenders), _offenders[:10]))
check("the corpus never pairs a unit with a foreign civ's private technology",
      len(_offenders) == 0, "%d precedents exist" % len(_offenders))
print("     -> every shipped civ-owned EnablingResearch belongs to a civilization")
print("        that really builds that unit, so such a pointer is a per-owner claim.")
print("        Writing British's 383 onto unit 2550 -- which Incas/Mapuche/Muisca/")
print("        Tupi build and British does not -- would be the first foreign pair.")
print("        The field is still READ, so the report can say what it holds.")

print()
if fails:
    print("ENABLING SCOPE: %d check(s) failed." % len(fails))
    for n in fails:
        print("  FAILED: %s" % n)
    sys.exit(1)
print("ENABLING SCOPE: the recipe the game confirmed writes no EnablingResearch")
print("  byte for this target, two in-game runs show the field does not gate, it is")
print("  global per unit id, and the shipped corpus has no precedent for the foreign")
print("  pairing a write would create.  The module reads it and leaves it alone.")
