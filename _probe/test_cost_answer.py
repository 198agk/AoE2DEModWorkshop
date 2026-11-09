# -*- coding: utf-8 -*-
"""「造价是多少」 shows the numbers instead of naming the four slots.

Measured 2026-11-02: 「村民造价是多少」 was answered 「...是四个不同的数。说清是哪
一项」 -- a menu.  The tool holds every price (a villager charges 50 food and
nothing else; a castle 650 stone and nothing else), so naming the slots instead
of printing them refused a question the data answers.

WHAT THIS PINS
--------------
  * the four prices are printed, zero/absent slots are not
  * the example sentence names a resource the record ACTUALLY charges
    (「城堡食物造价减10%」 would point at an empty slot)
  * it is still not an intent -- there is nothing to build
  * a sentence that already names the resource is untouched (it is an edit)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

FAILS = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    import contextlib
    import io

    from aoe2mod.ui import server as S

    with contextlib.redirect_stdout(io.StringIO()):
        a = S.App()

    def parse(text):
        with contextlib.redirect_stdout(io.StringIO()):
            r = a.parse(text)
        return (r.get("clauses") or [{}])[0], r

    print("\n=== 1. the numbers are printed, not just the slot names ===")
    cl, _r = parse("村民造价是多少")
    why = cl.get("why") or ""
    check("the villager's price is on screen", "食物 50" in why, why[:110])
    check("and empty slots are not claimed", "木材" not in why, why[:110])
    check("it is still not an edit", cl.get("intent") is None, cl.get("intent"))

    cl, _r = parse("民兵造价是多少")
    why = cl.get("why") or ""
    check("a two-resource unit shows both",
          "食物 50" in why and "黄金 20" in why, why[:110])

    print("\n=== 2. the example names a resource that has a price ===")
    # A castle charges stone only.  Offering 「城堡食物造价减10%」 would send the
    # player to an empty slot, which is the failure this example must not have.
    cl, _r = parse("城堡造价是多少")
    why = cl.get("why") or ""
    check("the castle shows its stone", "石头 650" in why, why[:110])
    check("and the example uses 石头, not 食物",
          "石头造价减10%" in why and "食物造价减10%" not in why, why[:110])

    print("\n=== 3. naming the resource is an edit, not a question ===")
    cl, _r = parse("村民木材造价减10%")
    check("a resource-named cost sentence is an intent",
          (cl.get("intent") or {}).get("resource") == "wood", cl.get("intent"))

    print("\n=== 4. the page still draws it as an answer, not an error ===")
    page = open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                encoding="utf-8").read()
    check("the page has a refusal branch that prints the reason",
          '"why"' in page or "c.why" in page)

    print()
    if FAILS:
        print("COST ANSWER: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("COST ANSWER: A BARE 造价 QUESTION PRINTS THE FOUR PRICES, AND THE "
          "EXAMPLE NEVER POINTS AT AN EMPTY SLOT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
