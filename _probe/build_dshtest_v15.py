# -*- coding: utf-8 -*-
r"""v15 -- the tree layer, WITH a control group that proves the mod loaded.

WHY THIS MOD EXISTS
-------------------
v14 asked the right question -- "does the game read a mod's
`CivTechTrees/<CIV>.json`?" -- and shipped two tree files on top of a
BYTE-IDENTICAL `.dat`.  The user launched it, the Incas still had the Champi
Scout and Britain still did not, so the tree write did not reach the build menu.

That reading has ONE confounder left, and it is the same one that made smoke5
AMBIGUOUS: a mod that never loaded and a mod whose tree half was ignored look
IDENTICAL on screen.  v14 cannot tell them apart, because every file it ships is
either a tree (the thing under test) or a byte-identical copy of something the
game already has.

v15 adds a CONTROL GROUP inside the same mod:

    villager family (27 record ids, all 63 civs) -> hit_points 25 -> 1000

That exact edit was verified in-game on 2026-10-16 (`dsh test v7`): the user
reported 村民血量 1000/1000, and still 1000 after giving the villager a job.
So if the villager screen says 1000, the mod DEFINITELY loaded and the `.dat`
route DEFINITELY works in this very launch.

The test group is unchanged from v14:

    INCAS   -> Barracks: Champi Scout must be GONE   (revoke + cascade)
    BRITONS -> Barracks, DARK AGE: Champi Scout appears (grant)

Reading (all three in the SAME launch):

    villagers 1000 + Incas keeps it  -> mod loaded, the TREE layer is ignored
    villagers 1000 + Incas loses it  -> the tree layer IS read, and works
    villagers 25                      -> the mod did not load at all; the tree
                                        reading is void, report nothing

HOW TO READ IT
--------------
  1. enable the mod, start a random-map single-player game
  2. look at any villager: hit points must read 1000 / 1000        [CONTROL]
  3. pick INCAS: Barracks must NOT offer Champi Scout              [TEST A]
  4. pick BRITONS: Barracks must offer Champi Scout in the DARK AGE[TEST B]
  5. read the BUTTON GRID of the selected building, NOT the tech-tree preview
"""
import contextlib
import _gamepaths as GP
import hashlib
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A                                     # noqa: E402
import aoe2mod.dat.families as F                            # noqa: E402
from aoe2mod.dat import parser as P                         # noqa: E402
from aoe2mod.dat import writer as W                         # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402
from aoe2mod.game import locations as G                     # noqa: E402
from aoe2mod.mod import emitter as E                        # noqa: E402
import testmod_name as TN                                   # noqa: E402

GAME = GP.GAME
OUT = os.path.join(HERE, "out_dshtest_v15")
VERSION = 15
UNIT = 2550             # Champi Scout
VILLAGER = 83           # the id the family lookup keys on
HP = 1000
REVOKE_KEY = "INCAS"
GRANT_KEY = "BRITONS"

fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name[:70], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


def tree_path(key):
    return os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees",
                        "%s.json" % key)


def load_tree(key):
    with open(tree_path(key), encoding="utf-8") as fh:
        return json.load(fh)


def rel_tree(key):
    return "resources/_common/dat/CivTechTrees/%s.json" % key


def parse_raw(raw):
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p


# ---------------------------------------------------------------- baseline
print("A  the shipped baseline this reading will be compared against")
_shipped = {k: load_tree(k) for k in (REVOKE_KEY, GRANT_KEY)}
check("INCAS ships 2550 as ResearchedCompleted",
      CT.node_status(_shipped[REVOKE_KEY], UNIT, CT.UNIT_USE_TYPES)
      == "ResearchedCompleted",
      CT.node_status(_shipped[REVOKE_KEY], UNIT, CT.UNIT_USE_TYPES))
check("BRITONS has NO row for 2550",
      CT.row_for(_shipped[GRANT_KEY], UNIT, CT.UNIT_USE_TYPES) is None)
_closed = CT.chain_closure(_shipped[REVOKE_KEY], UNIT, CT.UNIT_USE_TYPES)
print("   revoke cascade on INCAS = %s" % sorted(_closed))
check("the cascade is larger than the single row (the chain is real)",
      len(_closed) > 1, sorted(_closed))

_raw_shipped = P.load_dat(G.dat_path(GAME))[0]
_how = P.load_dat(G.dat_path(GAME))[1]
print("   shipped .dat: %d raw bytes (%s)" % (len(_raw_shipped), _how))
_p0 = parse_raw(_raw_shipped)
_civs0 = _p0.stats["civs"]
_vil0 = sorted({u.get("hit_points") for c in _civs0
                for u in (c.get("units") or []) if u.get("id") == VILLAGER})
