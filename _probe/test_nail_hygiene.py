"""Register test_plan_writes.py was already done; this registers nothing new.

Instead: assert that the *fix* to test_nl_schema_words.py L238 is not itself a
tautology, by checking at the source level that the assertion no longer derives its
expectation from the function it is testing.

A regex over source is weak on purpose here -- it is cheap, and it fails loudly if
someone re-introduces the `== nl.intent_for_stat(...)` shape that this round removed.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FAILED = []
CHECKS = [0]


def check(name, cond, detail=""):
    CHECKS[0] += 1
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILED.append(name)


NAILS = (
    "_probe/test_nl_schema_words.py",
    "_probe/test_nl_live_vocab.py",
    "_probe/test_class_edit.py",
    "_probe/test_class_mirror.py",
    "_probe/test_plan_writes.py",
    "_probe/test_objreplace_facts.py",
)

# `got[...].get("intent") == intent_for_stat(...)` is the shape that went vacuous:
# the reader computes the id with the same call, so the two sides move together.
SELF_REF = re.compile(
    r"get\(\"intent\"\)\s*==\s*\w*\.?intent_for_stat\(", re.MULTILINE)


def main():
    print("=== A. no nail derives an expectation from the function under test")
    offenders = []
    for rel in NAILS:
        path = os.path.join(ROOT, *rel.split("/"))
        if not os.path.isfile(path):
            check("%s exists" % rel, False, path)
            continue
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            src = fh.read()
        m = SELF_REF.search(src)
        check("%s does not compare against intent_for_stat" % rel, m is None,
              m.group(0) if m else "")
        if m:
            offenders.append(rel)

    print("=== B. the expectation is spelled out as data")
    with io.open(os.path.join(ROOT, "_probe", "test_nl_schema_words.py"),
                 "r", encoding="utf-8", newline="") as fh:
        body = fh.read()
    check("the plugin intent id appears as a literal", '"unit.sort_order"' in body,
          "no literal unit.sort_order in the file")
    check("and the sentence really is read", 'read("村民排序号加5")' in body,
          "the sentence moved or was renamed")

    print("=== C. the detector rule that this round paid for")
    # Three suites print FAIL three ways; the break-detector must accept all of them.
    variants = ("  FAIL a :: b", "FAIL a :: b", "a :: FAIL")
    pat = re.compile(r"\bFAIL\b")
    check("a FAIL at any column is recognised", all(pat.search(v) for v in variants),
          [v for v in variants if not pat.search(v)])
    check("and a summary line is not counted as a failure",
          not pat.search("NL SCHEMA WORDS: 20 CHECKS PASSED -- ..."), "summary matched")

    print()
    if FAILED:
        print("NAIL HYGIENE: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("NAIL HYGIENE: NO NAIL DERIVES AN EXPECTATION FROM THE CODE UNDER TEST (%d checks)"
          % CHECKS[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
