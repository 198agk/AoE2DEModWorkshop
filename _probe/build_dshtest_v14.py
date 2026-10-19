# -*- coding: utf-8 -*-
r"""v14 -- the TREE LAYER alone, tested in both directions at once.

WHY THIS MOD EXISTS
-------------------
Every previous attempt to answer "does the game read a mod's
`CivTechTrees/<CIV>.json`?" was confounded:

  * 2026-10-14  the mod edited the `.dat` AND the tree, so only the `.dat`
                half could be attributed;
  * `dsh test v9` revoke INCAS 2550 deleted the tree row but left a DANGLING
                `Link ID 2550` behind (row 2588 still pointed at the deleted
                node -- no shipped file has a single dangling link), AND
                simultaneously deleted the panel entry, so a reading could not
                separate "the file was invalid and rejected" from "the panel did
                it" from "the tree is not read at all".

This mod removes all three confounders at once:

  * it ships ONLY tree files (the panel is untouched, and the panel has already
    been excluded in both directions by two in-game observations);
  * the `.dat` rides along BYTE-IDENTICAL (raw sha256 asserted below), so the
    `.dat` route -- the global `type 2` enable of 2550 in tech 1350 plus each
    civ's own train entry -- is exactly as shipped;
  * every emitted tree is CHAIN-CLOSED (`dangling_links` empty, asserted), which
    is the shape all 62 shipped files have.

It asks BOTH directions in one launch, because one direction alone cannot
distinguish "the write works" from "the write is ignored":

  INCAS   -> Barracks: Champi Scout must be GONE      (revoke, +cascade)
  BRITONS -> Barracks, DARK AGE: Champi Scout appears (grant)

Reading:
    both changed   -> the game reads the tree layer, and both writes take effect
    neither        -> the tree layer is NOT read from a mod (or the mod did not
                      load -- cross-check MainLog.txt for "Enabling mod")
    only one       -> half the story; report which half, do not generalise

HOW TO READ IT
--------------
  1. enable the mod, start a random-map single-player game
  2. pick INCAS: Barracks must NOT offer Champi Scout  (它出厂时是有的)
  3. pick BRITONS: Barracks must offer Champi Scout in the DARK AGE
  4. both readings are about the BUTTON GRID, not the tech-tree preview
"""
import collections
import contextlib
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
from aoe2mod.dat import parser as P                         # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402
from aoe2mod.game import locations as G                     # noqa: E402
from aoe2mod.mod import emitter as E                        # noqa: E402
import testmod_name as TN                                   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v14")
VERSION = 14
UNIT = 2550
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


def parse_deflate(path):
    raw, how = P.load_dat(path)
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return raw, how, p


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

print()
print("B  build the two edited trees")
_rev = json.loads(json.dumps(_shipped[REVOKE_KEY]))
_gon = set()
_n = CT.revoke(_rev, UNIT, CT.UNIT_USE_TYPES, revoked_ids=_gon)
check("revoke removed rows", _n > 0, _n)
check("INCAS' tree is now CHAIN-CLOSED", CT.dangling_links(_rev) == [],
      CT.dangling_links(_rev))
check("INCAS no longer has a row for 2550",
      CT.row_for(_rev, UNIT, CT.UNIT_USE_TYPES) is None)
