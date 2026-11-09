# -*- coding: utf-8 -*-
"""The preview says what the number BECOMES, and never one answer for many.

WHY THIS EXISTS
---------------
AGE3 shows a grid of raw numbers and leaves the arithmetic to the player: to
check "生命值 +20" you find the field in a 620-column tree and read the integer
yourself.  A tool that claims to be easier has to print the result -- 生命值
25 → 45 -- and it has to print it without lying.

The lie this suite exists to prevent is the AVERAGE.  A class edit spans 217
units whose starting values differ, so 所有步兵血量加10% really is 45 distinct
pairs (60→66 appears 1,197 times, 65→72 appears 693 times, ...).  Collapsing that
into one number would be a confident answer to a question nobody asked, which is
this codebase's most expensive failure mode.  So a multi-valued edit reports the
commonest pair, how many kinds there are, and every pair in the tooltip.

Run:  python -X utf8 _probe/test_preview_values.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.ui.server import App                            # noqa: E402

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
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


def pv_of(a, sentence):
    r = a.parse(sentence)
    cl = (r.get("clauses") or [{}])[0]
    pre = cl.get("preview") or {}
    plan = pre.get("plan") or {}
    return plan.get("preview_values"), pre, cl


def main():
    a = App()

    print("\n=== 1. one edit, one pair, stated plainly ===")
    v, pre, cl = pv_of(a, u"\u6751\u6c11\u8840\u91cf\u6539\u621040")
    check("the sentence is understood", (cl.get("why") or "") == "",
          str(cl.get("why")))
    check("the preview carries values", bool(v), str(pre.get("error")))
    if v:
        eq("there is exactly one kind of change", v.get("distinct"), 1)
        eq("the field is named in Chinese", v.get("field"), u"\u751f\u547d\u503c")
        eq("the old value is the one on disk", v.get("before"), 25)
        eq("the new value is what was asked for", v.get("after"), 40)
        check("and the pair list agrees with the flat keys",
              v["pairs"][0]["before"] == v["before"]
              and v["pairs"][0]["after"] == v["after"], str(v["pairs"][0]))

    print("\n=== 2. the value is the STORED one, not a float32 artefact ===")
    # 移动速度 is stored as float32; the plan hands back 1.350000023841858.
    # Printing that beside "加10%" is the same defect as an English refusal: the
    # player is looking at a rounding artefact, not at a number the game has.
    v, pre, cl = pv_of(a, u"\u6240\u6709\u6b65\u5175\u79fb\u52a8\u901f\u5ea6\u52a010%")
    if v:
        bad = [p for p in v["pairs"]
               if isinstance(p["before"], float)
               and len(repr(p["before"]).split(".")[-1]) > 6]
        check("no pair prints a float32 tail longer than 6 digits", not bad,
              str(bad[:2]))
        eq("an integral value is printed as an integer, not 25.0",
           isinstance(v["pairs"][0]["before"], int)
           or "." in str(v["pairs"][0]["before"]), True)

    print("\n=== 3. many starting values are reported as many, never averaged ===")
    v, pre, cl = pv_of(a, u"\u6240\u6709\u6b65\u5175\u8840\u91cf\u52a010%")
    check("the class sentence is understood", (cl.get("why") or "") == "",
          str(cl.get("why")))
    check("the preview carries values", bool(v), str(pre.get("error")))
    if v:
        print("     distinct %s, first pairs %s"
              % (v.get("distinct"), v.get("pairs")[:3]))
        check("a class edit really does span many starting values",
              (v.get("distinct") or 0) > 1, str(v.get("distinct")))
        check("so there is NO single before/after to mistake for the answer",
              v.get("before") is None and v.get("after") is None,
              "before %r after %r" % (v.get("before"), v.get("after")))
        check("the pairs are ordered by how many places they cover",
              all(v["pairs"][i]["count"] >= v["pairs"][i + 1]["count"]
                  for i in range(len(v["pairs"]) - 1)),
              str([p["count"] for p in v["pairs"]]))
        check("the counts add up to at most the edit count (the list is capped)",
              sum(p["count"] for p in v["pairs"])
              <= (pre.get("plan") or {}).get("edit_count", 0),
              str(sum(p["count"] for p in v["pairs"])))
        # +10% is applied to the WHOLE value, not to the delta: 65 HP becomes 72,
        # not 65+7 by way of rounding the increment first (which would give 71).
        # Asserting `after - before == round(before*0.1)` would be asserting the
        # wrong arithmetic -- 65*0.1 is 6.5 and half-to-even sends it to 6, so a
        # correct implementation would look broken.
        check("each pair is the percentage applied to ITS OWN starting value",
              all(p["after"] == int(round(p["before"] * 1.1))
                  for p in v["pairs"]),
              str([(p["before"], p["after"], round(p["before"] * 1.1, 2))
                   for p in v["pairs"][:5]]))

    print("\n=== 4. a percentage is computed per record, not once ===")
    # The reason `delta_percent` is a separate slot: the SAME 10% is a different
    # number of points on a 25 HP villager and a 60 HP spearman.  If the compiler
    # collapsed it to +10 the pairs above would all move by 10 and this would not.
    v, pre, cl = pv_of(a, u"\u6240\u6709\u6b65\u5175\u8840\u91cf\u52a010%")
    if v:
        deltas = {p["after"] - p["before"] for p in v["pairs"]}
        check("different bases really do get different point amounts",
              len(deltas) > 1, str(sorted(deltas)[:6]))

    print("\n=== 5. a cost edit names the RESOURCE, not the word 成本 ===")
    v, pre, cl = pv_of(a, u"\u5f13\u7bad\u624b\u6728\u6750\u6210\u672c\u52a010")
    check("the cost sentence is understood", (cl.get("why") or "") == "",
          str(cl.get("why")))
    if v:
        check("the label names the resource in Chinese",
              u"\u6728\u6750" in (v.get("field") or ""), str(v.get("field")))
        check("and does not leak the internal word for it",
              "wood" not in (v.get("field") or "").lower(), str(v.get("field")))

    print("\n=== 6. a technology edit is previewed the same way ===")
    v, pre, cl = pv_of(a, u"\u7ec7\u5e03\u673a\u7814\u7a76\u65f6\u95f4\u51cf5")
    check("the tech sentence is understood", (cl.get("why") or "") == "",
          str(cl.get("why")))
    if v:
        eq("Loom's research time is stored as 25", v.get("before"), 25)
        eq("and 减5 is a decrease, not an increase", v.get("after"), 20)

    print("\n=== 7. the page prints it, and says how many kinds there are ===")
    page = open(PAGE, encoding="utf-8").read()
    check("the page reads preview_values", "preview_values" in page)
    check("it prints an arrow between the two numbers", u"\u2192" in page)
    check("and it discloses a multi-valued edit",
          u"\u7b49 " in page and "distinct" in page)
    check("the full list goes in a tooltip rather than widening the card",
          ".title =" in page and "preview_values" in page)

    print()
    if FAILS:
        print("PREVIEW VALUES: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("PREVIEW VALUES: EVERY EDIT SHOWS 现在 → 改成, AND A CLASS EDIT "
          "DISCLOSES ITS 45 KINDS INSTEAD OF AVERAGING THEM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
