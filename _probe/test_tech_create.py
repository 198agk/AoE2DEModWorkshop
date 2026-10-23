# -*- coding: utf-8 -*-
"""Can a sentence append a technology the game does not have?

Run: python _probe/test_tech_create.py

Why this file exists
--------------------
`_probe/test_new_tech.py` proves the MODULE works: given a clone request, it
appends a record and the 93 MB stream still parses.  That file cannot tell you
whether a player can ask for it, and it cannot tell you whether the product
writes what it promised.  Both failures are quiet:

  * the reader could refuse every sentence about a new technology (it did, until
    2026-10-22: `照织布机做一个新科技` was answered "这句话没说要照着哪个单位做" --
    a refusal about a UNIT for a sentence about a TECHNOLOGY);
  * the preview could promise files the build does not write, which is the same
    defect class this project keeps paying for.

So this nails the PATH a player takes: sentence -> intent -> preview -> mod on
disk -> read back from the disk (never from the manifest).

`tech.create` had one honest limit that this file used to assert -- "the engine
has never been shown to draw a card for an index past the shipped count".  That
stopped being true on 2026-10-22: v49 put the created technology on the town
centre's 8th research box and the user read it there.  The limit that is still
true is the opposite direction (a game patch can move the first free id), and
that is what the manifest now has to say.
"""

import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.semantic import index as SI                   # noqa: E402
from aoe2mod.ui import nl                                  # noqa: E402

OUT = os.path.join(HERE, "out_tech_create")
FAILS = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILS.append(name)


