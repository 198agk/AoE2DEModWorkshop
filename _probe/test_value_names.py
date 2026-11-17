# -*- coding: utf-8 -*-
"""A number in a picker says what it is, or it says nothing and stays a number.

WHY THIS PIN EXISTS
-------------------
Reported 2026-11-16, verbatim: 「我发现你这很多这种下拉的选项全是id，很难看懂
是什么东西，没有解释」.  The screenshot showed 步弓手 4 with 「训练出的单位」= 87
and a picker of `#12 12`, `#13 13`, ... `#-1 -1`.  AGE3 prints `87 - 靶场`.

The bug was that the server only asked `fieldlabels.value_name`, which answers
for six task columns and returns None for everything else, so the page fell back
to `"#" + id` on 1,786 of 2,038 pickers.  `aoe2mod/game/valuenames.py` is the
missing table: it says which id space a column lives in.

WHAT THIS PIN REFUSES TO LET SLIP
---------------------------------
  1. the id space is read from the FULL column name, because DeadFish.0/4/8 are
     pictures while DeadFish.1/5/9 are seconds -- naming all twelve as graphics
     would rename a duration as a picture;
  2. a name is only printed when the file really holds one.  -1 has no unit,
     and a column that is just a number (HitPoints, IconID, LanguageDLLName)
     must stay a number: a wrong name is worse than no name, because the player
     edits the value the name claims;
  3. the class names come from the effect tables, not from UNIT_CLASS_ZH:
     39 is 城门 and 35 is 爆破兵, while that older table says 投石手 and 火枪兵;
  4. the picker prints 「名字  编号」 and drops the `#87 87` stutter, which said
     the same number twice and no name at all.

Run: python -X utf8 _probe/test_value_names.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import aoe2mod.game.hotkeys as HK                  # noqa: E402
import aoe2mod.game.valuenames as VN               # noqa: E402
import aoe2mod.ui.server as SRV                    # noqa: E402

# The columns that hold a hotkeys.json `string_index_list` entry.  The two that
# merely have "HotKey" in the name are deliberately absent -- see section 5.
HOTKEY_COLS = ["Creatable.TrainLocations.0.HotKeyID", "ResearchLocations.0.HotKeyID",
               "HotKeyID", "HotKey", "HotKeyFromUnit"]

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


# ---------------------------------------------------------------------------
section("1. the table names the id space, and only where it is checked")
# ---------------------------------------------------------------------------
SPACES = [
    ("Creatable.TrainLocations.0.UnitID", "unit"),
    ("DeadUnitID", "unit"),
    ("Building.StackUnitID", "unit"),
    ("Bird.DropSites.3", "unit"),
    ("StandingGraphic.0", "graphic"),
    ("DeadFish.0", "graphic"),
    ("DeadFish.4", "graphic"),
    ("AttackGraphic2", "graphic"),
    ("SelectionSound", "sound"),
    ("TrainSound", "sound"),
    ("TerrainID", "terrain"),
    ("PlacementTerrain.0", "terrain"),
    ("PlacementSideTerrain.1", "terrain"),
    ("Class", "class"),
    ("Tasks.0.ClassID", "class"),
    ("TechID", "tech"),
    ("Enabled", "bool"),
    ("CanBeBuiltOn", "bool"),
]
for name, want in SPACES:
    got = VN.space(name)
    ck("%s is a %s" % (name, want), got == want, got)

# The corpse block is the reason `space()` takes the whole name: same prefix,
# four meanings, and only the picture slots may be spelled.
BARE = [
    "DeadFish.1", "DeadFish.2", "DeadFish.3", "DeadFish.5", "DeadFish.9",
    "HitPoints", "LanguageDLLName", "IconID", "SortNumber", "HillMode",
    "TerrainRestriction", "Amount", "ID", "Type", "WwiseGatherSoundID",
    "CombatLevelFlag", "HideInEditor", "FlyWithin", "GarrisonCapacity",
]
for name in BARE:
    ck("%s stays a number" % name, VN.space(name) is None, VN.space(name))

ck("an empty name is not a space", VN.space("") is None and VN.space(None) is None)
ck("each space has a Chinese label",
   [VN.space_zh(s) for s in ("unit", "graphic", "sound", "terrain", "class",
                             "tech", "bool")]
   == ["单位编号", "图形编号", "音效编号", "地形编号", "类别编号", "科技编号", "开关"])
ck("an unknown space prints nothing rather than a guess", VN.space_zh("nope") == "")

ck("0 spells 否", VN.bool_name(0) == "否")
ck("1 spells 是", VN.bool_name(1) == "是")
ck("2 and 5 do NOT spell themselves", VN.bool_name(2) is None and VN.bool_name(5) is None,
   (VN.bool_name(2), VN.bool_name(5)))

# ---------------------------------------------------------------------------
section("2. the shipped file really holds those names")
# ---------------------------------------------------------------------------
app = SRV.App()
app.tk._ensure()

# The two that the report pointed at: a 87 is 靶场, and the picker under
# 「训练出的单位」 is the one that read `#87 87`.
FACTS = [
    ("Creatable.TrainLocations.0.UnitID", 87, "靶场"),
    ("UnitID", 103, "铁匠铺"),
    ("DeadUnitID", 152, "SPRMN_D"),
    ("StandingGraphic.0", 1102, "SPRMN_W0"),
    ("DeadFish.0", 1106, "SWDMN_A1"),
    ("SelectionSound", 420, "civs.wav"),
    ("TerrainID", 1, "Water, Shallow"),
    ("PlacementTerrain.0", 1, "Water, Shallow"),
    ("TechID", 67, "锻造"),
]
for name, v, want in FACTS:
    got = app._stored_name(name, v)
    ck("%s %s is %s" % (name, v, want), got == want, got)

# The class space is the one that had a WRONG table available: UNIT_CLASS_ZH
# says 投石手 for 39 and 火枪兵 for 44/35.  The data says otherwise.
CLS = [(52, "塔"), (39, "城门"), (27, "城墙"), (35, "爆破兵"), (44, "火枪手"),
       (18, "僧侣"), (23, "征服者"), (6, "步兵")]
for cid, want in CLS:
    got = app._stored_name("Class", cid)
    ck("class %d is %s" % (cid, want), got == want, got)
ck("the class table is the effect tables, not UNIT_CLASS_ZH",
   app._stored_name("Class", 39) != "投石手" and app._stored_name("Class", 35) != "火枪兵")

ck("1 is 是 in a real switch column", app._stored_name("Enabled", 1) == "是")
ck("0 is 否 in a real switch column", app._stored_name("Enabled", 0) == "否")
ck("-1 has no unit, so it prints nothing", app._stored_name("UnitID", -1) is None)
ck("-1 has no class either", app._stored_name("Class", -1) is None)
ck("a plain number column is not spelled",
   app._stored_name("HitPoints", 40) is None
   and app._stored_name("IconID", 12) is None
   and app._stored_name("TerrainRestriction", 3) is None)
ck("the sound hash columns are left as numbers",
   app._stored_name("WwiseGatherSoundID", 12345) is None)

sizes = dict((k, len(app._id_names(k))) for k in
             ("unit", "tech", "graphic", "sound", "terrain", "class"))
ck("every space is populated from the file",
   all(n > 50 for n in sizes.values()), sizes)
ck("the four spaces are the four tables",
   sizes["sound"] == 439 and sizes["terrain"] == 200 and sizes["class"] == 62, sizes)

# ---------------------------------------------------------------------------
section("3. the route ships the space and the name with the row")
# ---------------------------------------------------------------------------
d = app.unit_fields(4, civ="British")
rows = d["fields"]
ck("步弓手 4 still reads", d.get("name") == "步弓手", d.get("name"))
withpicker = [r for r in rows if r.get("seen")]
named = [r for r in withpicker if any(nm and nm[0] != "#"
                                     for nm in (r.get("seen_names") or {}).values())]
ck("most pickers now carry a name, not just a number",
   len(named) * 100 // max(1, len(withpicker)) >= 35,
   "%d of %d" % (len(named), len(withpicker)))

spaces = sorted(set(r.get("seen_space_zh") for r in withpicker))
ck("the shipped spaces are the checked ones",
   set(["单位编号", "图形编号", "音效编号", "地形编号", "类别编号", "开关"])
   <= set(spaces), spaces)
ck("a bare column ships an empty space",
   all(r.get("seen_space_zh") == "" for r in withpicker
       if r["name"] in ("HitPoints", "IconID", "LanguageDLLName")))

by = dict((r["name"], r) for r in rows)
units_col = None
for nm, r in by.items():
    if nm.endswith(".UnitID") or nm == "UnitID":
        units_col = r
        break
ck("a UnitID row says 单位编号", units_col is not None and
   units_col.get("seen_space_zh") == "单位编号")
ck("and its values are named, not numbered",
   units_col is not None and
   any(v and v[0] != "#" for v in units_col["seen_names"].values()),
   units_col and list(units_col["seen_names"].items())[:3])
ck("an unnamed value keeps the old sentinel so the page can tell",
   units_col is not None and
   all(v for v in units_col["seen_names"].values()), units_col and units_col["seen_names"])

# ---------------------------------------------------------------------------
section("4. the page prints 名字 编号, and drops the #87 87 stutter")
# ---------------------------------------------------------------------------
PAGE = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
               encoding="utf-8").read()
ck("the name in the value cell is its own span",
   'const sp = el("span", "vname", spelledFor(f, spelled));' in PAGE)
ck("the span carries the space and the equation in its tooltip",
   'sp.title = (f.seen_space_zh ? f.seen_space_zh + "：" : "")' in PAGE)
ck("the picker names its space first",
   'sel.title = [(f.seen_space_zh ? "这是" + f.seen_space_zh + "。" : "")' in PAGE)
ck("an option prints the name and the number",
   'nm.charAt(0) === "#" ? k : (spelledFor(f, nm) + "  " + k)' in PAGE)
ck("it no longer prints #87 87", '("#" + k) : (nm + " " + k)' not in PAGE)
ck("the span is styled to fit inside the cell",
   "#editor table.f td.v > span.vname {" in PAGE
   and "text-overflow: ellipsis" in PAGE.split("span.vname {")[1][:400])

# ---------------------------------------------------------------------------
section("5. a hotkey number says which key, and which action that key runs")
# ---------------------------------------------------------------------------
# Reported 2026-11-16, verbatim: 「所以这个热键编号全是数字，我怎么知道这些数字
# 代表的是那个热键，就是哪个键位」.  The column is `HotKeyID`, the number is an
# index into hotkeys.json's `string_index_list`, the NAME comes from
# name_string_id, and the KEY comes from defaults_list["definitive"] -- NOT from
# the first letter of that name, which is the community rule of thumb and is
# stale for this build (16083's name starts with 'A' while the game binds Q).
for name in HOTKEY_COLS:
    ck("%s is a hotkey column" % name, VN.space(name) == "hotkey", VN.space(name))
ck("the space is called 热键编号", VN.space_zh("hotkey") == "热键编号",
   VN.space_zh("hotkey"))
# The two hotkey-adjacent columns are deliberately NOT in the space, and that
# refusal is the point: neither holds a hotkeys.json index.
for name in ("LanguageDLLHotKeyText", "Creatable.ButtonHotkeyAction"):
    ck("%s is not spelled as a hotkey" % name, VN.space(name) is None, VN.space(name))

# 「你这个名字不需要，很多都是共用同一串编码的，我只需要知道这些编码指的是什么
# 热键」 -- so the answer is the key letter alone.  One id serves several commands
# (16101 is the unique-unit key on the castle, the dock AND the siege workshop),
# which is exactly why the name cannot be trusted and the key can.
HK_FACTS = [
    (16101, "Q"),
    (16131, "S"),
    (16128, "W"),
    (16135, "Q"),
    (16164, "Z"),
    (16186, "X"),
    (16083, "Q"),
]
for sid, want in HK_FACTS:
    got = app._stored_name("Creatable.TrainLocations.0.HotKeyID", sid)
    ck("hotkey %d is the key %s, with no command name" % (sid, want),
       got == want, got)
ck("a spelled hotkey is one or two characters, never a sentence",
   all(len(w) <= 2 for _s, w in HK_FACTS),
   [w for _s, w in HK_FACTS])
ck("16000 is the no-hotkey sentinel, said in words",
   app._stored_name("Creatable.TrainLocations.0.HotKeyID", 16000) == "没设热键")
ck("an unmapped 155xxx id stays a number",
   app._stored_name("Creatable.TrainLocations.0.HotKeyID", 155000) is None)
ck("and so does -1", app._stored_name("Creatable.TrainLocations.0.HotKeyID", -1) is None)
ck("the key is the definitive preset, not the string's first letter",
   app._stored_name("Creatable.TrainLocations.0.HotKeyID", 16083) != "A",
   app._stored_name("Creatable.TrainLocations.0.HotKeyID", 16083))
ck("and the command name never rides along with it",
   "弓手系" not in (app._stored_name("Creatable.TrainLocations.0.HotKeyID",
                                    16083) or ""))
ck("a machine with no hotkeys.json answers with an empty table, not a crash",
   HK.entries("/nonexistent-game-root", None) == {})

# The unit pane: the row's OWN hotkey must be spelled even though the census
# stops at 24,000 records and never saw this one (unit 4's 16083 was absent).
u4 = dict((r["name"], r) for r in app.unit_fields(4, civ="British")["fields"])
hkrow = u4.get("Creatable.TrainLocations.0.HotKeyID") or {}
ck("步弓手 4 has a hotkey row", bool(hkrow), list(u4)[:3])
ck("the row says 热键编号", hkrow.get("seen_space_zh") == "热键编号",
   hkrow.get("seen_space_zh"))
ck("its own value is in the list it ships",
   str(hkrow.get("value")) in (hkrow.get("seen") or {}), hkrow.get("value"))
ck("and that value is spelled as its key, not put back to #16083",
   (hkrow.get("seen_names") or {}).get(str(hkrow.get("value"))) == "Q",
   (hkrow.get("seen_names") or {}).get(str(hkrow.get("value"))))

# The tech pane: 263 observed hotkeys is too many for a dropdown, so the LIST is
# refused -- and the one name that matters travels alone as `value_name`.
t67 = dict((r["name"], r) for r in app.tech_fields(67)["fields"])
thk = t67.get("ResearchLocations.0.HotKeyID") or {}
ck("锻造 67 has a research hotkey row", bool(thk), list(t67)[:3])
ck("a 263-value column ships no dropdown", not thk.get("seen"), len(thk.get("seen") or {}))
ck("but it still spells the value on this row",
   thk.get("value_name") == "Q", thk.get("value_name"))
ck("and says which space that number lives in",
   thk.get("seen_space_zh") == "热键编号", thk.get("seen_space_zh"))
ck("the page prints a lone name too, not only a dropdown one",
   "(f.value_name || null)" in PAGE)
# A hotkey is the one space spelled with a single letter.  Beside a number a
# lone 「Q」 reads as a stray character, so the page says 「Q 键」 -- the key,
# without naming which of the several commands sharing that id was meant.
ck("a hotkey letter is drawn as a key, not as a stray character",
   "function spelledFor(f, spelled)" in PAGE and '" 键"' in PAGE,
   PAGE.count('spelledFor'))
ck("both the value cell and the picker go through that formatter",
   PAGE.count('spelledFor(f, ') >= 2, PAGE.count('spelledFor(f, '))

# ---------------------------------------------------------------------------
print()
if FAILED:
    print("VALUE NAMES: %d FAILED -> %r" % (len(FAILED), FAILED[:6]))
    sys.exit(1)
print("VALUE NAMES: A NUMBER SAYS WHICH SPACE IT LIVES IN AND WHAT IT IS "
      "CALLED -- AND THE COLUMNS THAT ARE JUST NUMBERS STILL SAY ONLY THE NUMBER")