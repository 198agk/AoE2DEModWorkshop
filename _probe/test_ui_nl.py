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

    def read(text):
        return nl.read(text, vocab, civ_names=None, civ_zh=nl.CIV_ZH)

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
