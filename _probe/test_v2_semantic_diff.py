# -*- coding: utf-8 -*-
r"""Prove `dsh test v2` differs from the base `.dat` in EXACTLY the three edits.

A raw byte diff is uninformative here: adding an effect changes the stage count, which
shifts every later byte, so `253 clusters / 59,486,724 differing positions` says
nothing about whether anything ELSE was changed.  The meaningful question is semantic:

    1  a new effect 1500 exists, commands [(2,8,1),(2,2550,1)]
    2  British tech 263's effect_id points at it (was 251)
    3  every villager-family record in every civ has hit_points 1000
    4  unit 2550's EnablingResearch is 263 (was -1)
    and NOTHING ELSE differs.

"Nothing else" is checked by comparing the two parsed models field by field and
reporting every difference, so an accidental edit cannot hide behind the shift.
"""
import contextlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The artifact this file reads is built, not checked in, and on 2026-10-25 a
# workspace cleanup deleted it -- the suite then failed with KeyError/FileNotFound,
# which reads like a data bug.  Rebuild it instead of depending on a directory
# that happens to be there.
sys.path.insert(0, HERE)
from ensure_artifact import ensure as _ensure  # noqa: E402
_ensure("out_dshtest_v2", "build_dshtest_v2.py", required=None)
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.families as F                           # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
V2 = os.path.join(_ensure("out_dshtest_v2", "build_dshtest_v2.py"), "resources", "_common", "dat",
                  "empires2_x2_p1.dat")
TECH = 263
OLD_EFFECT = 251
NEW_EFFECT = 1500
UNIT = 2550
LONGBOW = 8
VILLAGER = 83
HP = 1000
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def model(path):
    raw, how = P.load_dat(path)
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    return raw, pr.stats


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
base_raw = tk._raw
with contextlib.redirect_stdout(io.StringIO()):
    bp = P.Parser(base_raw)
    bp.parse()
base = bp.stats
v2_raw, v2 = model(V2)

print("A  the two models agree on everything that is not one of the three edits")
print("     base: effects %d techs %d civs %d"
      % (len(base["effects"]), len(base["techs"]), len(base["civs"])))
print("     v2  : effects %d techs %d civs %d"
      % (len(v2["effects"]), len(v2["techs"]), len(v2["civs"])))
check("exactly ONE effect was added",
      len(v2["effects"]) == len(base["effects"]) + 1,
      "%d -> %d" % (len(base["effects"]), len(v2["effects"])))
check("no tech was added or removed",
      len(v2["techs"]) == len(base["techs"]))
check("no civ changed", len(v2["civs"]) == len(base["civs"]))

print()
print("B  every pre-existing EFFECT is untouched")
_d_eff = [i for i in range(len(base["effects"]))
          if base["effects"][i].get("commands") != v2["effects"][i].get("commands")
          or base["effects"][i].get("name") != v2["effects"][i].get("name")]
print("     pre-existing effects that differ: %d %s" % (len(_d_eff), _d_eff[:6]))
check("not one of the 1500 shipped effects was modified", not _d_eff,
      "%s" % _d_eff[:6])
print("     new effect %d: name=%r commands=%s"
      % (NEW_EFFECT, v2["effects"][NEW_EFFECT].get("name"),
         v2["effects"][NEW_EFFECT].get("commands")))
check("the new effect carries exactly the two commands",
      [tuple(c) for c in v2["effects"][NEW_EFFECT]["commands"]]
      == [(2, LONGBOW, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)],
      "%s" % v2["effects"][NEW_EFFECT]["commands"])

print()
print("C  exactly ONE tech record differs, and only in its effect_id")
_d_tech = []
for i in range(len(base["techs"])):
    b, v = base["techs"][i], v2["techs"][i]
    if b == v:
        continue
    keys = sorted({k for k in set(b) | set(v) if b.get(k) != v.get(k)})
    _d_tech.append((i, keys, {k: (b.get(k), v.get(k)) for k in keys}))
