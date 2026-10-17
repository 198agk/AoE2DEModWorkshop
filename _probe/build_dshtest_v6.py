# -*- coding: utf-8 -*-
r"""dsh test v6: v5 minus the EnablingResearch change -- does it stay working, and
does it come back in the DARK AGE?

## What v5 proved (user m25909)

    「A和B没问题，C的情况是在造出城堡后，兵营里就出现了蔷琵侦察兵」

C PASSED for the first time in 70 rounds.  Two things came out of it:

  1. the recipe works (5 layers), and
  2. **the unit appears only after a Castle is built** -- a side effect.

## Why the side effect, measured

v5 points the unit's `EnablingResearch` at `tech 263 'Longbow (make avail)'`, whose
associated unit is the Longbowman (`Age ID = 3`, Castle).  The Incas -- who get the
Champi Scout in the Dark Age -- have `EnablingResearch = -1` and reach it through the
tree row's `Trigger Tech ID = 1350` instead.

So the ONE difference between "Dark Age" and "Castle Age" availability is
`EnablingResearch`.  v6 removes it, which asks two questions at once:

  * is layer 3 (`EnablingResearch`) needed at all now that the button slot is fixed?
  * does dropping it restore the Dark Age?

    v6 PASS at Dark Age  -> layer 3 was never needed, and the gate is fixed
    v6 PASS at Castle    -> layer 3 is not the cause of the gate
    v6 FAIL              -> layer 3 IS needed, and its tech is what gates the age
"""
import contextlib
import io
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import testmod_name as TN                                   # noqa: E402

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
V5 = os.path.join(HERE, "out_dshtest_v5")
OUT = os.path.join(HERE, "out_dshtest_v6")
TITLE = TN.name_for(6, "村民血量1000 + 不列颠可造蔷琵侦察兵（黑暗时代·去掉EnablingResearch）")
DESC = TN.description_for(
    6,
    "在 v5（已实现可用）基础上，只把 unit 2550 的 EnablingResearch 从 263 改回 -1"
    "（即印加原本的样子）",
    "黑暗时代·不列颠兵营里有没有蔷琵侦察兵（v5 要等到建了城堡才出现）",
    extra_lines=[
        "v5 证实 5 层配方可用；v6 问两件事：第3层到底需不需要、年代门是不是它造成的",
        "对照A：村民派活后血量应仍为1000",
        "对照B：城堡时代·不列颠城堡 → 长弓兵是否还在",
    ])
UNIT = 2550
CIV = "British"
VERSION = 6
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def enabling_offset(raw, gv_, want):
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv_)
    r.pos = stage[1] + 7 * 4
    na, nb = r.u8(), r.u8()
    nu = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(na):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(nb):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    for _ in range(nu):
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
        if uid == want:
            return o, en
    raise SystemExit("unit %d has no connection" % want)


if "AoE2DE_s.exe" in __import__("subprocess").run(
        ["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
        capture_output=True, text=True).stdout:
    print("REFUSING: close the game first.")
    sys.exit(1)
print("game running: False")

print()
print("A  read v5 and confirm the state we are changing away from")
src = os.path.join(V5, "resources", "_common", "dat", "empires2_x2_p1.dat")
raw, how = P.load_dat(src)
with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(raw)
    _p.parse()
gv = _p.r.gv
_o, _v = enabling_offset(raw, gv, UNIT)
print("     unit %d EnablingResearch = %s (at %d)" % (UNIT, _v, _o))
check("v5 has it pointing at a tech (the thing v6 removes)", _v >= 0,
      "value=%s" % _v)
_civs, _cs, _gv, _tail = L.locate(raw, parser=_p)
_brit = next(c for c in _civs if c["name"] == CIV)
_u = next(u for u in _brit["units"] if u["id"] == UNIT)
print("     unit %d button_id = %s (the v5 fix)"
      % (UNIT, _u["train_locations"][0]["button_id"]))
check("v5 already has the free button slot", _u["train_locations"][0]["button_id"] == 4)

print()
print("B  patch EnablingResearch back to -1 (one i32)")
patched = bytearray(raw)
struct.pack_into("<i", patched, _o, -1)
patched = bytes(patched)
_d = [i for i in range(len(raw)) if raw[i] != patched[i]]
print("     EnablingResearch %s -> -1 ; bytes changed: %d at %s" % (_v, len(_d), _d))
check("exactly 4 bytes changed", len(_d) == 4, "%s" % _d)

print()
print("C  re-parse and confirm the whole recipe is otherwise intact")
with contextlib.redirect_stdout(io.StringIO()):
    p2 = P.Parser(patched)
    p2.parse()
print("     consumed %d of %d; clean EOF: %s"
      % (p2.r.pos, len(patched), p2.r.pos == len(patched)))
check("clean EOF", p2.r.pos == len(patched))
_o2, _v2 = enabling_offset(patched, gv, UNIT)
print("     EnablingResearch now = %s" % _v2)
check("it is -1 now", _v2 == -1)
_c2, _cs2, _g2, _t2 = L.locate(patched, parser=p2)
_b2 = next(c for c in _c2 if c["name"] == CIV)
_u2 = next(u for u in _b2["units"] if u["id"] == UNIT)
print("     unit %d button_id still = %s" % (UNIT, _u2["train_locations"][0]["button_id"]))
check("the free button slot is untouched", _u2["train_locations"][0]["button_id"] == 4)
check("the effect is still there",
      [tuple(c) for c in p2.stats["effects"][1500]["commands"]]
      == [(2, 8, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)])
check("tech 263 still points at it", p2.stats["techs"][263]["effect_id"] == 1500)
_hp = sorted({x.get("hit_points") for c in p2.stats["civs"]
              for x in (c.get("units") or []) if x.get("id") == 83})
check("villagers still 1000 hp %s" % _hp, _hp == [1000])

print()
print("D  and the tree row / panel entry are inherited unchanged")
_t = CT.load_trees(V5)
_row = CT.row_for(_t["BRITONS"], UNIT, CT.UNIT_USE_TYPES)
print("     v5 tree row: %s" % {k: _row.get(k) for k in
                                ("Node ID", "Node Status", "Age ID",
                                 "Building ID", "Trigger Tech ID")})
check("the row keeps Trigger Tech ID 1350 (the Incas' global make-avail)",
      _row.get("Trigger Tech ID") == 1350)

print()
print("E  emit (inherit v5's JSON payloads, swap the .dat)")
info = {"Author": "dsh", "CacheStatus": 0, "Description": DESC, "Title": TITLE}
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
shutil.copytree(V5, OUT)
import zlib
with open(os.path.join(OUT, "resources", "_common", "dat",
                       "empires2_x2_p1.dat"), "wb") as fh:
    c = zlib.compressobj(6, zlib.DEFLATED, -15)
    fh.write(c.compress(patched) + c.flush())
with open(os.path.join(OUT, "info.json"), "w", encoding="utf-8",
          newline="\n") as fh:
    json.dump(info, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
for root, _dd, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("     %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))
print("     备注：", DESC)

print()
print("DSH TEST V6 READY:", OUT)
print("  与 v5 的唯一差别：unit 2550 的 EnablingResearch 263 -> -1")
print("  三种结局：黑暗时代就有=第3层不需要且年代门修好；城堡才有=第3层不是年代门的原因；")
print("           完全没有了=第3层是必要的")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
