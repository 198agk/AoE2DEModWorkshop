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


def check(name, ok, detail=""):
    if not ok:
        FAILS.append("%s :: %s" % (name, detail))
        print("FAIL %s :: %s" % (name, detail))


def main():
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)
    civs = [e for e in ()]  # filled from the .dat only when available

    def read(text, pins=None):
        return nl.read(text, vocab, civ_names=None, civ_zh=nl.CIV_ZH, pins=pins)

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
    check("a stat with no entity is refused, and says which half is missing",
          not _i and "哪个东西" in clauses[0].why, clauses[0].why)

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
