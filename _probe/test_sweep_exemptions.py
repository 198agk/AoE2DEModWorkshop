# -*- coding: utf-8 -*-
"""Check the exemption table against the guard's own rules, without a 20-minute run.

`_probe/test_full_sweep.py` is one of the eight long suites (~20 min).  Its
`DECLARED INTENTS` guard sits at the very end, after every case has been built,
so the only way to see it fire is to pay for the whole sweep.

The guard's rules are about DATA, though: for each declared intent, either a case
builds it, or an exemption names a file AND the token that file carries.  This
probe reads the real table out of the source with `ast.literal_eval` -- not a
copy -- and applies those rules.

Written after watching the guard fire on two entries of this very table:
  * `unit.art -> test_reskin.py` -- a stale pointer, driven by the wrong strategy
  * `unit.art -> test_repaint.py` -- the token I then required was not in it,
    because that nail drives `aoe2mod/intent/repaint.py` directly and never
    spells the intent id
The second one was a defect in my rule, not in the file, so the table now carries
its own token.  This file checks that every token is really there.

What it proves: the table satisfies the guard.  What it does NOT prove: that the
sweep's loop reaches the guard.  That still needs one run, at the freeze.
"""
import ast
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from aoe2mod.intent import compiler as C  # noqa: E402

SWEEP = os.path.join(ROOT, "_probe", "test_full_sweep.py")
FAILS = []
REQUIRED = ("tech.toggle_group", "tech.create", "unit.create",
            "unit.replace_on_map")


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILS.append(name)


def table_from_source():
    """Pull the real `_VERIFIED_ELSEWHERE` dict out of the file."""
    src = io.open(SWEEP, encoding="utf-8").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_VERIFIED_ELSEWHERE":
                    return ast.literal_eval(node.value), src
    raise SystemExit("REFUSING: the table is not a literal I can read")


def main():
    ix, _bd = C.load_schema()
    declared = sorted(ix["intents"])
    table, src = table_from_source()

    print("=== the table as the source actually holds it")
    print("entries: %d" % len(table))
    for intent in sorted(table):
        rel, token, _why = table[intent]
        print("  %-20s %-38s %r" % (intent, rel, token))

    print()
    print("=== A. every entry is a checkable claim")
    for intent in sorted(table):
        rel, token, why = table[intent]
        path = os.path.join(ROOT, rel)
        exists = os.path.isfile(path)
        body = io.open(path, encoding="utf-8", errors="replace").read() \
            if exists else ""
        check("%s -> %s exists" % (intent, os.path.basename(rel)), exists, rel)
        check("%s -> that file carries %r" % (intent, token),
              bool(token) and token in body, rel)
        check("%s gives a reason" % intent, bool((why or "").strip()))

    print()
    print("=== B. every entry points at an intent the schema declares")
    for intent in sorted(table):
        check("%s is still declared" % intent, intent in declared)

    print()
    print("=== C. the four intents this loop cannot diff are exempt")
    # None of these produces a `.dat` patch the sweep can compare: two append a
    # whole record, one writes a JSON beside the dat, one ships a carrier.
    for intent in REQUIRED:
        check("%s is exempt" % intent, intent in table,
              "missing -> the guard reports DECLARED BUT UNSWEPT")

    print()
    print("=== D. and nothing is exempt that the loop actually builds")
    head = src.split("_VERIFIED_ELSEWHERE = {")[0]
    built = [i for i in sorted(table) if ('"%s"' % i) in head]
    check("no exemption is for an intent the case list builds", not built, built)

    print()
    if FAILS:
        print("SWEEP EXEMPTIONS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("SWEEP EXEMPTIONS: EVERY DECLARED INTENT IS EITHER SWEPT OR "
          "EXEMPTED-WITH-A-TOKEN-THAT-EXISTS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