_kept = {r.get("Node ID") for r in CT.rows_of(_rev) if r.get("Use Type") == "Unit"}
check("no surviving row still points at a removed node",
      not any(r.get("Link ID") in set(_gon) for r in CT.rows_of(_rev)
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
check("the grant copied a real row rather than inventing one",
      CT.can_build(_grt, UNIT) is True)
check("BRITONS' tree is still CHAIN-CLOSED", CT.dangling_links(_grt) == [],
      CT.dangling_links(_grt))
for w in _warn:
    print("   inherited: %s" % w)

print()
print("C  emit a mod that ships ONLY these two trees")
_panel_untouched = True


def _rel(key):
    return "resources/_common/dat/CivTechTrees/%s.json" % key


_json = {_rel(REVOKE_KEY): CT.serialize(_rev),
         _rel(GRANT_KEY): CT.serialize(_grt)}
check("the serialized Incas tree parses back to the same rows",
      CT.serialize(_rev) and json.loads(CT.serialize(_rev)) == _rev)
check("the serialized British tree parses back to the same rows",
      CT.serialize(_grt) and json.loads(CT.serialize(_grt)) == _grt)

TITLE = TN.name_for(VERSION, "只改科技树：印加没有、不列颠有蔷琵侦察兵",
                    "mod的树文件到底读不读")
DESC = TN.description_for(
    VERSION,
    "只替换两个文明树文件：印加兵营去掉蔷琵侦察兵（连同它整条升级链），"
    "不列颠兵营黑暗时代就能造蔷琵侦察兵。`.dat` 与建造面板都逐字节未改。",
    "游戏是否读取 mod 里的 CivTechTrees 文件",
    extra_lines=[
        "怎么看（看选中建筑后的按钮格，不要看科技树预览）：",
        "① 选印加，兵营里应该【没有】蔷琵侦察兵（出厂时是有）；",
        "② 选不列颠，黑暗时代的兵营里应该【有】蔷琵侦察兵（出厂时是没有）。",
        "两边都变 = 游戏确实读树层；两边都没变 = 树层没有被读；只变一边 = 只改了一半，"
        "请告诉我变的是哪一边。",
    ])
check("the Title fits the engine's 100-byte limit",
      len(TITLE.encode("utf-8")) <= 100,
      "%d bytes" % len(TITLE.encode("utf-8")))

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
_info = E.make_info(TITLE, author="dsh", description=DESC)
man = E.emit_json_mod(OUT, _json, _info, base_dir=GAME, overwrite=True)

print()
print("D  what landed on disk")
_files = sorted(f.get("rel") for f in (man.get("files") or []))
for f in _files:
    print("     %s" % f)
check("exactly the two tree files plus the .dat carrier (and info.json)",
      _files == sorted(["info.json", _rel(REVOKE_KEY), _rel(GRANT_KEY),
                        "resources/_common/dat/empires2_x2_p1.dat"]), _files)
check("no panel file in the mod",
      not any("futuravailableunits" in f for f in _files), _files)

print()
print("E  the carrier .dat is byte-identical to the shipped one")
_ra, _how_a, _pa = parse_deflate(os.path.join(OUT, "resources", "_common", "dat",
                                              "empires2_x2_p1.dat"))
_rb, _how_b, _pb = parse_deflate(G.dat_path(GAME))
check("raw sha256 matches the shipped .dat",
      hashlib.sha256(_ra).hexdigest() == hashlib.sha256(_rb).hexdigest())
check("the carrier .dat parses to exact EOF", _pa.r.pos == len(_ra),
      "%d of %d" % (_pa.r.pos, len(_ra)))
check("2550 is still in the INCAS .dat unit array (nothing hidden there)",
      any(u["id"] == UNIT for c in _pa.stats["civs"] if c.get("name") == "Incas"
          for u in c["units"]))

print()
print("F  the two files re-read from WHERE THEY LANDED")
_rev2 = json.load(open(os.path.join(OUT, _rel(REVOKE_KEY)), encoding="utf-8"))
_grt2 = json.load(open(os.path.join(OUT, _rel(GRANT_KEY)), encoding="utf-8"))
check("INSTALLED Incas tree refuses 2550",
      CT.can_build(_rev2, UNIT) is False)
check("INSTALLED British tree allows 2550",
      CT.can_build(_grt2, UNIT) is True)
check("INSTALLED Incas tree is chain-closed", CT.dangling_links(_rev2) == [])
check("INSTALLED British tree is chain-closed", CT.dangling_links(_grt2) == [])
_base = {k: json.dumps(_shipped[k], sort_keys=True) for k in _shipped}
check("the two trees really differ from shipped",
      json.dumps(_rev2, sort_keys=True) != _base[REVOKE_KEY]
      and json.dumps(_grt2, sort_keys=True) != _base[GRANT_KEY])

print()
if fails:
    print("v14: %d FAILED" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("v14: ALL CHECKS PASSED")
print("   Title: %s" % TITLE)
print("   out:   %s" % OUT)
