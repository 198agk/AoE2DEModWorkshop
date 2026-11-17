# -*- coding: utf-8 -*-
r"""dsh test v7: put the enable on a tech that fires at 0:00, not at the Castle.

## What v5/v6 got wrong

v5 emitted a British Barracks button for the Champi Scout, and the user confirmed
it -- but only AFTER a Castle was built (m26421):

    「A和B依旧没问题，C还是必须建了城堡后，兵营才会出现蔷琵侦察兵的按钮」

v5 hung the enable command on `tech 263 'Longbow (make avail)'`.  v6 then cleared
unit 2550's `EnablingResearch`, which changed nothing.  Neither attempt asked WHY
tech 263 fires late.  `RequiredTechs` -- a field `walk_tech` reads and THROWS AWAY
-- answers it:

    tech 1350 'Champi Scout (Make avail)'  RequiredTechs [104]       works at 0:00
    tech 263  'Longbow (make avail)'       RequiredTechs [102, 266]  waits for Castle
    tech 381  'C-Bonus, 1/2 TCs'           RequiredTechs [102]       Castle
    tech 382  'C-Bonus, +1 Archer range'   RequiredTechs [102]       Castle
    tech 383  'C-Bonus, +25% Shepherd'     RequiredTechs []          fires at 0:00
    tech 403  'C-Bonus, archer range +1'   RequiredTechs [103]       Imperial

Tech 1350 requires tech 104 (Dark Age) and that is why the Incas get the unit on
an empty map.  So the anchor must have `RequiredTechs == []`, and among the five
British-owned, location-less techs only **383** qualifies.  Its effect (381) has
two commands and is referenced by no other tech, so appending the enable there
neither loses the shepherds' bonus nor leaks the unit to another civilization.

## v7 = a fresh build off the SHIPPED dat

    EDIT 1  villager family (27 ids) -> hit_points 1000                    [CONTROL A]
    EDIT 2  effect 381 gains (2, 2550, 1, -1, 0.0)  <- tech 383, fires at 0:00
    EDIT 3  British unit 2550's train_location.button_id 1 -> 4            [free slot]
    EDIT 4  CivTechTrees/BRITONS.json : a row for 2550, ResearchedCompleted
    EDIT 5  futuravailableunits.json  : the Britons Barracks gains 2550

tech 263 is left ALONE (it keeps effect 251), so CONTROL B is the shipped
behaviour: Castle Age -> British Castle -> Longbowman still there.
"""
import contextlib
import _gamepaths as GP
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
import aoe2mod.dat.families as F                           # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.writer as W                             # noqa: E402
import aoe2mod.intent.availability as AV                   # noqa: E402
from aoe2mod.dat import locate as L                        # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = GP.GAME
OUT = os.path.join(HERE, "out_dshtest_v7")
VERSION = 7
UNIT = 2550
CIV = "British"
TREE_KEY = "BRITONS"
ANCHOR_TECH = 383
ANCHOR_EFFECT = 381
LONGBOW_TECH = 263
LONGBOW_EFFECT = 251
HP = 1000
NEW_SLOT = 4
TITLE = TN.name_for(VERSION, "村民血量1000 + 不列颠黑暗时代可造蔷琵侦察兵")
DESC = TN.description_for(
    VERSION,
    "把「启用蔷琵侦察兵」的效果从不列颠的城堡科技 263 改挂到科技 383"
    "（RequiredTechs 为空 = 开局即生效），并保留按钮槽 4 与树/面板的两半",
    "开局即刻·不列颠兵营 → 蔷琵侦察兵（不用建城堡）",
    extra_lines=[
        "起因：v5/v6 的按钮要等到建了城堡才出现（用户 m26421 实测）",
        "根因：RequiredTechs —— 263 需要 [102]（城堡时代），383 需要 []（开局）",
        "对照A：给村民派活后血量应仍为1000",
        "对照B：城堡时代·不列颠城堡 → 长弓兵是否还在（263 未动，应仍在）",
    ])
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def enabling(pr, raw, gv_, want):
    """`EnablingResearch` of `want`, plus its byte offset."""
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
        o = r.pos
        en = r.i32()
        if uid == want:
            return o, en
    raise SystemExit("unit %d has no TechTree connection" % want)


def required_techs(raw, start, gv_, index):
    """`RequiredTechs` of one tech record, read off the raw head.

    Tech records are variable length at this game version (ResearchLocations is an
    explicit array), so walking with a fixed stride drifts.  Rewind over the
    product's own walker instead.
    """
    r = L.Orec(raw, start, gv=gv_)
    n = r.i16()
    for i in range(n):
        rec_start = r.o
        req = list(r.i16_array(6))
        if i == index:
            return req
        # Rewind and let the product's own walker advance the cursor: records are
        # variable length here, so stepping by the head's width would drift.
        r.o = rec_start
        L.walk_tech(r)
    raise SystemExit("tech %d not found" % index)


