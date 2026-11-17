# -*- coding: utf-8 -*-
"""The other direction: a record's neighbours, read out of the file instead of
guessed from its name.

WHY THIS PIN EXISTS
-------------------
Reported 2026-11-16, verbatim: 「我想的是能把关联的直接搜出来，比如我搜铁匠铺，
就能显示出这个铁匠铺有关的东西」.

A .dat points ONE WAY ONLY.  A technology names the building it is researched
at (research_locations[].location_id); a unit names the hoard that shows its
button (train_locations[].unit_id).  Nothing points back, so "what is related
to 铁匠铺" can only be answered by walking every record once and turning the
arrows around -- which is what aoe2mod/semantic/relations.py does, cached per
file generation.

FOUR THINGS THIS PIN REFUSES TO LET SLIP
----------------------------------------
  1. the tables are DERIVED, not typed: the numbers below are the shipped
     file's, and the pin compares against a fresh build() rather than a
     hand-written table that could drift;
  2. the three id spaces do not mix.  target_kind is filtered to "unit", so a
     class row can never print 骆驼投石机 as something 锻造 changes;
  3. a repeated name is announced.  铁匠铺 is FIVE records (18, 19, 103, 105,
     2441) and only 103 carries the fifteen technologies -- opening the first
     one used to look like a broken feature;
  4. the pane draws chips, not names, because every entry is a record the
     screen can open.

Run: python -X utf8 _probe/test_relations.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import aoe2mod.api as A                              # noqa: E402
import aoe2mod.ui.server as SRV                     # noqa: E402
from aoe2mod.semantic import relations as R         # noqa: E402

FAILED = []


def ck(what, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", what,
                         (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILED.append(what)
    return ok


def section(title):
    print()
    print("=== %s ===" % title)


tk = A.open_toolkit()
_ = tk.version
MAPS = R.build(tk)
IX = tk.index()


def groups(kind, uid):
    return R.for_record(kind, uid, MAPS, IX)


def keys_of(kind, uid):
    return [g["key"] for g in groups(kind, uid)]


def total_of(kind, uid, key):
    for g in groups(kind, uid):
        if g["key"] == key:
            return g["total"]
    return None


# ---------------------------------------------------------------------------
section("1. the tables are built from the file, and every arrow is reversed")
# ---------------------------------------------------------------------------
ck("build() returns every table, the reverse class map included", sorted(MAPS) ==
   ["class_mod", "class_units", "classes", "clsname", "modified", "research",
    "targets", "train", "ucls", "utypes"], sorted(MAPS))
_pairs = 0
for bi, techs in MAPS["research"].items():
    for ti in techs:
        _pairs += 1
ck("the research table is keyed by building and the pairs are real",
   _pairs > 100 and all(isinstance(bi, int) for bi in MAPS["research"]), _pairs)
_probe = MAPS["targets"].get(67) or []
ck("targets and modified are inverse maps",
   bool(_probe) and all(67 in (MAPS["modified"].get(u) or []) for u in _probe), _probe)
ck("train is keyed by the hoard, not by the product",
   all(isinstance(k, int) and isinstance(v, list) for k, v in MAPS["train"].items())
   and len(MAPS["train"]) > 5, len(MAPS["train"]))

# ---------------------------------------------------------------------------
section("2. the three id spaces stay apart")
# ---------------------------------------------------------------------------
ck("the class rows are kept as names", MAPS["classes"].get(67) ==
   ["步兵", "双手剑士", "骑兵", "长枪兵", "长矛兵", "侦察兵"], MAPS["classes"].get(67))
ck("and they are NOT in the unit list", MAPS["targets"].get(67) ==
   [1923, 1831, 2626, 2627, 2628], MAPS["targets"].get(67))
_names = [IX.units[u].display for u in (MAPS["targets"].get(67) or []) if IX.units.get(u)]
ck("no class name leaked into the unit rows", "步兵" not in _names, _names)
ck("every target id is a real unit record",
   all(IX.units.get(u) is not None for u in (MAPS["targets"].get(67) or [])),
   MAPS["targets"].get(67))

# ---------------------------------------------------------------------------
section("3. the groups say which way the arrow runs")
# ---------------------------------------------------------------------------
# 103 铁匠铺 is class 3 (建筑), and exactly one technology names that whole class,
# so a third group appears and it is NOT noise -- see section 7.
ck("铁匠铺 103 is researched at, built by someone, and one tech names its class",
   keys_of("unit", 103) == ["research_here", "built_by", "modified_by_class"],
   keys_of("unit", 103))
ck("fifteen technologies are offered there",
   total_of("unit", 103, "research_here") == 15,
   total_of("unit", 103, "research_here"))
ck("the label says the direction out loud, and names the class it means",
   [g["label"] for g in groups("unit", 103)] ==
   ["在这里研究的科技", "谁造的", "改它这一类（建筑）的科技"],
   [g["label"] for g in groups("unit", 103)])
ck("a building is BUILT, a unit is TRAINED -- two different words",
   R.is_building(103, MAPS) and not R.is_building(74, MAPS) and
   "trained_at" in keys_of("unit", 74) and "built_by" not in keys_of("unit", 74),
   keys_of("unit", 74))
ck("锻造 67 lists its building, its classes, its units and the records behind those classes",
   keys_of("tech", 67) == ["researched_at", "classes", "targets", "class_members"],
   keys_of("tech", 67))
ck("and the building is one record", total_of("tech", 67, "researched_at") == 1,
   total_of("tech", 67, "researched_at"))
_castle = groups("unit", 82)
_rh = [g for g in _castle if g["key"] == "research_here"][0]
ck("城堡 has 211 technologies but the route sends 24",
   _rh["total"] == 211 and len(_rh["items"]) == 24, (_rh["total"], len(_rh["items"])))
ck("the cut is reported, not silent", _rh["total"] > len(_rh["items"]))
ck("an unfiled record answers an empty list, not a crash",
   groups("unit", 2) == [], groups("unit", 2))

# ---------------------------------------------------------------------------
section("4. a repeated name is announced, not left looking broken")
# ---------------------------------------------------------------------------
ck("103 knows the other three 铁匠铺",
   [s["id"] for s in R.siblings("unit", 103, IX)] == [18, 19, 105],
   [s["id"] for s in R.siblings("unit", 103, IX)])
ck("and 18 knows the rest, never itself",
   [s["id"] for s in R.siblings("unit", 18, IX)] == [19, 103, 105],
   [s["id"] for s in R.siblings("unit", 18, IX)])
_sib_castle = R.siblings("unit", 82, IX)
ck("城堡's siblings are 城堡 too",
   [s["id"] for s in _sib_castle] == [235, 2418]
   and all(s["name"] == "城堡" for s in _sib_castle), [s["id"] for s in _sib_castle])
ck("technologies repeat too, and are found the same way",
   [s["id"] for s in R.siblings("tech", 7, IX)] == [482] and
   [s["id"] for s in R.siblings("tech", 482, IX)] == [7])
ck("a unique name has no siblings", R.siblings("tech", 67, IX) == [])
ck("a sibling always carries a name",
   all(s["name"] for s in R.siblings("unit", 103, IX)))

# ---------------------------------------------------------------------------
section("5. the route answers the screen's question")
# ---------------------------------------------------------------------------
APP = SRV.App()
_j = APP.relations("unit", "103")
ck("the route says ok and names the record", _j["ok"] and _j["name"] == "铁匠铺",
   _j.get("name"))
ck("it ships the groups and the siblings together",
   sorted(_j) == ["groups", "id", "kind", "name", "ok", "siblings"], sorted(_j))
_j2 = APP.relations("unit", "abc")
ck("a non-number id is refused with a sentence, not a traceback",
   _j2.get("ok") is False and "abc" in _j2.get("error", ""), _j2.get("error"))
ck("an unknown kind falls back to the unit table",
   APP.relations("building", "103")["kind"] == "unit")
ck("an unknown id answers empty groups, not an exception",
   APP.relations("unit", "999999")["groups"] == [])
ck("the same record answers identically twice -- no shared mutable state",
   APP.relations("unit", "103") == _j)

# ---------------------------------------------------------------------------
section("6. the pane draws doors, not a wall of names")
# ---------------------------------------------------------------------------
PAGE = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
               encoding="utf-8").read()
ck("the box is a strip tool like the other five",
   'edTool(tools, "edrel", "有关的东西"' in PAGE)
ck("it is the FIRST box in the strip",
   PAGE.index('"edrel"') < PAGE.index('"edrecbox"'))
ck("every entry is a button that opens a record",
   "function relChip(kind, id, name, isOn)" in PAGE and
   "b.onclick = () => edRelGo(kind, id, name);" in PAGE)
ck("a class entry is text, never a door",
   'el("span", "edrele", it.name + "（整类）")' in PAGE)
ck("the sibling line is drawn before the groups",
   PAGE.index('"同名的还有 "') < PAGE.index('g.label + " " + g.total'))
ck("a cut list says how many were left out", " 条没列" in PAGE)
ck("a cut list carries a door that lists the rest in place, no reload",
   "function relCut(row, kind, id, g)" in PAGE and
   "看全部 " in PAGE and
   "row.textContent = \"\";" in PAGE)
ck("that door asks for ONE group and asks for no cut",
   "&group=\" + encodeURIComponent(g.key) + \"&limit=0\"" in PAGE)
ck("the box stays SHUT until asked -- a 320px wall over the fields",
   "rel.box.open = true;" not in PAGE)
ck("a cross-space jump moves the tab and the list with the pane",
   "ED_WANT = id;" in PAGE and "edKind(want);" in PAGE)
ck("the box scrolls instead of growing the strip",
   "#editor .edtools #edrel .fxbody { max-height: 320px; overflow: auto; }" in PAGE)
ck("what the box does NOT know is said on screen",
   "科技的前置条件不在这张图里。" in PAGE)


# ---------------------------------------------------------------------------
section("7. a technology that names a CLASS reaches the records inside it")
# ---------------------------------------------------------------------------
# Reported 2026-11-16, verbatim: 「这个不是会作用于塔类吗，为什么没有相关项没有塔，
# 塔那边相关项也没用这个科技，你全部复查一遍，我这是找了个特例」.  996 强化堡垒 has
# eight commands: five name units (82 城堡, four 城镇中心) and three name CLASSES
# (27 城墙, 52 塔, 39 城门).  A class row used to be a dead end in both
# directions -- the tech said 「塔（整类）」 and no tower said 996.
ck("996 names the tower class, not any single tower",
   "塔" in (MAPS["classes"].get(996) or []) and
   79 not in (MAPS["targets"].get(996) or []),
   (MAPS["classes"].get(996), MAPS["targets"].get(996)))
_cm996 = [g for g in groups("tech", 996) if g["key"] == "class_members"][0]
_cm_ids = [i["id"] for i in _cm996["items"]]
ck("the records behind that class are listed, so a tower shows up",
   _cm996["total"] == 118 and 79 in _cm_ids and 235 in _cm_ids,
   (_cm996["total"], _cm_ids[:6]))
ck("and they are real records with names, not class names",
   IX.units[79].display == "瞭望箭塔" and "塔" not in
   [i["name"] for i in _cm996["items"]])
_via79 = [g for g in groups("unit", 79) if g["key"] == "modified_by_class"][0]
ck("the tower answers back: 996 is among the techs that change its class",
   996 in [i["id"] for i in _via79["items"]], _via79["total"])
ck("the two 改 groups are kept apart, and the class one says which class",
   [g["label"] for g in groups("unit", 79)] ==
   ["谁造的", "改它的科技", "改它这一类（塔）的科技"],
   [g["label"] for g in groups("unit", 79)])
ck("a tech named DIRECTLY is not repeated in the class group",
   not (set(MAPS["modified"].get(79) or []) &
        set(i["id"] for i in _via79["items"])))
ck("a record named directly is not repeated under its class either",
   not (set(MAPS["targets"].get(996) or []) & set(_cm_ids)))
ck("an unnamed class still answers, under a made-up name",
   MAPS["clsname"].get(64) == "第 64 类" and
   [g["label"] for g in groups("unit", 2607)] == ["改它这一类（第 64 类）的科技"],
   [g["label"] for g in groups("unit", 2607)])
ck("a class with no visible member invents no group",
   all(not [u for u in MAPS["class_units"].get(c, ())
            if IX.units.get(u) is not None and IX.units[u].is_visible]
       for c in (45, 46, 50)) and
   all("members" not in [g["key"] for g in groups("class", c)]
       for c in (45, 46, 50)))
ck("the class itself can be asked what is inside it",
   [i["id"] for i in groups("class", 52)[0]["items"]] ==
   [79, 190, 234, 235, 236, 684, 685, 785, 1102, 1665],
   [i["id"] for i in groups("class", 52)[0]["items"]])
ck("the new group is cut and reopened like every other one",
   [(g["total"], len(g["items"])) for g in groups("tech", 996)
    if g["key"] == "class_members"] == [(118, 24)])
ck("the route answers kind=class instead of falling back to units",
   APP.relations("class", "52")["kind"] == "class" and
   APP.relations("class", "52")["groups"][0]["key"] == "members")
# ---------------------------------------------------------------------------
print()
if FAILED:
    print("RELATIONS: %d FAILED -> %r" % (len(FAILED), FAILED[:6]))
    sys.exit(1)
print("RELATIONS: A RECORD'S NEIGHBOURS COME OUT OF THE FILE, IN BOTH "
      "DIRECTIONS, WITH THE ID SPACES KEPT APART AND THE REPEATED NAMES ANNOUNCED")