print("   shipped villager hit_points across all civs = %s" % _vil0)
check("the shipped villager is NOT already 1000 (so the control is a real change)",
      _vil0 != [HP], _vil0)
check("2550 is in the INCAS .dat unit array as shipped",
      any(u["id"] == UNIT for c in _civs0 if c.get("name") == "Incas"
          for u in (c.get("units") or [])))

# ---------------------------------------------------------------- the trees
print()
print("B  build the two edited trees (the TEST half)")
_rev = json.loads(json.dumps(_shipped[REVOKE_KEY]))
_gon = set()
_n = CT.revoke(_rev, UNIT, CT.UNIT_USE_TYPES, revoked_ids=_gon)
check("revoke removed rows", _n > 0, _n)
check("INCAS' tree is now CHAIN-CLOSED", CT.dangling_links(_rev) == [],
      CT.dangling_links(_rev))
check("INCAS no longer has a row for 2550",
      CT.row_for(_rev, UNIT, CT.UNIT_USE_TYPES) is None)
check("no surviving row still points at a removed node",
      not any(r.get("Link ID") in _gon for r in CT.rows_of(_rev)
              if r.get("Use Type") == "Unit" and isinstance(r.get("Link ID"), int)))
print("   rows removed: %d  (%s)" % (_n, sorted(_gon)))

_grt = json.loads(json.dumps(_shipped[GRANT_KEY]))
_donor = CT.row_for(_shipped[REVOKE_KEY], UNIT, CT.UNIT_USE_TYPES)
_row, _warn = CT.grant(_grt, UNIT, _donor, status="ResearchedCompleted")
check("BRITONS' tree now has a ResearchedCompleted row for 2550",
      CT.node_status(_grt, UNIT, CT.UNIT_USE_TYPES) == "ResearchedCompleted",
      CT.node_status(_grt, UNIT, CT.UNIT_USE_TYPES))
check("the grant landed in the barracks", _row.get("Building ID") == 12,
      _row.get("Building ID"))
check("BRITONS' tree is still CHAIN-CLOSED", CT.dangling_links(_grt) == [],
      CT.dangling_links(_grt))
for w in _warn:
    print("   inherited: %s" % w)

# ---------------------------------------------------------------- the .dat
print()
print("C  the CONTROL half: villager family -> %d hp (proven in-game on 2026-10-16)"
      % HP)
tk = A.open_toolkit(game_root=GAME)
tk.describe(VILLAGER)
data, civs, _cs, gv, tail, how = tk._parsed
check("the toolkit parsed the shipped .dat", len(civs) == 63, len(civs))

with contextlib.redirect_stdout(io.StringIO()):
    _p1 = P.Parser(data)
    _p1.parse()
stats = _p1.stats
check("the parser reached exact EOF", _p1.r.pos == len(data),
      "%d of %d" % (_p1.r.pos, len(data)))

F.warm({"civs": civs}, game_root=GAME)
_family = sorted(F.family_of(F.build_families(civs), VILLAGER))
_touched = 0
for c in stats["civs"]:
    for u in (c.get("units") or []):
        if u.get("id") in _family:
            if u.get("hit_points") != HP:
                _touched += 1
            u["hit_points"] = HP
print("   villager family (%d ids) -> %d ; records set: %d"
      % (len(_family), HP, _touched))
check("every civilization's villager records were set",
      _touched == len(_family) * len(civs),
      "%d vs %d" % (_touched, len(_family) * len(civs)))

_out, _rep = W.serialize_dat(stats, raw=data, gv=gv)
_p2 = parse_raw(_out)
check("the writer's output re-parses to a clean EOF", _p2.r.pos == len(_out),
      "%d vs %d" % (_p2.r.pos, len(_out)))
check("re-parsed: every villager is %d hp" % HP,
      sorted({u.get("hit_points") for c in _p2.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == VILLAGER}) == [HP],
      sorted({u.get("hit_points") for c in _p2.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == VILLAGER}))
check("re-parsed: 2550 is still in the INCAS unit array (the .dat does not hide it)",
      any(u["id"] == UNIT for c in _p2.stats["civs"] if c.get("name") == "Incas"
          for u in (c.get("units") or [])))
_d = [i for i in range(min(len(_out), len(data))) if _out[i] != data[i]]
print("   .dat bytes changed: %d   (%d -> %d bytes)"
      % (len(_d), len(data), len(_out)))
check("the .dat really changed (so this half is not a byte-identical carrier)",
      len(_d) > 0 or len(_out) != len(data), len(_d))