def commands_of(stats, tech_id):
    eid = stats["techs"][tech_id].get("effect_id")
    out = []
    for c in (stats["effects"][eid].get("commands") or []):
        out.append(tuple(c) if not isinstance(c, dict)
                   else (c["type"], c["a"], c["b"], c["c"], c["d"]))
    return eid, out


if "AoE2DE_s.exe" in __import__("subprocess").run(
        ["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
        capture_output=True, text=True).stdout:
    print("REFUSING: close the game first.")
    sys.exit(1)
print("game running: False")

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
assert names[1] == CIV, names[1]

with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
stats = _p.stats
_tech_stage = [t for t in _p.stage_offsets if t[0].startswith("9 Techs")][0]
_req_anchor = required_techs(data, _tech_stage[1], gv, ANCHOR_TECH)
_req_longbow = required_techs(data, _tech_stage[1], gv, LONGBOW_TECH)

print()
print("A  the anchor, read from the shipped bytes")
print("     tech %-5d RequiredTechs = %s   <- must be empty (= fires at 0:00)"
      % (ANCHOR_TECH, [x for x in _req_anchor if x != -1]))
print("     tech %-5d RequiredTechs = %s   <- the v5/v6 anchor (Castle Age)"
      % (LONGBOW_TECH, [x for x in _req_longbow if x != -1]))
check("the anchor has no required techs", [x for x in _req_anchor if x != -1] == [])
check("the v5/v6 anchor is gated (so this is a real difference)",
      [x for x in _req_longbow if x != -1] != [])
_eid_anchor, _cmds_anchor = commands_of(stats, ANCHOR_TECH)
print("     tech %d -> effect %d : %s" % (ANCHOR_TECH, _eid_anchor, _cmds_anchor))
check("the anchor's effect carries no type-2 command yet",
      not [c for c in _cmds_anchor if c[0] == 2])
_by_eff = {}
for i, rec in enumerate(stats["techs"]):
    _by_eff.setdefault(rec.get("effect_id"), []).append(i)
_sharers = [j for j in _by_eff.get(_eid_anchor, []) if j != ANCHOR_TECH]
check("the anchor's effect is shared with no other tech", not _sharers, str(_sharers))
_o2550, _v2550 = enabling(_p, data, gv, UNIT)
print("     unit %s EnablingResearch = %s (shipped; matches Incas)" % (UNIT, _v2550))
check("unit %s needs no EnablingResearch change" % UNIT, _v2550 == -1)

print()
print("B  the .dat edits")
# A NEW effect record, not an appended command.  `write_effect` can only grow a
# record through its `_new` path (which freezes the raw cursor for the duration);
# mutating an existing effect's command list makes the writer's model and raw
# cursors disagree and the output is unrecoverable -- measured: the re-parse died
# in `read_bird` with `struct.error: bad char in struct format`.
stats["effects"].append({
    "name": "dsh test v7 Shepherd + Champi Scout",
    "commands": list(_cmds_anchor) + [(2, UNIT, 1, -1, 0.0)],
    "_new": True,
})
stats["effect_count"] = len(stats["effects"])
_new_idx = len(stats["effects"]) - 1
stats["techs"][ANCHOR_TECH]["effect_id"] = _new_idx
print("     EDIT 2  new effect %d = %s ; tech %d -> effect %d"
      % (_new_idx, stats["effects"][_new_idx]["commands"][:2] +
         [(2, UNIT, 1, -1, 0.0)], ANCHOR_TECH, _new_idx))
check("the anchor's original commands were carried over",
      list(stats["effects"][_new_idx]["commands"])[:len(_cmds_anchor)]
      == list(_cmds_anchor))
check("effect %d itself is left alone" % _eid_anchor,
      [tuple(c) if not isinstance(c, dict)
       else (c["type"], c["a"], c["b"], c["c"], c["d"])
       for c in stats["effects"][_eid_anchor]["commands"]] == _cmds_anchor)

F.warm({"civs": civs}, game_root=GAME)
family = sorted(F.family_of(F.build_families(civs), 83))
touched = 0
for c in stats["civs"]:
    for u in c.get("units") or []:
        if u.get("id") in family:
            if u.get("hit_points") != HP:
                touched += 1
            u["hit_points"] = HP
print("     EDIT 1  villager family (%d ids) -> %d ; records set: %d"
      % (len(family), HP, touched))
check("every civilization's villager records were set",
      touched == len(family) * len(civs))

out, rep = W.serialize_dat(stats, raw=data, gv=gv)
with contextlib.redirect_stdout(io.StringIO()):
    _p2 = P.Parser(out)
    _p2.parse()
check("the writer's output re-parses to a clean EOF", _p2.r.pos == len(out),
      "%d vs %d" % (_p2.r.pos, len(out)))
_eid2, _cmds2 = commands_of(_p2.stats, ANCHOR_TECH)
check("re-parsed: the anchor's effect carries the enable",
      (2, UNIT, 1, -1, 0.0) in _cmds2, str(_cmds2))
check("re-parsed: villagers are 1000 hp",
      sorted({x.get("hit_points") for c in _p2.stats["civs"]
              for x in (c.get("units") or []) if x.get("id") == 83}) == [1000])
check("re-parsed: tech %d is untouched (CONTROL B)" % LONGBOW_TECH,
      _p2.stats["techs"][LONGBOW_TECH]["effect_id"] == LONGBOW_EFFECT,
      str(_p2.stats["techs"][LONGBOW_TECH]["effect_id"]))

_o2550b, _v2550b = enabling(_p2, out, gv, UNIT)
_civs2, _cs2, _gv2, _tl2 = L.locate(out, parser=_p2)
_brit2 = next(c for c in _civs2 if c["name"] == CIV)
_u2 = next(u for u in _brit2["units"] if u["id"] == UNIT)
_off2 = _u2["train_locations"][0]["_off_train_time"]
patched = bytearray(out)
patched[_off2 + 4] = NEW_SLOT                                        # EDIT 3
if _v2550b != -1:
    struct.pack_into("<i", patched, _o2550b, -1)
patched = bytes(patched)
_d = [i for i in range(len(out)) if out[i] != patched[i]]
print("     EDIT 3  button_id %d -> %d at offset %d ; bytes changed: %d"
      % (out[_off2 + 4], NEW_SLOT, _off2 + 4, len(_d)))
check("the button edit moved exactly one byte", _d == [_off2 + 4],
      "%s vs [%d]" % (_d, _off2 + 4))

with contextlib.redirect_stdout(io.StringIO()):
    _p3 = P.Parser(patched)
    _p3.parse()
check("the patched dat still re-parses to a clean EOF",
      _p3.r.pos == len(patched), "%d vs %d" % (_p3.r.pos, len(patched)))

print()
print("C  the JSON halves (tree row + panel entry), via the PRODUCT's own path")
trees = CT.load_trees(GAME)
proposal = dict(trees)
proposal[TREE_KEY] = json.loads(json.dumps(trees[TREE_KEY], ensure_ascii=False))
rep5 = AV.apply(proposal, TREE_KEY, UNIT, "grant")
files, rel = AV.emit_files(proposal, TREE_KEY)
_row = CT.row_for(proposal[TREE_KEY], UNIT, CT.UNIT_USE_TYPES)
print("     EDIT 4  %s : %s" % (rel, rep5.get("mode", "?")))
print("             row = %s"
      % {k: _row.get(k) for k in ("Node ID", "Name", "Node Status", "Age ID",
                                  "Building ID", "Trigger Tech ID")})
check("the tree says Dark Age", _row.get("Age ID") == 1, str(_row.get("Age ID")))
check("the tree says the Barracks", _row.get("Building ID") == 12)
panel_rep, panel_files = tk._panel_availability(TREE_KEY, UNIT, "grant",
                                                CT.UNIT_USE_TYPES, proposal)
print("     EDIT 5  panel: %s"
      % {k: panel_rep.get(k) for k in ("mode", "ok", "panel_name", "donor",
                                       "before_entries", "after_entries")})
check("the panel edit landed", panel_rep.get("ok") is True, str(panel_rep))
check("the panel really gained an entry",
      (panel_rep.get("after_entries") or 0) > (panel_rep.get("before_entries") or 0),
      str(panel_rep))
files.update(panel_files)

print()
print("D  emit")
info = {"Author": "dsh", "CacheStatus": 0, "Description": DESC, "Title": TITLE}
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
E.emit_data_mod(OUT, patched, info, base_dir=GAME, overwrite=True,
                json_files=files or None)
for root, _dd, fs in os.walk(OUT):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        print("     %10d  %s" % (os.path.getsize(fp), os.path.relpath(fp, OUT)))
print("     Title = %r (%d UTF-8 bytes)" % (TITLE, len(TITLE.encode("utf-8"))))
check("the Title fits the engine's 100-byte folder limit",
      len(TITLE.encode("utf-8")) <= 100)

print()
print("DSH TEST V7 READY: %s" % OUT)
print("  CONTROL A : villager + task -> stays at 1000 hp")
print("  CONTROL B : CASTLE AGE, British CASTLE -> Longbowman still there")
print("  TEST C    : DARK AGE, British BARRACKS -> Champi Scout (no Castle needed)")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
