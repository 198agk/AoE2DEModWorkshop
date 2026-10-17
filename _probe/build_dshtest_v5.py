# -*- coding: utf-8 -*-
r"""dsh test v5: move the Champi Scout to a FREE button slot (the user's hypothesis).

## The user's hypothesis (m25679), verbatim

    「我觉得可能是，你把印加的一模一样复制过来，但是按钮的位置还是一样的对吧，
      但是旧的兵营的内容还在，所以同一个按钮的位置其实有剑士和蔷琵侦察兵，
      但是剑士的按钮在上，这个就得你去查验一下了，你应该试着更换按钮位置，
      或者把原剑士给禁用掉」

## And the data confirms it

`button_id` is not a free-form number: it groups a building's units into button
CHAINs.  Measured per slot, counting only units the civilization's tree actually
grants:

    British   button 1 : 5 available  -- 74 75 77 473 567 (the militia line)
              button 2 : 3 available  -- 93 358 359 (the spear line)
              button 3 : 0 available  (only 882 Condottiero, not British)
              button 4 : 0 available  (28 units, none British)
    Incas     button 1 : 4 available  -- 2550 2552 2554 2588 (the WHOLE champi line)
              button 2 : 3 available
              button 3 : 0 ; button 4 : 0

So the Incas put the champi line in button 1 **because their militia line is
`NotAvailable` and that slot is therefore free**.  The British already have five
available units in button 1, and 2550 was given the same `button_id` -- so it is
masked.  The user is right.

## What button 4 means

Button 4 is where the game puts REGIONAL and UNIQUE units:
`751-753 Eagle`, `759/761 Huskarl`, `1699 Flemish Militia`, `2110/2111 Hoplite`,
`2384/2385 Phalangite`, `2586/2587 Temple Guard`, `2703/2704 Varangian Guard`.
That is exactly what the Champi Scout is (`Node Type: RegionalUnit`), so button 4 is
the semantically correct slot as well as a free one.

## v5 = v4 + ONE BYTE

    EDIT 7  British unit 2550's `train_location.button_id`: 1 -> 4

Everything else is v4, so the two are directly comparable: if C passes in v5 and not
v4, the button slot was the missing input.  If both fail, it was not.
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
V4 = os.path.join(HERE, "out_dshtest_v4")
OUT = os.path.join(HERE, "out_dshtest_v5")
TITLE = TN.name_for(5, "村民血量1000 + 不列颠可造蔷琵侦察兵（按钮槽改到空槽4）")
DESC = TN.description_for(
    5,
    "在 v4 基础上只改一个字节：不列颠 unit 2550 的 train_location.button_id 从 1 改成 4",
    "黑暗时代·不列颠兵营里有没有蔷琵侦察兵",
    extra_lines=[
        "原因：button 1 在不列颠已被剑士线占满（5个可用），2550 被盖住；"
        "button 4 在不列颠是空槽，且是游戏放区域单位的地方",
        "对照A：给村民派活后血量应仍为1000",
        "对照B：城堡时代·不列颠城堡 → 长弓兵是否还在",
    ])
UNIT = 2550
CIV = "British"
NEW_SLOT = 4
VERSION = 5
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


if "AoE2DE_s.exe" in __import__("subprocess").run(
        ["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
        capture_output=True, text=True).stdout:
    print("REFUSING: close the game first.")
    sys.exit(1)
print("game running: False")

print()
print("A  read v4's .dat and find the British 2550 button byte")
src = os.path.join(V4, "resources", "_common", "dat", "empires2_x2_p1.dat")
raw, how = P.load_dat(src)
with contextlib.redirect_stdout(io.StringIO()):
    pr = P.Parser(raw)
    pr.parse()
gv = pr.r.gv
# NOT `pr.stats["civs"]`: that is the PARSER's own reduced model, which keeps only
# `class/hit_points/id/name/task_swap_group/type` per unit -- an earlier draft read
# `u["train_locations"]` from it and died with `KeyError: 'train_locations'`.
# `L.locate()` is the full model the product uses, and it records `_off_train_time`
# per train location, which is what a byte patch needs.
_civs, _cs, gv, _tail = L.locate(raw, parser=pr)
_brit = next(c for c in _civs if c["name"] == CIV)
_o = None
for u in _brit["units"]:
    if u["id"] == UNIT:
        _o = u["train_locations"][0]["_off_train_time"]
        break
assert _o is not None, "the British must have a record for %d" % UNIT
_tt, _uid = struct.unpack_from("<hh", raw, _o)
_b0 = raw[_o + 4]
print("     train_location at %d: TrainTime=%d UnitID=%d ButtonID=%d"
      % (_o, _tt, _uid, _b0))
check("the record trains at the Barracks (12)", _uid == 12)
check("its ButtonID is currently 1 (the slot the militia line occupies)",
      _b0 == 1, "got %d" % _b0)

print()
print("B  patch the single byte")
patched = bytearray(raw)
patched[_o + 4] = NEW_SLOT
patched = bytes(patched)
_d = [i for i in range(len(raw)) if raw[i] != patched[i]]
print("     ButtonID %d -> %d ; bytes changed: %d at %s"
      % (_b0, NEW_SLOT, len(_d), _d))
check("exactly one byte changed, at the button field", _d == [_o + 4],
      "%s vs [%d]" % (_d, _o + 4))

print()
print("C  re-parse with the unmodified parser and confirm BOTH the patch and v4")
with contextlib.redirect_stdout(io.StringIO()):
    p2 = P.Parser(patched)
    p2.parse()
print("     consumed %d of %d; clean EOF: %s"
      % (p2.r.pos, len(patched), p2.r.pos == len(patched)))
check("clean EOF", p2.r.pos == len(patched))
_c2, _cs2, _gv2, _tl2 = L.locate(patched, parser=p2)
_b2 = next(c for c in _c2 if c["name"] == CIV)
_u2 = next(u for u in _b2["units"] if u["id"] == UNIT)
print("     British unit %d button_id now %s"
      % (UNIT, _u2["train_locations"][0]["button_id"]))
check("the new slot took", _u2["train_locations"][0]["button_id"] == NEW_SLOT)
check("v4's effect is still there",
      [tuple(c) for c in p2.stats["effects"][1500]["commands"]]
      == [(2, 8, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)])
check("tech 263 still points at it", p2.stats["techs"][263]["effect_id"] == 1500)
_hp = sorted({x.get("hit_points") for c in p2.stats["civs"]
              for x in (c.get("units") or []) if x.get("id") == 83})
check("villagers still 1000 hp %s" % _hp, _hp == [1000])

print()
print("D  and the slot really is free for the British")
trees = CT.load_trees(GAME)
_tr = trees["BRITONS"]
_slots = {}
for x in _b2["units"]:
    for tl in (x.get("train_locations") or []):
        if tl.get("unit_id") == 12:
            row = CT.row_for(_tr, x["id"], CT.UNIT_USE_TYPES)
            st = (row or {}).get("Node Status")
            _slots.setdefault(tl.get("button_id"), []).append((x["id"], st))
for b in sorted(_slots):
    av = [(i, s) for i, s in _slots[b]
          if s in ("ResearchedCompleted", "ResearchRequired")]
    print("     button %-3s: %2d units, %d available %s"
          % (b, len(_slots[b]), len(av), av if len(av) <= 8 else ""))
check("button %d has no other unit available to the British" % NEW_SLOT,
      not [i for i, s in _slots.get(NEW_SLOT, [])
           if s in ("ResearchedCompleted", "ResearchRequired") and i != UNIT])

print()
print("E  emit: v4's JSON payloads + the patched .dat")
info = {"Author": "dsh", "CacheStatus": 0, "Description": DESC, "Title": TITLE}
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
shutil.copytree(V4, OUT)
os.makedirs(os.path.join(OUT, "resources", "_common", "dat"), exist_ok=True)
with open(os.path.join(OUT, "resources", "_common", "dat",
                       "empires2_x2_p1.dat"), "wb") as fh:
    import zlib
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
print("DSH TEST V5 READY:", OUT)
print("  与 v4 的唯一差别：不列颠 unit 2550 的按钮槽 1 → 4（空槽）")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