print("     techs that differ: %d" % len(_d_tech))
for i, keys, ch in _d_tech:
    print("        tech %-5s changed keys=%s  %s" % (i, keys, ch))
check("exactly one tech changed", len(_d_tech) == 1, "%s" % _d_tech)
check("it is tech 263 and only `effect_id` moved, %d -> %d"
      % (OLD_EFFECT, NEW_EFFECT),
      bool(_d_tech) and _d_tech[0][0] == TECH
      and _d_tech[0][1] == ["effect_id"]
      and _d_tech[0][2]["effect_id"] == (OLD_EFFECT, NEW_EFFECT))

print()
print("D  the villager edit covers the whole family, and nothing else in any unit")
F.warm({"civs": tk._parsed[1]}, game_root=GAME)
family = set(F.family_of(F.build_families(tk._parsed[1]), VILLAGER))
print("     family of %d: %d ids" % (VILLAGER, len(family)))
_units_diff = {}
for ci, (cb, cv) in enumerate(zip(base["civs"], v2["civs"])):
    for ub, uv in zip(cb.get("units") or [], cv.get("units") or []):
        if ub == uv:
            continue
        keys = sorted({k for k in set(ub) | set(uv) if ub.get(k) != uv.get(k)})
        _units_diff.setdefault(tuple(keys), []).append((ci, ub.get("id"),
                                                        ub.get("hit_points"),
                                                        uv.get("hit_points")))
print("     distinct changed-key sets across all unit records: %d"
      % len(_units_diff))
for keys, rows in _units_diff.items():
    ids = sorted({r[1] for r in rows})
    print("        keys=%s  records=%d  unit ids=%s" % (list(keys), len(rows), ids))
check("units differ ONLY in hit_points", list(_units_diff) == [("hit_points",)],
      "%s" % list(_units_diff))
_allrows = [r for rows in _units_diff.values() for r in rows]
_ids = sorted({r[1] for r in _allrows})
print("     changed unit ids: %d -> %s" % (len(_ids), _ids))
check("the changed ids are exactly the villager family", set(_ids) == family,
      "diff=%s" % (set(_ids) ^ family))
check("every changed record went from %s to 1000"
      % sorted({r[2] for r in _allrows}),
      all(r[3] == HP for r in _allrows)
      and sorted({r[2] for r in _allrows}) != [HP],
      "before=%s" % sorted({r[2] for r in _allrows}))

print()
print("E  and the EnablingResearch patch, read from the artifact")
def enabling(pr, raw, gv_, want):
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv_)
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
    for _ in range(n_units):
        uid = r.i32(); r.u8()
        r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); r.i32()
        r.i32()
        en = r.i32()
        if uid == want:
            return en
    return None


with contextlib.redirect_stdout(io.StringIO()):
    _pv = P.Parser(v2_raw)
    _pv.parse()
with contextlib.redirect_stdout(io.StringIO()):
    _pb = P.Parser(base_raw)
    _pb.parse()
print("     unit %d EnablingResearch: base %s -> v2 %s"
      % (UNIT, enabling(_pb, base_raw, tk._parsed[3], UNIT),
         enabling(_pv, v2_raw, tk._parsed[3], UNIT)))
check("unit 2550's EnablingResearch is now 263",
      enabling(_pv, v2_raw, tk._parsed[3], UNIT) == TECH)
check("unit 8's is untouched at 263",
      enabling(_pv, v2_raw, tk._parsed[3], LONGBOW) == TECH)
check("the base still has -1 for 2550 (so it was a real change)",
      enabling(_pb, base_raw, tk._parsed[3], UNIT) == -1)

print()
print("V2 SEMANTIC DIFF: one effect added, one tech's effect_id moved, the villager")
print("  family's hit points set to 1000, and unit 2550's EnablingResearch pointed at")
print("  tech 263 -- with every other effect, tech, unit and civ byte-identical.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
