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

`tech.create` has one honest limit and it is asserted here rather than hidden:
the new record's index is `len(techs)`, and the engine has never been shown to
draw a card for an index past the shipped count.  `not_proven` must say so.
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

    from aoe2mod.dat import newtech as NT
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
    npro = " ".join((man.get("verification") or {}).get("not_proven") or [])
    check("the manifest admits the engine has never drawn it",
          "never" in npro or "no test" in npro.lower(), npro)
    check("and admits the index may be unreachable",
          "reachable" in npro or "index" in npro, npro)

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
