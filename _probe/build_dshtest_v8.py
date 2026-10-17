# -*- coding: utf-8 -*-
r"""Build `dsh test v8` using ONLY the product API -- no hand-written .dat code.

Why this file exists
--------------------
`dsh test v7` was hand-built (`build_dshtest_v7.py`): it appends the effect,
re-points the technology, and patches the button byte with its own `struct`
calls.  The user confirmed v7 in game (m27131) -- but a hand-built artifact
proving the FORMAT is not the product proving itself.  v7's script also copied
the anchor's commands BY HAND, so it never would have caught the product's
carry-over defect (`apply_grant` replaced the anchor's commands instead of
carrying them).

This script builds the same request through `aoe2mod.api` alone:

    sentence 1  unit.stat          villagers -> 1000 hp          [CONTROL A]
    sentence 2  unit.availability  British <- unit 2550, grant   [TEST C]

and the product must produce all FOUR layers by itself: the `.dat` recipe (new
effect carrying the anchor's own commands + the enable command, re-pointed
technology, moved training button), the civ tech tree row, and the build-panel
entry -- plus leave `EnablingResearch` alone and leave the Longbowman's
technology alone (CONTROL B).

v8 == v7 in behaviour but not in authorship.  If the user confirms v8, the
PRODUCT is confirmed, not just the format.

Run:  python _probe/build_dshtest_v8.py
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import aoe2mod.api as A                                       # noqa: E402
import testmod_name as TN                                     # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v8")
VERSION = 8
UNIT = 2550

WHAT = "村民血量1000 + 不列颠黑暗时代可造蔷琵侦察兵"
VERIFIED = ("全部由产品 API 构建（不再手写 .dat 字节）：村民 1000 血 + 不列颠兵营"
            "黑暗时代出蔷琵侦察兵")
TITLE = TN.name_for(VERSION, WHAT)
DESC = TN.description_for(
    VERSION, WHAT, VERIFIED,
    extra_lines=[
        "与 v7 行为相同，但 v7 是手工脚本拼出来的，v8 只用 aoe2mod.api。",
        "验证要点：A 村民 1000 血且派活后不变；B 城堡里长弓兵仍在；"
        "C 黑暗时代兵营就有蔷琵侦察兵按钮。",
    ])


def check(name, ok, detail=""):
    global fails
    print("  %-62s %s" % (name, "PASS" if ok else "FAIL"))
    if detail:
        print("      %s" % detail)
    if not ok:
        fails += 1


fails = 0
print("building %s" % TITLE)
print("  title: %d UTF-8 bytes (engine truncates at 100)"
      % len(TITLE.encode("utf-8")))
assert len(TITLE.encode("utf-8")) <= 100, "title too long for the engine"

if os.path.isdir(OUT):
    shutil.rmtree(OUT)

tk = A.open_toolkit(game_root=GAME)

print()
print("1  the two sentences, as a user would type them")
SENTENCES = [
    {"intent": "unit.stat", "unit": "村民", "stat": "hit_points", "value": 1000},
    {"intent": "unit.availability", "unit": UNIT, "civ": "British",
     "action": "grant"},
]
for s in SENTENCES:
    print("     %s" % json.dumps(s, ensure_ascii=False))
prev = tk.plan_bundle(SENTENCES)
print("     preview: edit_count=%s  changes_dat=%s  dat_is_carrier=%s"
      % (prev["edit_count"], prev["changes_dat"], prev["dat_is_carrier"]))

print()
print("2  build")
man = tk.build_bundle(SENTENCES, OUT, title=TITLE, author="dsh",
                      description=DESC, overwrite=True)
rels = sorted(f.get("rel") for f in (man.get("files") or []))
for r in rels:
    print("     %s" % r)

print()
print("3  all four layers landed")
check("the .dat is in the mod", bool(man.get("dat")))
check("the civ tech tree file is there",
      any(r.endswith("CivTechTrees/BRITONS.json") for r in rels), rels)
check("the build panel is there", any(r.endswith("futuravailableunits.json")
                                      for r in rels), rels)
check("the manifest does not call the .dat a mere carrier",
      man.get("dat_is_carrier") is False, repr(man.get("dat_is_carrier")))
check("and the preview agreed with the build on both flags",
      prev["changes_dat"] == (man.get("dat_is_carrier") is not True)
      and prev["dat_is_carrier"] == man.get("dat_is_carrier"),
      "preview=%s/%s build=%s/%s" % (prev["changes_dat"],
                                     prev["dat_is_carrier"],
                                     man.get("dat_is_carrier"),
                                     man.get("changes_dat")))
check("the preview's edit count is the build's edit count",
      prev["edit_count"] == man.get("edit_count"),
      "preview=%s build=%s" % (prev["edit_count"], man.get("edit_count")))

print()
print("4  the .dat half reported what it did")
halves = man.get("dat_half") or []
for rep in halves:
    print("     tech %s (%s): %s"
          % (rep.get("tech"), rep.get("anchor_name"),
             ", ".join(str(e.get("what")) for e in (rep.get("edits") or []))))
check("both availability and availability's .dat half ran",
      len(halves) == 1 and halves[0].get("ok") is True, repr(halves)[:200])
if halves and halves[0].get("ok"):
    _h = halves[0]
    check("the anchor is the 0:00 technology, not the age-gated one",
          _h.get("anchor_name") == "C-Bonus, +25% Shepherd",
          repr(_h.get("anchor_name")))
    check("the anchor's own commands were carried",
          _h.get("effect", {}).get("carried_commands") == 2,
          repr(_h.get("effect")))
    check("EnablingResearch was read but NOT written",
          _h.get("enabling_research", {}).get("written") is False,
          repr(_h.get("enabling_research")))
    check("the button moved off the militia-line slot",
          _h.get("button", {}).get("now") == 4,
          repr(_h.get("button")))

print()
print("5  the emitted JSON really carries the new abilities")
_json_p = os.path.join(OUT, "resources", "_common", "dat",
                       "CivTechTrees", "BRITONS.json")
_blob = json.loads(open(_json_p, encoding="utf-8-sig").read())
_rows = [r for r in (_blob.get("civ_techs_units") or [])
         if r.get("Node ID") == UNIT]
check("the British tree now has a row for unit 2550", len(_rows) == 1,
      repr(_rows)[:200])
if _rows:
    _r = _rows[0]
    check("and it is a Dark Age row at the Barracks",
          _r.get("Age ID") == 1 and _r.get("Building ID") == 12,
          "Age ID=%s Building ID=%s" % (_r.get("Age ID"), _r.get("Building ID")))
    check("and it is immediately buildable (ResearchedCompleted)",
          _r.get("Node Status") == "ResearchedCompleted",
          repr(_r.get("Node Status")))

print()
print("6  CONTROL B -- the Longbowman is untouched")
import aoe2mod.dat.parser as P                                 # noqa: E402
raw, _how = P.load_dat(man["dat"])
pr = P.Parser(raw)
with __import__("contextlib").redirect_stdout(__import__("io").StringIO()):
    pr.parse()
check("the game's own decompressor rebuilds it and it parses to EOF",
      pr.r.pos == len(raw), "%d of %d" % (pr.r.pos, len(raw)))
check("tech 263 still points at effect 251",
      pr.stats["techs"][263]["effect_id"] == 251,
      repr(pr.stats["techs"][263]["effect_id"]))

print()
if fails:
    print("V8: %d check(s) failed." % fails)
    sys.exit(1)
print("V8: the PRODUCT API alone builds the mod the user confirmed by hand.")
print("    Install it with:  python _probe/install_dshtest.py %s" % OUT)