# ---------------------------------------------------------------- emit
print()
print("D  emit ONE mod carrying both halves")
_json = {rel_tree(REVOKE_KEY): CT.serialize(_rev),
         rel_tree(GRANT_KEY): CT.serialize(_grt)}
check("the serialized Incas tree parses back to the same rows",
      json.loads(CT.serialize(_rev)) == _rev)
check("the serialized British tree parses back to the same rows",
      json.loads(CT.serialize(_grt)) == _grt)

TITLE = TN.name_for(VERSION, "对照组实验：村民1000血 + 只改树的蔷琵侦察兵",
                    "证明mod确实加载")
DESC = TN.description_for(
    VERSION,
    "同一个 mod 里放两半：一半是已经实机证明会生效的村民血量（对照组），"
    "另一半只替换印加与不列颠的文明树文件（测试组）。`.dat` 里除了村民血量"
    "没有任何其他改动，建造面板逐字节未改。",
    "这个 mod 到底有没有被加载，以及树文件到底读不读",
    extra_lines=[
        "怎么读（全部在同一局里看，看按钮格不要看科技树预览）：",
        "对照：随便一个村民，血量应该是 1000 / 1000。若是 25，说明 mod 根本没加载，"
        "下面两条读数作废。",
        "测试①：选印加，兵营里应该【没有】蔷琵侦察兵（出厂时是有）。",
        "测试②：选不列颠，黑暗时代的兵营里应该【有】蔷琵侦察兵（出厂时是没有）。",
        "三个结果：村民1000且印加仍有 = mod加载了但树层被忽略；村民1000且印加没有了 = "
        "树层生效；村民25 = mod没加载。",
    ])
check("the Title fits the engine's 100-byte limit",
      len(TITLE.encode("utf-8")) <= 100,
      "%d bytes" % len(TITLE.encode("utf-8")))

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
_info = E.make_info(TITLE, author="dsh", description=DESC)
man = E.emit_data_mod(OUT, _out, _info, base_dir=GAME, overwrite=True,
                      json_files=_json)

print()
print("E  what landed on disk")
_files = sorted(f.get("rel") for f in (man.get("files") or []))
for f in _files:
    print("     %s" % f)
check("the mod carries both trees and exactly one .dat",
      _files == sorted(["info.json", rel_tree(REVOKE_KEY), rel_tree(GRANT_KEY),
                        "resources/_common/dat/empires2_x2_p1.dat"]), _files)
check("no panel file in the mod",
      not any("futuravailableunits" in f for f in _files), _files)

print()
print("F  read the emitted mod back off the disk")
_inst = parse_raw(P.load_dat(os.path.join(OUT, "resources", "_common", "dat",
                                          "empires2_x2_p1.dat"))[0])
check("the INSTALLED .dat gives every villager %d hp" % HP,
      sorted({u.get("hit_points") for c in _inst.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == VILLAGER}) == [HP],
      sorted({u.get("hit_points") for c in _inst.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == VILLAGER}))
check("the INSTALLED .dat still lists 2550 for the Incas",
      any(u["id"] == UNIT for c in _inst.stats["civs"] if c.get("name") == "Incas"
          for u in (c.get("units") or [])))
check("the INSTALLED .dat is NOT the shipped one",
      hashlib.sha256(_out).hexdigest() != hashlib.sha256(data).hexdigest())

_rev2 = json.load(open(os.path.join(OUT, rel_tree(REVOKE_KEY)), encoding="utf-8"))
_grt2 = json.load(open(os.path.join(OUT, rel_tree(GRANT_KEY)), encoding="utf-8"))
check("INSTALLED Incas tree refuses 2550", CT.can_build(_rev2, UNIT) is False)
check("INSTALLED British tree allows 2550", CT.can_build(_grt2, UNIT) is True)
check("INSTALLED Incas tree is chain-closed", CT.dangling_links(_rev2) == [])
check("INSTALLED British tree is chain-closed", CT.dangling_links(_grt2) == [])
check("the two installed trees really differ from shipped",
      json.dumps(_rev2, sort_keys=True) != json.dumps(_shipped[REVOKE_KEY], sort_keys=True)
      and json.dumps(_grt2, sort_keys=True) != json.dumps(_shipped[GRANT_KEY], sort_keys=True))

print()
if fails:
    print("v15: %d FAILED" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("v15: ALL CHECKS PASSED")
print("   Title: %s" % TITLE)
print("   out:   %s" % OUT)
print("   对照: 村民血量 1000/1000（若是 25 则 mod 没加载，读数作废）")
print("   测试A: 印加兵营 -> 没有蔷琵侦察兵")
print("   测试B: 不列颠黑暗时代兵营 -> 有蔷琵侦察兵")
