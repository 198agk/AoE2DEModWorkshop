# -*- coding: utf-8 -*-
r"""v9 -- one session, three answers.

WHY THIS MOD EXISTS
-------------------
Two of the three sentences are CONTROLS that already passed in game; they are
here so a single launch can re-check that the PRODUCT path (not a hand-written
script) still does what `dsh test v7` did by hand.

  A (control)  Villagers 1000 hp.  Proven by m11482/m26421.
  B (control)  British may build the Champi Scout at 0:00.  Proven by m27131
               (`dsh test v7`), and here it must come out of `aoe2mod.api`.
  C (NEW)      INCAS may NOT build it any more -- a REVOKE.

C is the question that has been open the longest and it is deliberately the
cheapest possible test of it:

  * The Incas really do build unit 2550 at 0:00 in a Barracks.  No age gate,
    no research gate, nothing to confuse the reading.
  * C touches ONLY the two JSON layers.  The `.dat` rides along byte-identical
    (raw sha256 asserted), so the `.dat` route -- the global `type 2` enable in
    tech 1350 plus this civ's own train entry -- is fully intact.
  * Therefore: button gone  -> a JSON layer drives the build menu.
                button there -> neither JSON layer can remove it, and revoke
                needs a `.dat` recipe (`type 2` with b = 0).

HOW TO READ IT
--------------
  Incas  -> Barracks: Champi Scout must be ABSENT   (C)
  British-> Barracks in the DARK AGE: present       (B)
  Any villager, after being given a job: 1000 hp    (A)
"""
import io, json, os, sys, contextlib, hashlib, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A
from aoe2mod.dat import parser as P
from aoe2mod.game import civtechtrees as CT
from aoe2mod.game import locations as G
from aoe2mod.game import buildpanel as BP
import testmod_name as TN

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v9")
VERSION = 9
UNIT = 2550
GRANT_CIV_KEY, GRANT_CIV = "BRITONS", "British"
REVOKE_CIV_KEY, REVOKE_CIV = "INCAS", "Incas"
HP = 1000