def main():
    tk = A.open_toolkit()
    ix = SI.index()
    vocab = nl.Vocabulary(ix.units, ix.techs)

    def read(text):
        return nl.read(text, vocab, civ_names=tk.civ_names, civ_zh=nl.CIV_ZH,
                       effect_count=tk.effect_count,
                       unit_class=tk.unit_class)

    # ---- A. the sentence layer ---------------------------------------------
    # Every phrasing below is one a player actually types.  The first four must
    # all land on `tech.create`; the last two must stay what they are.
    print("A. a Chinese sentence asks for a new technology")
    wanted = [
        ("照织布机做一个新科技叫铁匠学徒的手艺", 22, "铁匠学徒的手艺"),
        ("做一个新科技，照着锻造，名字叫做熔炉改良", 67, "熔炉改良"),
        ("新建一项科技，参考织布机，叫快速采集", 22, "快速采集"),
        ("给城镇中心加一项新科技，照着织布机，叫铁匠学徒", 22, "铁匠学徒"),
    ]
    for text, donor, name in wanted:
        ints, _cl = read(text)
        got = ints[0] if ints else {}
        check("%s -> tech.create" % text,
              got.get("intent") == "tech.create", json.dumps(ints, ensure_ascii=False))
        check("and copies technology %d" % donor, got.get("donor") == donor,
              repr(got.get("donor")))
        check("and is called %r" % name, got.get("name") == name, repr(got.get("name")))

    # A technology is not per-civilization: the shipped file carries civ = -1 on
    # all 1,510 of them.  Demanding one would refuse a true sentence.
    ints, _cl = read("照织布机做一个新科技叫铁匠学徒的手艺")
    check("a technology needs no civilization",
          "civ" not in (ints[0] if ints else {}), json.dumps(ints, ensure_ascii=False))

    # A named BUILDING moves the research card.  Without this the clone inherits
    # the donor's card even when the player said otherwise.
    ints, _cl = read("给城镇中心加一项新科技，照着织布机，叫铁匠学徒")
    check("a named building moves the research card",
          (ints[0] if ints else {}).get("building") is not None,
          json.dumps(ints, ensure_ascii=False))

    # A research time is a property of the new thing, and it must not be read as
    # hit points (the number means HP in a unit creation).
    ints, _cl = read("照织布机做一个新科技叫快速采集，研究时间20")
    check("a research time is read as a research time",
          (ints[0] if ints else {}).get("research_time") == 20,
          json.dumps(ints, ensure_ascii=False))
    check("and is not read as hit points",
          "hp" not in (ints[0] if ints else {}), json.dumps(ints, ensure_ascii=False))

    # The two neighbours must not be captured: an ordinary stat edit, and a unit
    # creation (which really needs a civilization).
    ints, _cl = read("把村民的血量改成1000")
    check("an ordinary edit is still an edit",
          (ints[0] if ints else {}).get("intent") == "unit.stat",
          json.dumps(ints, ensure_ascii=False))
    ints, _cl = read("给不列颠新建一个单位，照着村民，名字叫做铁匠学徒")
    check("a unit creation is still a unit creation",
          (ints[0] if ints else {}).get("intent") == "unit.create",
          json.dumps(ints, ensure_ascii=False))

    # Refusals have to name the thing the player was asked for: a sentence about
    # a technology may not be told it forgot a "unit".
    ints, cl = read("新建一个科技加进不列颠")
    why = (cl[0].why if cl else "")
    check("a creation with no donor is refused", not ints, json.dumps(ints, ensure_ascii=False))
    check("and the refusal says 科技, not 单位", "科技" in why, why)
    check("and it does not mention a unit", "单位" not in why, why)

    # ---- B. the preview ----------------------------------------------------
    print("B. the preview says what the build will do")
    intent = {"intent": "tech.create", "donor": 22, "name": "铁匠学徒",
              "research_time": 20, "button": 3}
    plan = tk.plan(intent)
    check("editable", plan.get("editable") is True, repr(plan.get("editable")))
    check("writes the .dat", plan.get("changes_dat") is True, repr(plan.get("changes_dat")))
    check("and is not a carrier", plan.get("dat_is_carrier") is False,
          repr(plan.get("dat_is_carrier")))
    check("edit_count is one", plan.get("edit_count") == 1, repr(plan.get("edit_count")))
    desc = plan.get("description") or ""
    check("the description names the new technology", "铁匠学徒" in desc, desc)
    check("and names the donor", "织布机" in desc, desc)
    check("and says which card it lands on", "研究卡" in desc, desc)
    check("the string id is past the shipped last one",
          plan.get("string_id", 0) > 30030001, repr(plan.get("string_id")))
    warns = " ".join(plan.get("warnings") or [])
    check("the preview warns it will not be in the tech tree", "科技树" in warns, warns)
    check("and warns about the icon", "图标" in warns, warns)
    # Same class of correction as the tree sentence above, one step further: the
    # icon warning first said "the icon ids 0..312 are full, this tool will not
    # touch that layer" (a missing feature dressed as a wall), then "this version
    # does not write the icon layer" -- which stopped being true on 2026-10-23
    # when `tech.create` grew an `icon` field.  What is true now is that the icon
    # is OPTIONAL: leave the field out and the clone draws the donor's picture.
    check("and the icon warning asks for a picture, not a missing layer",
          "图标用" in warns and "还不写" not in warns and "做不到" not in warns, warns)
    check("and it says the clone would otherwise draw the donor's icon",
          "照着做的那个科技" in warns, warns)
    # The reason it is not in the tree must be "this tool does not write that
    # half yet", NOT "the node id is taken".  The old sentence claimed the id
    # collided with the unit `City Gate NE (Rubble)`; measured 2026-10-23, no
    # tree row in any of the 62 civilizations carries node 1510 in either space
    # (`_probe/tmp_tree_for_tech.py`).  A nail that only looked for 科技树 stayed
    # green through that -- which is the whole reason this assertion exists.
    check("and gives an honest reason, not a collision that does not exist",
          "还没动" in warns and "共用" not in warns and "已经是单位" not in warns,
          warns)
    check("   and does not name the unit that no tree row has",
          "City Gate" not in warns and "CityGate" not in warns, warns)

    # ---- C. the mod on disk ------------------------------------------------
    print("C. the mod on disk really has the record")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    man = tk.build(intent, OUT, title="dsh test tech create nail", author="dsh",
                   overwrite=True)
    dat_path = os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")
    check("the .dat is in the mod", os.path.isfile(dat_path), dat_path)
    check("the manifest says the .dat changed", man.get("changes_dat") is True, "")
    shipped_bytes = 93268152
    check("and the file grew by one record",
          man.get("dat_raw_bytes", 0) > shipped_bytes,
          "%s vs %s" % (man.get("dat_raw_bytes"), shipped_bytes))

    # Read the SHIPPED-BYTES back from the disk rather than trusting the manifest.
    raw2, how2 = A.P.load_dat(dat_path)
    check("the emitted file inflates", bool(raw2), how2)
    civs2, civs_start2, gv2, tail2 = A.L.locate(raw2)
    recs2 = A.L.locate_techs(raw2, tail2, gv2)
    check("there is one more technology than shipped", len(recs2) == 1511, str(len(recs2)))
    rec = recs2[1510] if len(recs2) > 1510 else {}
    check("the new record reads back its display string id",
          rec.get("lang_name") == plan.get("string_id"),
          "%r vs %r" % (rec.get("lang_name"), plan.get("string_id")))
    locs = rec.get("research_locations") or []
    check("with the research box it was given",
          len(locs) == 1 and locs[0].get("research_time") == 20
          and locs[0].get("button_id") == 3,
          json.dumps(locs, ensure_ascii=False))
    # The name itself ships in a key-value table, because that is the ONLY way
    # the game learns a string id it does not have (the file's own 605-byte
    # instructions say so).
    zh = os.path.join(OUT, "resources", "zh", "strings", "key-value",
                      "key-value-modded-strings-utf8.txt")
    check("the mod ships the name", os.path.isfile(zh), zh)
    if os.path.isfile(zh):
        body = io.open(zh, encoding="utf-8").read()
        check("and the table defines the new string",
              "%d " % plan["string_id"] in body or '%d "' % plan["string_id"] in body, body)
        check("and the table has exactly one instructions banner",
              body.count("//INSTRUCTIONS:") == 1, body[:200])

    # A box is shared, not owned: 66 shipped (building, button) pairs hold two
    # or more technologies.  The preview must say who else is in the box, or the
    # player meets two technologies on one button and cannot tell whether they
    # broke something.
    from aoe2mod.dat import newtech as NT
    _busy = tk.plan({"intent": "tech.create", "donor": 22, "name": "手艺八",
                     "building": 109, "button": 8})
    _wn = " ".join(_busy.get("warnings") or [])
    check("a shared box says which technologies already sit in it",
          "那一格本来已经有" in _wn, _wn[-160:])
    check("and names at least one of them",
          "城镇瞭望" in _wn or "城镇巡逻" in _wn, _wn[-160:])
    _free = tk.plan({"intent": "tech.create", "donor": 22, "name": "手艺单",
                     "building": 109, "button": 1})
    _wf = " ".join(_free.get("warnings") or [])
    check("an unused box does not claim a crowd",
          "那一格本来已经有" not in _wf, _wf[-160:])

    # A sentence that names a BUILDING must not inherit every box that
    # building ever had.  Measured 2026-10-22: the town centre has 18 shipped
    # research locations (8 distinct buttons, each repeated for the technologies
    # that share it), and the first version of this path copied all 18 into the
    # new record -- one technology claiming eighteen boxes at once.  The nail
    # above only ever exercised the DONOR path (`button` alone), which is why
    # nothing caught it.
    for _asked, _want_b in ((109, 3), (103, 2)):
        _rec = NT.add_tech(
            tk._stats, 22, NT.internal_name_for("卡位", 1510), 30030009,
            research_locations=[
                {"location_id": _asked, "research_time": 10,
                 "button_id": _want_b, "hotkey_id": -1}])
        _locs = _rec["record"]["research_locations"]
        check("naming building %d yields exactly one box" % _asked,
              len(_locs) == 1, json.dumps(_locs, ensure_ascii=False))
        check("and it is the box that was asked for (%d)" % _want_b,
              bool(_locs) and _locs[0].get("button_id") == _want_b,
              json.dumps(_locs, ensure_ascii=False))

    _card = tk._tech_locations_by_building(109)
    check("the card helper answers one box, not every box on the card",
          len(_card) == 1, "%d box(es)" % len(_card))
    # 12 (barracks) DOES have a card -- it holds the infantry upgrades -- so the
    # first version of this assertion was asking the wrong building and read as
    # a product defect.  71 and 50 are two of the records that have none: 71 is
    # the town-centre copy the name index hands out, which is exactly why the
    # sibling search exists.
    for _bare in (71, 50):
        check("building %d has no research card at all" % _bare,
              len(tk._tech_locations_by_building(_bare)) == 0,
              "%d box(es)" % len(tk._tech_locations_by_building(_bare)))

    # Every other technology must be untouched.
    shipped_civs, shipped_start, shipped_gv, shipped_tail = A.L.locate(tk._raw)
    shipped_recs = A.L.locate_techs(tk._raw, shipped_tail, shipped_gv)

    def strip(d):
        return {k: v for k, v in d.items() if not k.startswith("_off_")}

    same = sum(1 for i in range(len(shipped_recs))
               if strip(shipped_recs[i]) == strip(recs2[i]))
    check("every shipped technology survived byte for byte",
          same == len(shipped_recs), "%d of %d" % (same, len(shipped_recs)))

    # The honest limit travels with the manifest, not only in a doc.
    #
    # This used to assert "the manifest admits the engine has never drawn it" --
    # which stopped being true on 2026-10-22 (v49 put the created technology on
    # the town centre's 8th research box and the user read it there).  A nail that
    # pins a now-FALSE admission is worse than no nail: it makes the honest limit
    # sound stale, and the next reader deletes the whole `not_proven` field.
    # So pin the limit that remains true instead.
    npro = " ".join((man.get("verification") or {}).get("not_proven") or [])
    check("the manifest still carries an honest limit", npro.strip() != "", npro)
    check("...and it is the game-update risk, which no run has settled",
          "UPDATE" in npro or "update" in npro, npro)
    check("...and it no longer claims the engine has never drawn one",
          "never drawn" not in npro.lower() and "no run has yet" not in npro.lower(),
          npro)

    # ---- D. what is refused ------------------------------------------------
    print("D. impossible requests are refused in Chinese")
    bad = [
        ("a donor that does not exist", {"intent": "tech.create", "donor": 999999,
                                         "name": "x"}),
        ("no name", {"intent": "tech.create", "donor": 22}),
        ("a name the string table cannot hold",
         {"intent": "tech.create", "donor": 22, "name": 'a"b'}),
        ("a research time past the field",
         {"intent": "tech.create", "donor": 22, "name": "x", "research_time": 40000}),
        ("a box past the card",
         {"intent": "tech.create", "donor": 22, "name": "x", "button": 40}),
    ]
    for name, intent in bad:
        try:
            got = tk.plan(intent)
            refused = got.get("editable") is False
            why = got.get("reason") or got.get("description") or ""
        except Exception as exc:                                    # noqa: BLE001
            refused = True
            why = str(exc)
        check("%s is refused" % name, refused, "")
        import re
        latin = [w for w in re.findall(r"[A-Za-z]{2,}", why)
                 if w.lower() not in ("civ", "tech", "dat")]
        check("and the refusal is Chinese", not latin, "%r -> %s" % (latin, why))

    # ---- E. the icon is a real file chain, not a promise --------------------
    # Every link here is silent when wrong: the preview could pick a slot the
    # build never fills, the merged table could be written without the new
    # material, the PNG could be filed where the engine does not look, or the
    # record could keep the donor's icon.  So check the chain end to end and read
    # the tables BACK FROM THE DISK.
    #
    # The Techs section is NOT the Units section.  Measured 2026-10-23 from the
    # only shipped precedent (`[UI]7V1_Three Kingdoms`): its keys start at 500,
    # its textures live under `textures/ingame/tech`, and its added icons are PNG
    # rather than uncompressed DDS.  Reusing the unit shape would write files the
    # engine never asks for and still look green.
    print("E. a picture becomes the new technology's own icon")
    import tempfile
    from aoe2mod.game import ddstex as DD
    from aoe2mod.game import iconart as IA
    from PIL import Image

    _tmp = tempfile.mkdtemp(prefix="techcreate_icon_")
    _side = 256
    _rgba = bytearray()
    for _y in range(_side):
        for _x in range(_side):
            # A pattern, not a flat colour: a decoder that transposes rows or
            # swaps R and B passes on a flat fill.
            _rgba += bytes((_x % 256, _y % 256, (_x * _y) % 256, 255))
    pic = os.path.join(_tmp, "sigil.png")
    io.open(pic, "wb").write(DD.encode_png(_side, _side, bytes(_rgba)))

    _icons0, _mats0 = IA.shipped(tk.game_root)
    _techs0 = dict(_icons0.get("Techs") or {})
    _units0 = dict(_icons0.get("Units") or {})
    _mats0_names = {e["MaterialDef"]["Name"] for e in _mats0["Materials"]}

    icon_intent = {"intent": "tech.create", "donor": 22, "name": "血祭",
                   "button": 4, "icon": pic}
    icon_plan = tk.plan(icon_intent)
    # The SENTENCE has to carry the picture too.  Without this block the whole
    # segment below stays green while the reader silently drops the path -- the
    # player writes 「图标用 <路径>」, the technology is created with the donor's
    # icon, and nothing anywhere says a word was ignored.  (Found by breaking
    # the reader: the nail stayed green, because every other assertion here
    # builds the intent in Python instead of parsing a sentence.)
    _sent = "照着织布机做一个新科技，就叫血祭，图标用 %s" % pic
    _ints, _cls = read(_sent)
    check("a sentence hands the picture to the new technology",
          bool(_ints) and _ints[0].get("intent") == "tech.create"
          and _ints[0].get("icon") == pic,
          json.dumps(_ints, ensure_ascii=False)[:200])
    check("...as one request, not two",
          len(_cls) == 1 and bool(_ints),
          "%d clause(s), %d intent(s)" % (len(_cls), len(_ints)))
    check("the sentence's own plan names the same icon slot",
          bool(_ints) and tk.plan(_ints[0]).get("icon_slot") == icon_plan.get("icon_slot"),
          repr(bool(_ints) and tk.plan(_ints[0]).get("icon_slot")))
    check("the preview accepts a picture", icon_plan.get("editable") is True,
          repr(icon_plan.get("reason")))
    check("and picks a slot past the shipped Techs range",
          (icon_plan.get("icon_slot") or 0) >= IA.FIRST_FREE["tech"],
          repr(icon_plan.get("icon_slot")))
    check("and names the three files it will ship",
          len(icon_plan.get("icon_files") or []) == 3,
          json.dumps(icon_plan.get("icon_files"), ensure_ascii=False))
    # Same contract as the unit side: eleven builds on 2026-10-24 showed the
    # bytes are right and the game draws an empty box, because an icon slot
    # resolves material names against the install directory's table only.  The
    # preview must not read like a promise, and the nail is what keeps a later
    # reader from turning the warning back into an advertisement.
    _iw = " ".join(icon_plan.get("warnings") or [])
    check("and says the game will not draw it, instead of promising a picture",
          "不会把它画出来" in _iw, _iw[:120])
    check("and gives the measurement that settles it",
          "图标用" in _iw or "空框" in _iw or "实测" in _iw, _iw[:120])

    check("and the description says it gets its own icon",
          "自己的图标" in (icon_plan.get("description") or ""),
          (icon_plan.get("description") or "")[:160])

    # A picture that is not a picture must be refused by the PREVIEW.  The build
    # path raises too, but by then the player has waited for 93 MB of work.
    _bad_pic = os.path.join(_tmp, "not_a_picture.png")
    io.open(_bad_pic, "wb").write(b"this is text")
    _bad = tk.plan({"intent": "tech.create", "donor": 22, "name": "坏图",
                    "icon": _bad_pic})
    check("a file that is not a picture is refused before the build",
          _bad.get("editable") is False, repr(_bad.get("editable")))
    check("...with a Chinese reason, not PIL's",
          "不是一张能识别的图片" in (_bad.get("reason") or "")
          and "UnidentifiedImageError" not in (_bad.get("reason") or ""),
          (_bad.get("reason") or "")[:120])

    OUT_ICON = os.path.join(HERE, "out_tech_create_icon")
    if os.path.isdir(OUT_ICON):
        shutil.rmtree(OUT_ICON)
    icon_man = tk.build(icon_intent, OUT_ICON, title="dsh test tech create icon",
                        author="dsh", overwrite=True)
    check("the icon build verifies", (icon_man.get("verification") or {}).get("ok") is True,
          json.dumps((icon_man.get("verification") or {}).get("not_proven"),
                     ensure_ascii=False))
    check("and the record reads back the slot the preview named",
          (icon_man.get("new_tech") or {}).get("icon_slot") == icon_plan.get("icon_slot"),
          "%r vs %r" % ((icon_man.get("new_tech") or {}).get("icon_slot"),
                        icon_plan.get("icon_slot")))

    _icons1 = json.load(io.open(os.path.join(OUT_ICON, "widgetui", "icons.json"),
                                encoding="utf-8"))
    _mats1 = json.load(io.open(os.path.join(OUT_ICON, "widgetui", "materials.json"),
                               encoding="utf-8"))
    _techs1 = _icons1.get("Techs") or {}
    _key = str(icon_plan["icon_slot"])
    check("the shipped Techs keys all survive",
          all(_techs1.get(k) == v for k, v in _techs0.items()),
          "%d of %d" % (sum(1 for k, v in _techs0.items() if _techs1.get(k) == v),
                        len(_techs0)))
    check("and one key was added", len(_techs1) == len(_techs0) + 1,
          "%d -> %d" % (len(_techs0), len(_techs1)))
    _mat_name = _techs1.get(_key)
    check("the new key points at the new material", _mat_name == icon_plan.get("icon_material"),
          "%r vs %r" % (_mat_name, icon_plan.get("icon_material")))
    check("the Units section was not touched by a Techs edit",
          _icons1.get("Units") == _units0, "")
    _new_mats = ({e["MaterialDef"]["Name"] for e in _mats1["Materials"]} - _mats0_names)
    check("exactly one material was added", _new_mats == {_mat_name}, sorted(_new_mats))
    check("and every shipped material survives",
          _mats0_names <= {e["MaterialDef"]["Name"] for e in _mats1["Materials"]}, "")

    # Follow the chain the ENGINE follows rather than the names this tool chose:
    # material -> GlobalTextures entry -> FileName under widgetui/.
    _def = None
    for _e in _mats1["Materials"]:
        _md = _e["MaterialDef"]
        if _md["Name"] == _mat_name:
            _def = _md
            break
    check("the material is a plain Texture, not an atlas slice",
          bool(_def) and _def.get("Type") == "Texture",
          json.dumps(_def, ensure_ascii=False)[:160])
    _tex = None
    for _e in _mats1.get("GlobalTextures") or []:
        _td = _e["TextureDef"]
        if _td["Name"] == _mat_name:
            _tex = _td
            break
    check("and it names a texture file", bool(_tex), json.dumps(_tex, ensure_ascii=False))
    _tex_rel = (_tex or {}).get("FileName") or ""
    check("under the tech icon folder, as a picture",
          _tex_rel.startswith("textures/ingame/tech/") and _tex_rel.endswith(".png"),
          _tex_rel)
    _on_disk = os.path.join(OUT_ICON, "widgetui", *_tex_rel.split("/"))
    check("the file the engine would ask for exists", os.path.isfile(_on_disk), _on_disk)
    if os.path.isfile(_on_disk):
        _back = Image.open(_on_disk)
        _back.load()
        check("and it decodes to the picture that was handed in",
              _back.size == (_side, _side)
              and _back.convert("RGBA").tobytes() == bytes(_rgba),
              "%r %s" % (_back.size, _back.mode))

    _raw_icon, _how_icon = A.P.load_dat(
        os.path.join(OUT_ICON, "resources", "_common", "dat", "empires2_x2_p1.dat"))
    _c3, _cs3, _gv3, _t3 = A.L.locate(_raw_icon)
    _recs3 = A.L.locate_techs(_raw_icon, _t3, _gv3)
    _rec3 = _recs3[(icon_man.get("new_tech") or {}).get("id", -1)]
    check("the emitted record carries the new icon id",
          _rec3.get("icon_id") == icon_plan.get("icon_slot"),
          "%r vs %r" % (_rec3.get("icon_id"), icon_plan.get("icon_slot")))

    print()
    if FAILS:
        print("TECH CREATE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("TECH CREATE: %d CHECKS PASSED -- a sentence appends a technology the game "
          "does not have, the mod on disk carries it, and every shipped record survives"
          % CHECKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
