# -*- coding: utf-8 -*-
"""The local grammar, exercised against real sentences.

Not a smoke test: every case below is a sentence a player would plausibly type,
and the ones that must be REFUSED are here because guessing them is the failure
mode that matters (the tool must never silently invent an edit).  The vocabulary
is the shipped semantic index, so this also pins that "村民" resolves without the
game being available at import time.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.semantic import index as SI                      # noqa: E402
from aoe2mod.ui import nl                                     # noqa: E402

FAILS = []


#: How many effect commands a technology has, as far as this file is concerned.
#: 織布機 (22) really has 3 -- measured with `Toolkit.effect_count` on 2026-10-20,
#: along with "371 of the 1,040 technologies that have any command have exactly
#: one".  A double is honest HERE because the reader must work without a `.dat`
#: (that is why `effect_count` is injected at all); the real counts are pinned by
#: `_probe/test_ui_server.py`, which does load the game.
def _effect_count(tech_id):
    return {22: 3}.get(tech_id, 1)


def check(name, ok, detail=""):
    if not ok:
        FAILS.append("%s :: %s" % (name, detail))
        print("FAIL %s :: %s" % (name, detail))


def main():
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)
    civs = [e for e in ()]  # filled from the .dat only when available

    def read(text, pins=None):
        return nl.read(text, vocab, civ_names=None, civ_zh=nl.CIV_ZH, pins=pins,
                       effect_count=_effect_count)

    # ---- plain stat edits ------------------------------------------------
    intents, clauses = read("村民血量改成 1000")
    check("set reads as a value", len(intents) == 1
          and intents[0]["intent"] == "unit.stat"
          and intents[0]["stat"] == "hit_points"
          and intents[0].get("value") == 1000
          and "delta" not in intents[0], intents)

    intents, _ = read("弓箭手攻击力加 2")
    check("add reads as a positive delta", len(intents) == 1
          and intents[0]["stat"] == "displayed_attack"
          and intents[0].get("delta") == 2, intents)

    intents, _ = read("弓箭手攻击力减少 3")
    check("reduce reads as a negative delta", len(intents) == 1
          and intents[0].get("delta") == -3, intents)

    intents, _ = read("村民血量 1000")
    check("a bare number defaults to set, and says so", len(intents) == 1
          and intents[0].get("value") == 1000
          and intents[0]["intent"] == "unit.stat", intents)
    check("the default is reported as a note, not hidden",
          any("设为" in n for cl in _ for n in cl.notes), "notes missing")

    intents, _ = read("村民血量改到1000")
    check("no spaces is still one sentence", len(intents) == 1
          and intents[0].get("value") == 1000, intents)

    # ---- costs -----------------------------------------------------------
    intents, _ = read("弓箭手木材成本加 10")
    check("resource word routes to unit.cost", len(intents) == 1
          and intents[0]["intent"] == "unit.cost"
          and intents[0]["resource"] == "wood"
          and intents[0].get("delta") == 10, intents)

    # ---- techs -----------------------------------------------------------
    intents, _ = read("织布机研究时间减 5")
    check("tech research time", len(intents) == 1
          and intents[0]["intent"] == "tech.research_time"
          and intents[0].get("delta") == -5, intents)

    intents, _ = read("织布机食物成本改成 50")
    check("tech cost", len(intents) == 1
          and intents[0]["intent"] == "tech.cost"
          and intents[0]["resource"] == "food"
          and intents[0].get("value") == 50, intents)

    # ---- availability ----------------------------------------------------
    intents, _ = read("给印加解锁蔷琵侦察兵")
    check("grant names the civ and the unit", len(intents) == 1
          and intents[0]["intent"] == "unit.availability"
          and intents[0]["civ"] == "Incas"
          and intents[0]["action"] == "grant", intents)

    intents, _ = read("印加不能造蔷琵侦察兵")
    check("revoke names the civ and the unit", len(intents) == 1
          and intents[0]["intent"] == "unit.availability"
          and intents[0]["action"] == "revoke", intents)

    # ---- must be refused, with a reason ---------------------------------
    _i, clauses = read("弓箭手")
    check("a name with no number is refused", not _i
          and "数字" in clauses[0].why, clauses[0].why)

    _i, clauses = read("弓箭手血量改成很多")
    check("a non-numeric amount is refused", not _i, _i)

    _i, clauses = read("血量改成 1000")
    # The refusal must NAME the field the sentence got right (「血量」), not just
    # say "no name I know": measured 2026-11-01, all four no-subject sentences in
    # the corpus named a real field and got one generic sentence back.
    check("a stat with no entity is refused, and names the field it DID read",
          not _i and "\u8840\u91cf" in clauses[0].why
          and "\u5355\u4f4d" in clauses[0].why, clauses[0].why)

    _i, clauses = read("这是什么")
    check("a question is not an edit", not _i
          and "提问" in clauses[0].why, clauses[0].why)

    _i, clauses = read("解锁蔷琵侦察兵")
    check("availability without a civ is refused", not _i, _i)

    # ---- a named civilization is a SCOPE, not decoration ------------------
    # "让不列颠的村民血量改成1000" narrowing to zero civilizations, or silently
    # fanning out to all 63, are both wrong; the sentence said one civ.
    intents, _ = read("把不列颠的村民血量改成1000")
    check("a named civ narrows the edit to that civ",
          len(intents) == 1 and intents[0].get("civs") == ["British"], intents)

    intents, _ = read("村民血量改成1000")
    check("no civ named means no scope is invented",
          len(intents) == 1 and "civs" not in intents[0], intents)

    # ---- multi-sentence --------------------------------------------------
    intents, clauses = read("村民血量改成 1000。弓箭手攻击力加 2")
    check("two sentences become two intents", len(intents) == 2
          and len(clauses) == 2, (len(intents), len(clauses)))

    # A comma is how Chinese actually joins two edits.  Reading it as one
    # sentence produced a WRONG edit (first entity + second stat) instead of a
    # refusal, so this case is pinned rather than incidental.
    intents, clauses = read("村民血量改成1000，弓箭手攻击力加2")
    check("a comma between two edits splits them", len(intents) == 2
          and len(clauses) == 2, (len(intents), len(clauses)))
    check("each half keeps its own entity and its own number",
          intents and (intents[0].get("unit") != intents[1].get("unit")
                       and intents[0].get("stat") == "hit_points"
                       and intents[1].get("stat") == "displayed_attack"),
          intents)

    intents, _clauses = read("村民血量改成1,000")
    check("a comma inside a number is not a sentence break",
          len(intents) == 1 and intents[0].get("value") == 1000, intents)

    intents, clauses = read("村民血量改成 1000\n瞎写的句子")
    check("a bad sentence does not discard the good one", len(intents) == 1
          and len(clauses) == 2, (len(intents), len(clauses)))

    # ---- the vocabulary must not be fooled by substrings -----------------
    intents, _ = read("村民血量改成 1000")
    check("'血' inside '血量' still resolves to hit_points",
          intents and intents[0]["stat"] == "hit_points", intents)

    intents, _ = read("城堡血量改成 5000")
    check("a building name resolves too", len(intents) == 1, intents)

    # ---- a picture click carries the id --------------------------------
    # Measured: of the 1,651 visible unit names, only 1,316 come back to the
    # record the player clicked -- 287 land on a different record because a
    # name like 靶场 or 城门 belongs to 10..29 records and the reader takes the
    # lowest id.  The clicked id therefore travels with the sentence.
    intents, _ = read("靶场 血量改成1000")
    check("without a pin a shared name takes the lowest id",
          intents and intents[0].get("unit") == 10, intents)

    intents, clauses = read("靶场 血量改成1000", pins=[{"kind": "unit", "id": 14}])
    check("a pin overrides the lowest-id guess",
          intents and intents[0].get("unit") == 14, intents)
    check("the clause says which picture it followed",
          clauses and any("14" in n for n in clauses[0].notes), clauses and clauses[0].notes)

    intents, _ = read("城门 血量改成1000", pins=[{"kind": "unit", "id": 1579}])
    check("a pin works on the worst name (29 records)", intents
          and intents[0].get("unit") == 1579, intents)

    intents, clauses = read("血量改成1000", pins=[{"kind": "unit", "id": 14}])
    check("a pin does not act when its name is gone from the sentence",
          not intents and clauses and not clauses[0].entity, intents)

    intents, _ = read("织布机 研究时间减5", pins=[{"kind": "tech", "id": 22}])
    check("a pin works for technologies too",
          intents and intents[0].get("tech") == 22, intents)

    # ---- names the reader used to be unable to say ----------------------
    intents, _ = read("鹿 血量改成1000")
    check("a one-character name standing alone resolves",
          intents and intents[0].get("unit") == 65, intents)

    intents, clauses = read("空气血量改成1000")
    check("a one-character name inside a word does NOT resolve",
          not intents and clauses and not clauses[0].entity, intents)

    intents, _ = read("草坪，绿 血量改成1000")
    check("a comma inside a shipped name is not a sentence break",
          len(intents) == 1 and intents[0].get("unit") == 301, intents)

    intents, clauses = read("村民血量改成1000，弓箭手攻击力加2")
    check("protecting comma-names did not stop ordinary comma splitting",
          len(clauses) == 2 and len(intents) == 2, (len(intents), len(clauses)))

    # "25% 的木材、75% 的黄金" is a shipped technology name with digits in it;
    # reading the amount before the name answered -25 instead of -5.
    intents, _ = read("25% 的木材、75% 的黄金 研究时间减5")
    check("a digit inside a name is not the amount",
          intents and intents[0].get("delta") == -5, intents)

    # ---- every name the grid can offer must come back to its own id ------
    # The grid lists 1,651 units and 536 technologies; a click posts the id
    # along with the name.  Measured before the pin existed: 287 unit names and
    # 4 technology names came back as a DIFFERENT record, and 48 + 13 were
    # refused -- so a third of the grid was a dead end that looked alive.  This
    # sweep is the only way to know that every row still works, including the
    # ones nobody would think to write a case for (single characters, names
    # containing commas, names containing digits).
    idx = SI.index()
    for kind, template, key in (("unit", "{} 血量改成1000", "unit"),
                                ("tech", "{} 研究时间加5", "tech")):
        table = idx.units if kind == "unit" else idx.techs
        wrong, refused, total = [], [], 0
        for uid, ent in table.items():
            if not ent.is_visible:
                continue
            name = ent.zh or ent.en
            if not name:
                continue
            total += 1
            intents, clauses = read(template.format(name),
                                    pins=[{"kind": kind, "id": uid}])
            got = intents[0].get(key) if intents else None
            if got != uid:
                (refused if got is None else wrong).append(
                    (uid, name, got, clauses[0].why if clauses else None))
        check("every %s name the grid offers comes back to its own id (%d rows)"
              % (kind, total), not wrong and not refused,
              "wrong=%r refused=%r" % (wrong[:6], refused[:6]))

    # ---- the five intents the screen could not say ----------------------
    # Each of these was measured as a wrong answer or a dead end before the
    # branch existed, so the assertions record the observed reading, not the
    # hoped-for one.
    intents, _ = read("步弓手对骑兵攻击加2")
    check("a class bonus reads as unit.attack_class, not as plain attack",
          intents and intents[0]["intent"] == "unit.attack_class"
          and intents[0].get("class_id") == 12
          and intents[0].get("kind") == "attack"
          and intents[0].get("delta") == 2, intents)

    intents, _ = read("步弓手对骑兵防御加2")
    check("the other half of the class bonus is armour",
          intents and intents[0].get("kind") == "armour", intents)

    intents, clauses = read("步弓手对骑兵加2")
    check("a class bonus with no attack/armour word is REFUSED, not guessed",
          not intents and clauses and "攻击" in (clauses[0].why or ""),
          intents or (clauses and [c.why for c in clauses]))

    # The class name only counts right after 对: "骑兵的血量" is about the CLASS
    # as an entity..., which is not a thing, so the safe reading is a refusal.
    intents, clauses = read("骑兵的血量改成1000")
    check("a class name is not treated as an entity on its own",
          not intents, intents)

    intents, _ = read("织布机第2条效果加5")
    check("the second command of a technology is addressed by position",
          intents and intents[0]["intent"] == "tech.effect"
          and intents[0].get("command") == 1
          and intents[0].get("delta") == 5, intents)

    intents, _ = read("织布机第1条效果改成10")
    check("the position is not read as the amount",
          intents and intents[0].get("value") == 10
          and intents[0].get("command") == 0, intents)

    intents, clauses = read("织布机效果加5")
    check("an unnumbered effect on a 3-command technology is refused",
          not intents and clauses and "第几条" in (clauses[0].why or ""),
          intents or (clauses and [c.why for c in clauses]))

    intents, clauses = read("织布机第9条效果加5")
    check("asking for a command that does not exist is refused with the count",
          not intents and clauses and "3" in (clauses[0].why or ""),
          intents or (clauses and [c.why for c in clauses]))

    intents, clauses = read("织布机第0条效果加5")
    # "第0条" is not a position either.  `_ordinal` hands back the number the
    # sentence said, so 0 arrived at the compiler as index -1, passed the
    # `idx >= count` guard (only that end was checked) and was refused THERE --
    # in English, naming the internal record "Loom".  A position that cannot
    # exist is refused where it is read.
    check("asking for a command before the first one is refused, not passed down",
          not intents and clauses
          and "从第 1 条开始数" in (clauses[0].why or ""),
          intents or (clauses and [c.why for c in clauses]))

    # ---- 研究 is a verb players use for technologies ---------------------
    intents, _ = read("印加不能研究织布机")
    check("'cannot research' reads as a technology revoke",
          intents and intents[0]["intent"] == "tech.availability"
          and intents[0].get("action") == "revoke"
          and intents[0].get("tech") == 22, intents)

    # ---- word order decides which unit is which -------------------------
    intents, _ = read("把村民的样子换成步弓手")
    check("the unit before 样子 is the one being changed",
          intents and intents[0]["intent"] == "unit.sprite"
          and intents[0].get("unit") == 1810
          and intents[0].get("donor") == 4, intents)

    intents, _ = read("把步弓手的样子换成村民")
    check("and swapping the two names swaps the direction",
          intents and intents[0].get("unit") == 4
          and intents[0].get("donor") == 1810, intents)

    intents, clauses = read("把村民的样子换成村民")
    check("the same unit on both sides is refused",
          not intents and clauses and "一个单位" in (clauses[0].why or ""),
          intents or (clauses and [c.why for c in clauses]))

    intents, clauses = read("把村民的样子换成步弓手，连干活的样子一起换")
    check("a trailing 'and its working poses too' joins the first edit",
          len(intents) == 1 and intents[0].get("whole_family") is True, intents)
    check("...instead of becoming a second refusal",
          len(clauses) == 1, [c.text for c in clauses])

    # ---- a picture path, and nothing else, selects unit.art -------------
    intents, _ = read("给村民换张图 D:\\pics\\a.png")
    check("a path in the sentence reads as unit.art",
          intents and intents[0]["intent"] == "unit.art"
          and intents[0].get("unit") == 1810
          and intents[0].get("picture") == "D:\\pics\\a.png", intents)

    intents, clauses = read("给织布机换张图 D:\\pics\\a.png")
    check("a technology has no picture of its own to replace",
          not intents and clauses and "科技" in (clauses[0].why or ""),
          intents or (clauses and [c.why for c in clauses]))

    # ---- a class name is a category, not a record -----------------------
    # 骑兵 covers 188 visible units and is not one of them.  Measured over all 62
    # class names with "X的血量改成1000": 33 resolved, and 15 of those resolved to
    # a DIFFERENT thing that merely starts with the word -- 攻城武器 -> 攻城武器厂
    # (a building), 征服者 -> 征服者威廉, 侦察兵 -> 蔷琵侦察兵.  Only the .dat knows
    # each record's class, so the reader takes a callback.
    CLASS_OF = {1800: 0, 4: 0, 1968: 0, 358: 6, 39: 36, 125: 18, 370: 27}

    def read_class(text, pins=None):
        return nl.read(text, vocab, civ_names=None, civ_zh=nl.CIV_ZH,
                       pins=pins, effect_count=_effect_count,
                       unit_class=lambda uid: CLASS_OF.get(uid))

    intents, clauses = read_class("骑兵的血量改成1000")
    check("a class word is refused instead of editing a like-named record",
          not intents and clauses and "一类" in (clauses[0].why or ""),
          intents or (clauses and [c.why for c in clauses]))

    intents, clauses = read_class("步兵的血量改成1000")
    check("the refusal offers the units the class covers (as far as it knows)",
          not intents and [c.id for c in (clauses[0].candidates or [])] == [358],
          clauses[0].candidates)

    # …but a word that is ALSO a shipped unit name still edits that unit: the
    # game really ships units called 长枪兵 and 骑射手.
    intents, _ = read_class("长枪兵血量改成1000")
    check("a word that is also a real unit name is not treated as a category",
          intents and intents[0].get("unit") == 358, intents)

    # …and a word that resolves to a member of that very class is fine:
    # 弓箭手 -> 复合弓箭手, both class 0.
    intents, _ = read_class("弓箭手攻击力加 2")
    check("a class word that resolves into its own class still edits",
          intents and intents[0].get("unit") == 1800
          and intents[0].get("delta") == 2, intents)

    # The gate needs data to say anything.  With no callback the reader must not
    # claim to know that a word is a category.
    intents, clauses = read("骑兵的血量改成1000")
    check("without class data the reader does not guess about categories",
          not any("一类" in (c.why or "") for c in clauses),
          [c.why for c in clauses])

    # ---- unit.create: a sentence that makes something the game does not have --
    # The reader is the only way to ask for this, so a sentence the player would
    # actually type has to produce it.  All three facts (donor, name, civ) are
    # required and each one has its own refusal, because a creation with a
    # guessed donor or a guessed civilization is a confident wrong answer.
    CREATE = [
        ("给不列颠新建一个和村民一样的单位，叫铁匠学徒", 1810, "British", "铁匠学徒"),
        ("照村民给不列颠做一个新单位，叫「铁匠学徒」", 1810, "British", "铁匠学徒"),
        ("不列颠新建一个单位，照着村民，名字叫做铁匠学徒", 1810, "British", "铁匠学徒"),
        ("做一个和村民一样的新单位，叫铁匠学徒，加进不列颠", 1810, "British", "铁匠学徒"),
    ]
    for text, donor, civ, name in CREATE:
        intents, clauses = read(text)
        check("a creating sentence is read as a creation :: %s" % text,
              len(intents) == 1 and intents[0].get("intent") == "unit.create",
              [c.intent for c in clauses])
        if len(intents) == 1 and intents[0].get("intent") == "unit.create":
            got = intents[0]
            check("…with the donor the sentence named :: %s" % text,
                  got.get("donor") == donor, got)
            check("…the civilization it named :: %s" % text,
                  got.get("civ") == civ, got)
            check("…and the name it named :: %s" % text,
                  got.get("name") == name, got)

    # A property after the name belongs to the new unit, not to a second edit.
    intents, _clauses = read("给不列颠新建一个和村民一样的单位，叫铁匠学徒，血量 500")
    check("a property after the name qualifies the new unit",
          len(intents) == 1 and intents[0].get("hp") == 500, intents)

    # A picture path is not a stat.  File names carry digits ("villager83.png")
    # and the first wiring read hp=83 straight out of the donor's screenshot
    # name -- a build that succeeded, a unit with the wrong health, and no error
    # anywhere.  The path has to reach the icon field and leave hp alone.
    intents, clauses = read(
        "不列颠照村民做一个新单位，叫铁匠学徒，图标用 D:\\pics\\villager83.png")
    check("a picture path becomes the icon and is not read as a number",
          len(intents) == 1
          and intents[0].get("icon") == "D:\\pics\\villager83.png"
          and "hp" not in intents[0],
          (intents, [c.why for c in clauses]))

    # …and a repaint still wins when the piece names what to repaint: the two
    # readings must not collapse into one.
    intents, _clauses = read("给村民换张图 D:\\pics\\villager.png")
    check("a path with an entity in front of it stays a repaint",
          len(intents) == 1 and intents[0].get("intent") == "unit.art",
          intents)

    # Missing facts are refused, and each refusal names the fact that is missing
    # AND finishes the sentence with the player's own words: a refusal that says
    # "did not understand" leaves them with a correct sentence and no idea what
    # to add, and an example that invents both the donor and the name makes them
    # rewrite the half they already got right.  The words were improved on
    # 2026-11-01 (「补上照着谁」 replacing 「说一个出厂单位的名字」); what these
    # checks pin is the property, not the phrasing -- the missing fact is named,
    # and the name the player typed comes back in the example.
    intents, clauses = read("给不列颠新建一个单位，叫铁匠学徒")
    check("a creation with no donor is refused, naming the donor",
          not intents and "照" in (clauses[0].why or "")
          and "铁匠学徒" in (clauses[0].why or ""),
          [c.why for c in clauses])
    intents, clauses = read("照着村民新建一个单位")
    check("a creation with no name is refused, naming the name",
          not intents and "叫什么" in (clauses[0].why or ""),
          [c.why for c in clauses])
    intents, clauses = read("照着村民新建一个单位，叫铁匠学徒")
    check("a creation with no civilization is refused, naming the civilization",
          not intents and "文明" in (clauses[0].why or "")
          and "铁匠学徒" in (clauses[0].why or ""),
          [c.why for c in clauses])
    # …and an ordinary edit must not be read as a creation.  "造" appears in
    # 能造; 照 appears in 照片 and 按照.
    for text, want in (("村民能造了", None),
                       ("按照村民的血量改成1000", "unit.stat"),
                       ("给印加解锁蔷琵侦察兵", "unit.availability")):
        intents, _clauses = read(text)
        got = intents[0].get("intent") if intents else None
        if want is None:
            check("「%s」is not read as a creation" % text, got != "unit.create", got)
        else:
            check("「%s」is read as %s, not a creation" % (text, want),
                  got == want, got)

    # ---- a qualifier the reader does not know is refused, not dropped ----
    # "火星人的村民血量改成1000" used to resolve 村民 perfectly and throw the
    # qualifier away, so a sentence scoped to one civilization edited all 63 --
    # 1,701 edits, identical to the sentence with no civilization at all.
    for text, word in (("火星人的村民血量改成1000", "火星人"),
                       ("MARTIANS的村民血量改成1000", "MARTIANS")):
        intents, clauses = read(text)
        why = (clauses[0].why or "") if clauses else ""
        check("「%s」is refused instead of editing every civilization" % word,
              not intents and word in why, (intents, why))

    # …and the words that legitimately scope a sentence must still work.
    for text in ("我的村民血量改成1000", "所有村民血量改成1000",
                 "复合弓箭手的血量改成1000", "村民血量改成1000",
                 "骑兵的血量改成1000"):
        intents, clauses = read(text)
        why = (clauses[0].why or "") if clauses else ""
        check("「%s」is not mistaken for an unknown qualifier" % text,
              "说法我不认识" not in why, why)

    # ---- two civilizations in one sentence mean both ---------------------
    intents, _clauses = read("不列颠和法兰克的村民血量改成1000")
    check("a sentence naming two civilizations scopes to both",
          bool(intents) and intents[0].get("civs") == ["British", "French"],
          intents[0].get("civs") if intents else None)

    intents, _clauses = read("不列颠的村民血量改成1000")
    check("a sentence naming one civilization scopes to that one",
          bool(intents) and intents[0].get("civs") == ["British"], intents)

    # Availability cannot be plural: each civilization owns its own tech-tree
    # file and its own copy of the panel, so two civilizations in one sentence is
    # a fact the player has to fix, not a thing to do halfway.
    intents, clauses = read("给不列颠和法兰克解锁蔷琵侦察兵")
    why = (clauses[0].why or "") if clauses else ""
    check("availability refuses two civilizations instead of doing one",
          not intents and "一个文明一份" in why, (intents, why))

    # ---- the example on the screen has to be readable --------------------
    # It said 伐木场成本减少 10, which the reader refuses ("没听出要改哪个属性"):
    # an example a player copies and immediately gets refused teaches the wrong
    # thing about what this tool understands.
    intents, _clauses = read("波兰的伐木场木材成本减少 10")
    check("the example sentence on the screen parses",
          bool(intents) and intents[0].get("intent") == "unit.cost"
          and intents[0].get("civs") == ["Poles"], intents)

    # ---- rate comparisons, spoken form -----------------------------------
    # 「造得快」/「做得快」 is how this is actually said.  The written compounds
    # (建造速度 / 生产速度) were the only spellings the rate table knew, and both
    # silent failures below come from that gap.
    for text in ("\u6751\u6c11\u9020\u5f97\u5feb\u4e00\u70b9",
                 "\u6751\u6c11\u9020\u7684\u5feb\u4e00\u70b9",
                 "\u6751\u6c11\u5efa\u9020\u5f97\u5feb\u4e00\u70b9",
                 "\u6751\u6c11\u751f\u4ea7\u5f97\u5feb\u4e00\u70b9",
                 "\u6751\u6c11\u505a\u5f97\u5feb\u4e00\u70b9"):
        _i, _c = read(text)
        check("%s reads as TRAINING TIME, faster" % text,
              bool(_i) and _i[0].get("stat") == "creation_time"
              and _i[0].get("delta", 0) < 0, _i or _c)

    _i, _c = read("\u6751\u6c11\u9020\u5f97\u6162\u4e00\u70b9")
    check("and \u6162 flips the direction", bool(_i)
          and _i[0].get("stat") == "creation_time"
          and _i[0].get("delta", 0) > 0, _i or _c)

    # The one that mattered: this sentence used to come back as
    # ``unit.stat hit_points +1``.  A wrong-but-plausible edit is worse than a
    # refusal, so the assertion names the field AND rejects the wrong one.
    _i, _c = read("\u6751\u6c11\u751f\u4ea7\u5f97\u5feb\u4e00\u70b9")
    check("production speed is NEVER read as hit points",
          not (bool(_i) and _i[0].get("stat") == "hit_points"), _i)

    # 攻击更快 is a RATE, 攻击力更强 is DAMAGE -- only the adjacency tells them
    # apart, and 造 must not steal 攻击 (it does not: longer words win).
    _i, _c = read("\u957f\u67aa\u5175\u653b\u51fb\u66f4\u5feb1")
    check("\u653b\u51fb\u66f4\u5feb stays a rate", bool(_i)
          and _i[0].get("stat") == "reload_time", _i or _c)
    _i, _c = read("\u6751\u6c11\u653b\u51fb\u529b\u66f4\u5f3a1")
    check("\u653b\u51fb\u529b\u66f4\u5f3a stays damage", bool(_i)
          and _i[0].get("stat") == "displayed_attack", _i or _c)

    # ---- honesty: every clause carries either an intent or a reason ------
    _, clauses = read("随便写点什么")
    for cl in clauses:
        check("a refusal always explains itself", bool(cl.intent) or bool(cl.why),
              cl.text)

    if FAILS:
        print("\nUI NL CHECKS FAILED (%d)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("ALL UI NL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