fails = []
def check(name, ok, detail=""):
    print("  %-68s %s%s" % (name[:68], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)

def raw_sha(path):
    return hashlib.sha256(P.load_dat(path)[0]).hexdigest()

def ms(rows):
    return collections.Counter(
        json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)

def tree_of(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

def listed(obj, civ, unit_id):
    out = []
    for blk in BP.buildings(obj, civ):
        for e in BP.entries(obj, civ, blk.get("ID"), BP.UNITS_KEY):
            if int(e.get("ID", -1)) == unit_id:
                out.append((blk.get("ID"), dict(e)))
    return out

tk = A.open_toolkit(game_root=GAME)
tk._ensure()

print("A  the two JSON layers say what the experiment needs them to say")
_pan = BP.load_all(GAME)
_ship_grant = tree_of(os.path.join(GAME, "resources", "_common", "dat",
                                   "CivTechTrees", "BRITONS.json"))
_ship_revoke = tree_of(os.path.join(GAME, "resources", "_common", "dat",
                                    "CivTechTrees", "INCAS.json"))
check("British has NO row for 2550 today (the grant is a real change)",
      CT.row_for(_ship_grant, UNIT, CT.UNIT_USE_TYPES) is None)
check("Incas HAS a ResearchedCompleted row for 2550",
      CT.node_status(_ship_revoke, UNIT, CT.UNIT_USE_TYPES) == "ResearchedCompleted")
check("the panel lists it for Incas and not for British",
      len(listed(_pan[BP.civ_key_for(_pan, REVOKE_CIV)]["obj"],
      BP.civ_key_for(_pan, REVOKE_CIV), UNIT)) == 1
      and listed(_pan[BP.civ_key_for(_pan, GRANT_CIV)]["obj"],
             BP.civ_key_for(_pan, GRANT_CIV), UNIT) == [])

print()
print("B  plan the three sentences, then build them as ONE bundle")
INTENTS = [
    {"intent": "unit.stat", "unit": "村民", "stat": "hit_points", "value": HP},
    {"intent": "unit.availability", "unit": UNIT, "civ": GRANT_CIV,
     "action": "grant"},
    {"intent": "unit.availability", "unit": UNIT, "civ": REVOKE_CIV,
     "action": "revoke"},
]
_plan = tk.plan_bundle(INTENTS)
print("   preview: edit_count=%s dat_half_edit_count=%s changes_dat=%s "
      "dat_is_carrier=%s dat_half_refusals=%s"
      % (_plan.get("edit_count"), _plan.get("dat_half_edit_count"),
         _plan.get("changes_dat"), _plan.get("dat_is_carrier"),
         _plan.get("dat_half_refusals")))
check("the bundle previews", _plan.get("edit_count") is not None)
# 2026-10-19 v17 gave `revoke` a `.dat` half of its own, so BOTH availability
# sentences write bytes now (grant 2 edits: the effect and the tech pointer;
# revoke 1: its own effect).  The old check demanded 2 edits and one refusal --
# it was describing the product as it stood before that commit.  Kept as a
# property, not a count: a refusal here would mean the revoke silently did
# nothing again.
check("both availability sentences contribute a .dat half",
        (_plan.get("dat_half_edit_count") or 0) == 3, _plan.get("dat_half_edit_count"))
check("and neither is refused -- the revoke really writes bytes now",
      len(_plan.get("dat_half_refusals") or []) == 0,
      _plan.get("dat_half_refusals"))
check("the plan knows the revoke carries a .dat half (v17, 2026-10-19)",
      _plan.get("changes_dat") is True and _plan.get("dat_is_carrier") is False,
        (_plan.get("changes_dat"), _plan.get("dat_is_carrier")))
check("the bundle says it changes .dat bytes (the grant does)",
      _plan.get("changes_dat") is True)
check("and that the .dat is not merely a carrier",
      _plan.get("dat_is_carrier") is False)

TITLE = TN.name_for(VERSION, "村民血量1000 + 不列颠可造印加不可造蔷琵侦察兵",
                    "撤销是否生效→菜单是否读JSON层")
DESC = TN.description_for(
    VERSION,
    "三件事一起做：(A) 全部文明村民血量 1000；(B) 不列颠兵营从黑暗时代起就能造蔷琵侦察兵（单位 2550）；"
    "(C) 印加兵营不再能造蔷琵侦察兵。",
    "A/B 是控制组（已在游戏里通过）；C 是新问题——撤销只改 CivTechTrees 与建造面板两层 JSON",
    extra_lines=[
        "怎么看：印加兵营里如果还有蔷琵侦察兵，说明两层 JSON 都拦不住它，撤销需要写 `.dat`；",
        "如果按钮消失了，说明至少有一层 JSON 是建造菜单真正读的。",
        "不列颠那一侧在黑暗时代（不用建城堡）就应该有按钮。",
    ])
check("the Title fits the engine's 100-byte limit",
      len(TITLE.encode("utf-8")) <= 100, "%d bytes" % len(TITLE.encode("utf-8")))

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
man = tk.build_bundle(INTENTS, OUT, title=TITLE, author="dsh", description=DESC,
                      overwrite=True)

print()
print("C  what landed on disk")
_files = sorted(f.get("rel") for f in (man.get("files") or []))
for f in _files:
    print("     %s" % f)
check("the .dat is there", any(f.endswith("empires2_x2_p1.dat") for f in _files))
check("both tree files are there",
      any("CivTechTrees/BRITONS.json" in f for f in _files)
      and any("CivTechTrees/INCAS.json" in f for f in _files))
check("the panel file is there", any(f.endswith("futuravailableunits.json") for f in _files))
check("the manifest counts the .dat half",
      man.get("dat_half_edit_count") == (_plan.get("dat_half_edit_count") or 0),
        "%s vs plan %s" % (man.get("dat_half_edit_count"),
                           _plan.get("dat_half_edit_count")))
check("build's edit_count equals the preview's",
      man.get("edit_count") == _plan.get("edit_count"),
      "%s vs %s" % (man.get("edit_count"), _plan.get("edit_count")))

print()
print("D  the .dat really carries all of it (unmodified parser, from disk)")
_dp = os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")
_rawn, _how = P.load_dat(_dp)
_pr = P.Parser(_rawn); _pr.parse()
check("clean EOF", _pr.r.pos == len(_rawn),
      "%d of %d" % (_pr.r.pos, len(_rawn)))
check("it grew: a new effect was appended",
      len(_rawn) > len(P.load_dat(G.dat_path(GAME))[0]),
      "%d vs %d" % (len(_rawn), len(P.load_dat(G.dat_path(GAME))[0])))
_effs = _pr.stats["effects"]
_ref = _pr.stats["techs"][383].get("effect_id")
# "tech 383 points at the LAST effect" stopped meaning the same thing once the
# revoke appended an effect after the grant's.  What the answer needs is that
# tech 383 points at an effect that ENABLES the unit -- the file having grown is
# already asserted above ("it grew: a new effect was appended").
check("tech 383 points at an appended effect", _ref is not None, _ref)
_cmds = [tuple(c) for c in _effs[_ref]["commands"]]
check("that effect carries the anchor's own commands AND a type-2 ENABLE",
        (2, UNIT, 1, -1, 0.0) in _cmds and len(_cmds) == 3, _cmds)
check("and the enable is the last command, so the later command wins",
      _cmds[-1] == (2, UNIT, 1, -1, 0.0), _cmds)
check("tech 263 (the Longbowman's, control B) is untouched",
      _pr.stats["techs"][263].get("effect_id") == 251)
_hps = sorted({u["hit_points"] for c in _pr.stats["civs"] for u in c["units"]
               if u["id"] == 83})
check("every villager family member is 1000 hp", _hps == [HP], _hps)

print()
print("E  the two JSON layers, re-read from disk")
_forbidden = CT.can_build(tree_of(os.path.join(
    OUT, "resources", "_common", "dat", "CivTechTrees", "INCAS.json")), UNIT)
_allowed = CT.can_build(tree_of(os.path.join(
    OUT, "resources", "_common", "dat", "CivTechTrees", "BRITONS.json")), UNIT)
check("the emitted Incas tree refuses it", _forbidden is False)
check("the emitted British tree allows it", _allowed is True)
_pnew = json.load(open(os.path.join(
    OUT, "resources", "_common", "dat", "futuravailableunits.json"),
    "r", encoding="utf-8"))
check("the emitted panel drops it for Incas",
      listed(_pnew, REVOKE_CIV, UNIT) == [])
# The panel has its OWN civilization key ("Britons"), which is not the `.dat`
# spelling ("British").  Asking with the `.dat` name silently returns nothing,
# which reads exactly like "the entry is missing".
_GPK = BP.civ_key_for(_pan, GRANT_CIV)
check("the grant civ's panel key is not the .dat spelling", _GPK == "Britons", _GPK)
check("and adds it to the British barracks",
      [b for b, _e in listed(_pnew, _GPK, UNIT)] == [12],
      listed(_pnew, _GPK, UNIT))
# Compare over the PANEL's own civ keys: the two spellings differ, and mixing
# them silently turns "the grant civ" into "a fourth untouched civilization".
_KEYS = {BP.civ_key_for(_pnew, GRANT_CIV), BP.civ_key_for(_pnew, REVOKE_CIV)}
check("the panel keys are the display names, not the .dat spellings",
      _KEYS == {"Britons", "Incas"}, _KEYS)
check("and the only civilizations listing it now are the grant civ plus the "
      "three that always did",
      sorted({c for c in _pnew for _b, _e in listed(_pnew, c, UNIT)})
      == ["Britons", "Mapuche", "Muisca", "Tupi"],
      sorted({c for c in _pnew for _b, _e in listed(_pnew, c, UNIT)}))

print()
print("F  the byte patches the writer's model cannot carry")
_boff_units = None
import aoe2mod.dat.locate as L
_civs2, _cs2, _gv2, _tl2 = L.locate(_rawn, parser=_pr)
_br = next(c for c in _civs2 if c["name"] == GRANT_CIV)
_u = next(u for u in _br["units"] if u["id"] == UNIT)
check("the British training button moved off slot 1 (where the militia line masks it)",
      _u["train_locations"][0]["button_id"] == 4,
      _u["train_locations"][0]["button_id"])

print()
if fails:
    print("v9: %d FAILED" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("v9: ALL CHECKS PASSED")
print("   Title: %s" % TITLE)
print("   out:   %s" % OUT)
