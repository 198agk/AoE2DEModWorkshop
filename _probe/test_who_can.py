# -*- coding: utf-8 -*-
"""「谁能造 X」 -- the one question the game data can answer without a number.

WHY THIS EXISTS
---------------
The reader used to answer 「谁能造手推炮」 with 「可用性得指定一个文明」, which is
the opposite of an answer: the whole point of the question is that it spans all
62 civilizations.  The data was already there (`api.availability_of` reads every
tech tree); nothing routed the question to it.

The trap this suite exists to keep closed
-----------------------------------------
The tech-tree file keeps buildings in a SEPARATE list from units -- a Castle is
``Building`` id 82, and no ``Unit`` row has that id.  Asking the ``Unit`` space
alone returns nothing for 「谁能造城堡」, and the honest-sounding sentence that
follows ("not in any tech tree") is simply FALSE: 62 of 62 civs have a Castle.
So the load-bearing assertion here is not that the list is long; it is that a
BUILDING is answered at all.

A negative question is not the complement of a positive one
-----------------------------------------------------------
「谁不能造手推炮」 is 36, not 62-26.  The civs with no row in the tree at all
belong on the cannot side (a grant adds a row, a revoke deletes one), so the two
numbers do not add to 62 and must not be forced to.

Run:  python -X utf8 _probe/test_who_can.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.ui.server import App                            # noqa: E402
from aoe2mod.game import civtechtrees as CT                  # noqa: E402

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


def who_of(a, sentence):
    """The `who` row the page would render, or None."""
    r = a.parse(sentence)
    cl = (r.get("clauses") or [{}])[0]
    return cl.get("who"), cl


def main():
    a = App()

    print("\n=== 1. a building is answered, although it is not a Unit row ===")
    # The trap, stated as data: Castle is a Building and is NOT a unit id.
    check("Castle id 82 is absent from the Unit space",
          a.tk.availability_of(82, CT.UNIT_USE_TYPES) is None)
    check("and present once the Building space is included",
          a.tk.availability_of(82, CT.UNIT_USE_TYPES + CT.BUILDINGS_USE_TYPES)
          is not None)
    w, cl = who_of(a, u"\u8c01\u80fd\u9020\u57ce\u5821")
    check("「谁能造城堡」 is answered, not refused", w is not None,
          str(cl.get("why")))
    eq("and all 62 civilizations have one", w and w.get("count"), 62)
    eq("the answer spans every tree", w and w.get("total"), 62)

    print("\n=== 2. a unit that only some civilizations can build ===")
    w, cl = who_of(a, u"\u8c01\u80fd\u9020\u624b\u63a8\u70ae")
    check("「谁能造手推炮」 is answered", w is not None, str(cl.get("why")))
    eq("it names a unit", w and w.get("kind"), "unit")
    eq("the record is Hand Cannoneer", w and w.get("id"), 36)
    eq("26 of 62 civilizations can build it", w and w.get("count"), 26)
    eq("the denominator is every civilization", w and w.get("total"), 62)
    names = (w or {}).get("civs") or []
    check("the answer carries NAMES, not ids", names and all(
        isinstance(n, str) and n and not n.isdigit() for n in names), str(names[:4]))
    check("and the count matches the list", len(names) == (w or {}).get("count"),
          "%d vs %s" % (len(names), (w or {}).get("count")))

    print("\n=== 3. a negative question is its own list, and it is complete ===")
    n, cl = who_of(a, u"\u8c01\u4e0d\u80fd\u9020\u624b\u63a8\u70ae")
    check("「谁不能造手推炮」 is answered", n is not None, str(cl.get("why")))
    eq("it is flagged negative", n and n.get("negative"), True)
    eq("36 civilizations cannot", n and n.get("count"), 36)
    cannot = (n or {}).get("civs") or []
    eq("and the count matches the list", len(cannot), (n or {}).get("count"))
    check("whoever can build it is absent from the cannot list",
          not (set(names) & set(cannot)),
          str(sorted(set(names) & set(cannot))[:5]))
    # `builders` = holders + pending (a civ whose prerequisite is still to come
    # can build it once that is researched), so can + cannot really does cover
    # all 62.  The check is worth having because it is the one arithmetic the
    # page's two numbers must satisfy.
    eq("can + cannot covers every civilization",
       (w or {}).get("count") + (n or {}).get("count"),
       (w or {}).get("total"))

    print("\n=== 3b. the cannot list must keep the civs with NO ROW AT ALL ===")
    # Nightmare case, and the reason the code concatenates two lists instead of
    # subtracting: 精锐炮舰 (691) has 36 civs blocked by a missing technology AND
    # 6 civs with no tech-tree row for it at all.  Reporting only `blocked`
    # would answer "36" for a unit that 42 civilizations in fact cannot build,
    # and the two groups are FIXED DIFFERENTLY (a status change vs a row insert),
    # so dropping either one hides real work.
    av = a.tk.availability_of(691, CT.UNIT_USE_TYPES + CT.BUILDINGS_USE_TYPES)
    check("the fixture really does have civs with no row",
          len(av["absent_from"]) > 0, str(len(av["absent_from"])))
    nm, clm = who_of(a, u"\u8c01\u4e0d\u80fd\u9020\u7cbe\u9510\u70ae\u8230")
    check("「谁不能造精锐炮舰」 is answered", nm is not None, str(clm.get("why")))
    if nm:
        eq("it counts blocked AND absent together",
           nm.get("count"),
           len(av["blocked_in"]) + len(av["absent_from"]))
        check("and the count is more than the blocked-only answer would give",
              nm.get("count") > len(av["blocked_in"]),
              "%d vs %d" % (nm.get("count"), len(av["blocked_in"])))
        check("the row still keeps the two groups apart for the page",
              isinstance(nm.get("blocked"), list)
              and isinstance(nm.get("absent"), list),
              str(sorted(nm.keys())))

    print("\n=== 4. the same question about a TECHNOLOGY ===")
    t, cl = who_of(a, u"\u8c01\u6709\u7ec7\u5e03\u673a")
    check("「谁有织布机」 is answered", t is not None, str(cl.get("why")))
    eq("it names a technology", t and t.get("kind"), "tech")
    eq("Loom is id 22", t and t.get("id"), 22)
    eq("every civilization has it", t and t.get("count"), 62)

    print("\n=== 5. other ways of asking reach the same answer ===")
    for s in (u"\u54ea\u4e9b\u6587\u660e\u80fd\u9020\u624b\u63a8\u70ae",
              u"\u6709\u51e0\u4e2a\u6587\u660e\u80fd\u9020\u624b\u63a8\u70ae",
              u"\u54ea\u4e2a\u6587\u660e\u80fd\u9020\u624b\u63a8\u70ae"):
        w2, cl2 = who_of(a, s)
        eq("%s -> Hand Cannoneer" % s, w2 and w2.get("id"), 36)

    print("\n=== 5b. 「玛雅能不能造长弓兵」 is a QUESTION, not a revoke ===")
    # The defect this pins: REVOKE_WORDS contains 「不能造」, which is a SUBSTRING
    # of 「能不能造」.  So the question silently became a revoke command -- and
    # because the sentence carries no number, the page offered a perfectly
    # plausible edit the player never asked for.  A question must not set
    # `cl.intent` at all: nothing about it is buildable.
    q, clq = who_of(a, "玛雅能不能造长弓兵")
    check("「玛雅能不能造长弓兵」 is answered, not refused", q is not None,
          str(clq.get("why")))
    eq("and it is NOT turned into a revoke command", clq.get("intent"), None)
    eq("the answer is about the Longbowman", q and q.get("id"), 8)
    eq("it asks about one civilization, so the denominator is 1",
       q and q.get("total"), 1)
    eq("the asker is named in Chinese", q and q.get("ask_civ"), "玛雅")
    eq("and Maya cannot build it", q and q.get("count"), 0)
    verdict = (q or {}).get("verdict") or ""
    check("the verdict says WHY, not just no", len(verdict) > 10, verdict)
    check("it names the civilization and the sentence that would fix it",
          "玛雅" in verdict and "玛雅能造" in verdict, verdict)

    q2, clq2 = who_of(a, "玛雅能造长弓兵吗")
    eq("the 「…吗」 spelling reaches the same answer", q2 and q2.get("id"), 8)
    eq("and is likewise not an intent", clq2.get("intent"), None)

    q3, clq3 = who_of(a, "不列颠能不能造手推炮")
    check("「不列颠能不能造手推炮」 is answered", q3 is not None,
          str(clq3.get("why")))
    eq("the asker is Britain", q3 and q3.get("ask_civ"), "不列颠")
    # blocked_in is a DIFFERENT answer from absent_from: the row exists and is
    # disabled, so one sentence opens it.  Collapsing the four cases into "no"
    # would throw away the only actionable part.
    check("a blocked civilization gets the one-step fix, not the insert story",
          "只差一步" in ((q3 or {}).get("verdict") or ""),
          (q3 or {}).get("verdict"))

    q4, clq4 = who_of(a, "玛雅能研究织布机吗")
    eq("the same question about a TECHNOLOGY names Loom", q4 and q4.get("id"), 22)
    eq("and Maya does have it", q4 and q4.get("count"), 1)

    print("\n=== 5c. but a STATEMENT is still a command ===")
    # The fix must not make every 「能造」 sentence a question: only the
    # interrogative frames are.  Otherwise 「玛雅不能造长弓兵」 stops revoking.
    _, cls = who_of(a, "玛雅不能造长弓兵")
    it = cls.get("intent") or {}
    eq("「玛雅不能造长弓兵」 stays a revoke", it.get("action"), "revoke")
    eq("and it names unit 8", it.get("unit"), 8)

    print("\n=== 5d. a can-question with NO civilization answers the whole list ===")
    # Deliberately NOT a refusal: 「长弓兵能造吗」 is 「谁能造长弓兵」 with the
    # civilization left out, and that question is already answered.  Refusing
    # it with 「没听出要改哪个属性」 would refuse a question the data answers.
    q5, cl5 = who_of(a, "长弓兵能造吗")
    check("「长弓兵能造吗」 is answered, not refused", q5 is not None,
          str(cl5.get("why")))
    eq("it is not an edit", cl5.get("intent"), None)
    eq("it names the Longbowman", q5 and q5.get("id"), 8)
    eq("and answers over all 62 civilizations", q5 and q5.get("total"), 62)
    eq("exactly one of them builds it", q5 and q5.get("count"), 1)
    eq("with no single civilization asked about", q5 and q5.get("ask_civ"), None)
    eq("the one is Britain, by name",
       ((q5 or {}).get("civs") or [""])[0], "不列颠")

    t5, clt5 = who_of(a, "织布机能研究吗")
    eq("the same shape works for a technology", t5 and t5.get("id"), 22)
    eq("which every civilization has", t5 and t5.get("count"), 62)

    print("\n=== 6. a question with no answerable subject is refused usefully ===")
    none, cl = who_of(a, u"\u8c01\u80fd\u9020\u6751\u6c11")
    eq("「谁能造村民」 does not invent a list", none, None)
    why = cl.get("why") or ""
    check("and says a villager is not obtained by building or researching",
          u"\u79d1\u6280\u6811" in why, why)
    cnone, cl = who_of(a, u"\u8c01\u80fd\u9020\u653b\u57ce\u6b66\u5668")
    eq("a class word is not turned into one record", cnone, None)
    check("and the refusal offers the class-edit sentence instead",
          u"\u653b\u57ce\u6b66\u5668" in (cl.get("why") or ""),
          str(cl.get("why")))
    check("an answer is never a bare number with no names",
          all(not (isinstance(x, str) and x.strip().isdigit())
              for x in ((w or {}).get("civs") or [])), "checked on 手推炮")

    print()
    if FAILS:
        print("WHO CAN: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("WHO CAN: BUILDINGS ARE ANSWERED, THE CANNOT SIDE KEEPS ITS OWN "
          "NUMBER, AND EVERY ANSWER CARRIES CIVILIZATION NAMES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
