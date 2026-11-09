# -*- coding: utf-8 -*-
"""「村民血量是多少」 -- the tool answers, and answers with the number on disk.

WHY THIS EXISTS
---------------
AGE3 has no answer path at all.  To learn a villager's hit points you find the
record in a tree of 620 columns and read the integer yourself.  That is the
single most common reason to open the tool, and it was the one thing the tool
could not do.

The design that makes this cheap and honest: a question is NOT a new resolver.
「村民血量是多少」 is read as 「村民血量加1」 -- the reader's own work -- and the
plan's `preview_values.before` IS the value on disk, because it comes from the
same code the write would use.  One source, so the answer cannot disagree with
the game.

A question must never become work.  It resolves to NO intent, so the page cannot
offer a build button for it; `buildable` stays false.  Two of these assertions
exist only for that.

Run:  python -X utf8 _probe/test_question_answers.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.ui.server import App                            # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def eq(label, got, want):
    return check("%s :: %r" % (label, want) if got != want else label,
                 got == want, "" if got == want else "got %r" % (got,))


def q_of(a, sentence):
    r = a.parse(sentence)
    cl = (r.get("clauses") or [{}])[0]
    return cl.get("question"), cl


def main():
    a = App()

    print("\n=== 1. the three questions a player actually asks ===")
    for s, field, value in (
            (u"\u6751\u6c11\u8840\u91cf\u662f\u591a\u5c11", u"\u751f\u547d\u503c", 25),
            (u"\u6751\u6c11\u653b\u51fb\u529b\u662f\u591a\u5c11", u"\u653b\u51fb\u529b", 3),
            (u"\u5f13\u7bad\u624b\u653b\u51fb\u529b\u662f\u591a\u5c11", u"\u653b\u51fb\u529b", 4)):
        q, cl = q_of(a, s)
        check("%s is answered, not refused" % s, q is not None,
              str(cl.get("why")))
        if q:
            eq("  and the field is named in Chinese", q.get("field"), field)
            eq("  and the value is the one on disk", q.get("value"), value)
            eq("  with one kind of value", q.get("distinct"), 1)

    print("\n=== 2. a technology question reads the tech record ===")
    q, cl = q_of(a, u"\u7ec7\u5e03\u673a\u7814\u7a76\u65f6\u95f4\u662f\u591a\u5c11")
    check("Loom's research time is answered", q is not None, str(cl.get("why")))
    if q:
        eq("the value is 25", q.get("value"), 25)

    print("\n=== 3. several values is the ANSWER, not an average ===")
    # 「村民射程是多少」 really is 2 values: 0 for 1,575 records and 3 for 126.
    # Reporting the pair count (4) would be the wrong kind of precision, and
    # reporting one number would be a lie.
    q, cl = q_of(a, u"\u6751\u6c11\u5c04\u7a0b\u662f\u591a\u5c11")
    check("a field with two values is still answered", q is not None,
          str(cl.get("why")))
    if q:
        eq("it reports two kinds", q.get("distinct"), 2)
        eq("and gives no single value", q.get("value"), None)
        vals = [p.get("before") for p in q.get("pairs") or ()]
        check("every value is in the pair list", 0 in vals and 3 in vals,
              str(vals))
        # A mirror field carries the SAME number as the field it mirrors; it is
        # dropped when an ordinary row exists, or 「村民射程是多少」 would say 4.
        check("mirror rows do not inflate the count",
              not any("mirror" in (p.get("field") or "")
                      for p in q.get("pairs") or ()),
              str([p.get("field") for p in q.get("pairs") or ()]))

    print("\n=== 4. a class question spans the class ===")
    q, cl = q_of(a, u"\u6240\u6709\u6b65\u5175\u8840\u91cf\u662f\u591a\u5c11")
    check("a class question is answered", q is not None, str(cl.get("why")))
    if q:
        check("it spans many values", (q.get("distinct") or 0) > 1,
              str(q.get("distinct")))
        eq("so there is no single number", q.get("value"), None)
        top = (q.get("pairs") or [{}])[0]
        check("and the commonest one is named with its count",
              top.get("before") is not None and (top.get("count") or 0) > 0,
              str(top))

    print("\n=== 5. a question is NOT work ===")
    q, cl = q_of(a, u"\u6751\u6c11\u8840\u91cf\u662f\u591a\u5c11")
    eq("it resolves to no intent", cl.get("intent"), None)
    eq("so the page cannot offer a build button", cl.get("buildable"), False)
    eq("and no preview is attached", cl.get("preview"), None)

    print("\n=== 6. a question that needs a qualifier says which one ===")
    q, cl = q_of(a, u"\u6751\u6c11\u9020\u4ef7\u662f\u591a\u5c11")
    eq("a four-resource question is not answered with one number", q, None)
    why = cl.get("why") or ""
    # This used to assert that all four slot names appear -- i.e. that the reply
    # is a MENU.  A villager charges 50 food and nothing else, so three of those
    # four "options" are empty slots.  The answer now prints the prices it has;
    # what must stay true is that the number is there, the empty slots are not
    # claimed, and the player is told what to add to turn it into an edit.
    check("the refusal prints the price it knows", u"\u98df\u7269 50" in why,
          why)
    check("and does not claim the empty slots cost something",
          u"\u6728\u6750" not in why and u"\u9ec4\u91d1" not in why, why)
    check("and says what to add to make it an edit",
          u"\u8981\u6539\u5c31\u8865\u4e0a\u6570\u503c" in why, why)

    print("\n=== 7. a question about nothing is still refused ===")
    # `_probe/test_ui_nl.py` pins this too: 「这是什么」 has no subject, and a
    # confident answer would be the worst possible output.
    q, cl = q_of(a, u"\u8fd9\u662f\u4ec0\u4e48")
    eq("「这是什么」 is not answered", q, None)
    check("and it is refused as a question, not as a broken edit",
          bool((cl.get("why") or "").strip()), str(cl.get("why")))

    print("\n=== 8. a bare field name asks for a value instead of inventing one ===")
    q, cl = q_of(a, u"\u6751\u6c11\u8840\u91cf")
    eq("「村民血量」 is not answered as a question", q, None)
    why = cl.get("why") or ""
    check("it asks for the number, and shows how", u"\u52a0" in why, why)

    print("\n=== 9. the page prints the answer without a build button ===")
    page = open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                encoding="utf-8").read()
    check("the card has a question branch", "c.question" in page)
    check("it prints 现在是 with the value", u"\u73b0\u5728\u662f" in page)
    check("and discloses several values as several",
          u"\u79cd\u53d6\u503c" in page)
    # Asserted as a SHAPE, not as a transcription.  The literal
    # `"c.question ? true : buildable(c)"` was true until the `who` branch joined
    # the same expression -- i.e. it broke when the code got MORE correct.  What
    # matters is that an answer kind forces the card green while `buildable()` is
    # still consulted for an edit.
    # `re.search` was enough until 2026-11-04, when a SECOND `const can = ` landed
    # 1302 lines earlier in `edStep()`:
    #     3845: const can = which === "undo" ? ED_UNDO_N : ED_REDO_N;
    #     5147: const can = (c.question || c.who) ? true : buildable(c);
    # The pin then read the undo guard and failed while the card code was right.
    # So: take EVERY `const can = ...;` and keep the one that talks to
    # `buildable()` -- the expression this file is actually about.
    _alls = [m.group(1) for m in re.finditer(r"const can = ([^;]+);", page)]
    _expr = next((e for e in _alls if "buildable(" in e), "")
    # The detail string is printed on GREEN lines too, so it may only describe
    # the failure.  It used to read "none mentions buildable()" on the very
    # line that had just found `buildable(c)` (seen 2026-11-04) -- a pin that
    # says the opposite of its own verdict costs the reader a minute every
    # time, and teaches them to skim.
    check("the card colour is decided in one expression", bool(_expr),
          "" if _expr else "%d `const can` found, none mentions buildable(): %s"
          % (len(_alls), _alls))
    check("a question is green although it builds nothing",
          "c.question" in _expr and "buildable(c)" in _expr
          and _expr.strip().startswith("(") and "? true :" in _expr, _expr)
    check("and an answer that is not a question is green too",
          "c.who" in _expr, _expr)

    print()
    if FAILS:
        print("QUESTION ANSWERS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("QUESTION ANSWERS: 现在是 IS PRINTED FROM THE SAME CODE THE WRITE "
          "USES, AND A QUESTION NEVER BECOMES A BUILD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
