# -*- coding: utf-8 -*-
"""The nail for the replacement SENTENCE (`unit.replace_on_map` from Chinese).

What it guards, in the order it goes wrong:

* the sentence is refused with "这句话里没有数字" (measured: all six phrasings that
  name two units were refused that way before the branch existed);
* the sentence is read as a RESKIN instead -- `把村民的样子换成步弓手` must keep
  meaning "copy the look", so the replacement branch has to yield to the sprite
  hints;
* a civilization in the sentence is silently dropped, which would edit 63
  civilizations for a player who asked for one (this layer has no per-civ key);
* the refusal for a bare 换成 names only one of its three readings.

All of these are refusals-with-reasons, so each assert is on the reason's CONTENT,
never on the sentence's absence alone.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod import api as A
from aoe2mod.semantic import index as SI
from aoe2mod.ui import nl

FAILS = []
CHECKS = 0


def check(name, ok, detail=""):
    global CHECKS
    CHECKS += 1
    print("%s %s%s" % ("ok  " if ok else "FAIL", name,
                       (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    tk = A.open_toolkit()
    ix = SI.index()
    vocab = nl.Vocabulary(ix.units, ix.techs)

    def read(text):
        intents, clauses = nl.read(text, vocab, civ_names=tk.civ_names,
                                   civ_zh=nl.CIV_ZH,
                                   effect_count=tk.effect_count,
                                   unit_class=tk.unit_class)
        why = clauses[0].why if clauses and not intents else ""
        return intents, why

    print("=== A. the four ways of saying it ===")
    for text in ("开局时让村民换成斥候骑兵",
                 "让村民在开局时换成斥候骑兵",
                 "地图上把村民换成斥候骑兵",
                 "一开始把村民变成斥候骑兵"):
        got, why = read(text)
        check("%s is a replacement" % text,
              len(got) == 1 and got[0].get("intent") == "unit.replace_on_map",
              got or why)
        if got:
            check("  and it names both units",
                  got[0].get("unit") is not None
                  and got[0].get("replacement") == 448, got[0])

    print("=== B. the reskin reading still wins ===")
    got, why = read("开局时把村民的样子换成步弓手")
    check("a look-swap with a timing aside is still a reskin",
          len(got) == 1 and got[0].get("intent") == "unit.sprite", got or why)
    got, why = read("把村民的样子换成步弓手")
    check("and without the timing word too",
          len(got) == 1 and got[0].get("intent") == "unit.sprite", got or why)

    print("=== C. a bare 换成 names all three readings ===")
    got, why = read("把村民换成斥候骑兵")
    check("it is refused", not got, got)
    check("the reason is not 'no number'", "没有数字" not in why, why)
    check("the reason names the placement reading", "开局时" in why, why)
    check("the reason names the look reading", "样子" in why, why)
    check("the reason names the value reading", "1000" in why, why)

    print("=== D. a civilization in the sentence is refused, not dropped ===")
    got, why = read("开局时让不列颠的村民换成斥候骑兵")
    check("it is refused", not got, got)
    check("and the reason says the file has no per-civ key",
          "逐文明" in why, why)

    print("=== E. two units are required ===")
    got, why = read("开局时让村民换成 1000")
    check("a value is not a replacement target", not got, got)
    check("and the reason counts the units it saw", "个单位" in why or "数字" in why,
          why)

    print("=== F. it reaches the preview, which names the file ===")
    app = A.open_toolkit()
    posted = app.plan({"intent": "unit.replace_on_map", "unit": 4,
                       "replacement": 448})
    check("the preview is editable", posted.get("editable") is True,
          posted.get("reason"))
    check("and names objreplacement.json",
          posted.get("writes") == "resources/_common/dat/objreplacement.json",
          posted.get("writes"))
    check("and says it is not a .dat edit",
          posted.get("changes_dat") is False, posted.get("changes_dat"))

    print("\n=== G. a where-word in front of 的 is not an unknown civilization")
    # `把地图上的村民换成斥候骑兵` was refused as 「地图上」这个说法我不认识 -- the
    # guard that stops "火星人的村民" from silently editing all 63 civilizations
    # also caught the phrase a replacement sentence needs.  Both directions are
    # asserted, because the exemption has to stay narrow: the same word with no
    # verb saying what happens must still be refused.
    _g, _gwhy = read("把地图上的村民换成斥候骑兵")
    check("the 把...的 shape reads as a replacement",
          len(_g) == 1 and _g[0].get("intent") == "unit.replace_on_map"
          and _g[0].get("replacement") == 448, _g or _gwhy)
    _s, _swhy = read("把地图上的村民的样子换成步弓手")
    check("and the reskin reading reaches the same word",
          len(_s) == 1 and _s[0].get("intent") == "unit.sprite", _s or _swhy)
    _n, _nwhy = read("地图上的村民血量改成1000")
    check("but with no verb saying what happens it is still refused",
          not _n, _n)
    check("and the refusal names the word the player wrote",
          "地图上" in _nwhy, _nwhy)


    print()
    if FAILS:
        print("REPLACE SENTENCE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("REPLACE SENTENCE: %d CHECKS PASSED -- the sentence parses, the reskin "
          "reading still wins, and the three ways of saying 换成 are told apart"
          % CHECKS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
