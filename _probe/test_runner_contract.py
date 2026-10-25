# -*- coding: utf-8 -*-
"""The runner's own contract: import is inert, and a report is not a sentence.

Two defects, both mine, both found by running the whole thing:

1. On 2026-10-25 the runner called two GREEN suites red.  `_FAIL_RE` was
   `\\bFAIL(?:ED|URE)?\\b`, a word match, and those two files `check()` the
   detectors themselves -- so they print
   `ok   a FAIL at any column is recognised` and `37 have a failure gate`.
   Both exited 0 with their own PASS line and were still counted as failures.
   The tree already had the convention (`_probe/test_nail_hygiene.py:73-75`):
   every real report puts the marker in a line that IS the report.

2. Later the same evening I did `from _probe import run_suites as R` to reuse
   that regex, and the import STARTED a full run -- the module had no
   `__main__` guard, so the 131-suite loop ran at import.  A runner that cannot
   be imported cannot be tested, and every future script that greps its name
   pays twenty minutes.

So this file tests the runner the way the runner tests everything else, from
the outside: spawn it, look at what it does.

Nothing here reads `_FAIL_RE` as its only witness -- a regex that disagrees with
itself would pass that.  The shapes below are strings taken from the suites that
actually print them, and each one is asserted to classify the way the runner
needs.
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILS.append(name)


def runner_source():
    return io.open(os.path.join(HERE, "run_suites.py"), encoding="utf-8",
                   newline="").read()


def main():
    src = runner_source()

    print("=== A. importing the runner must not run it")
    # Structural half: the loop has to sit inside a guarded main().
    check("the runner defines main()", "def main():" in src)
    check("and only calls it under the guard",
          'if __name__ == "__main__":' in src)
    head = src.split("def main():")[0]
    check("the suite loop is not at module level", "for rel in SUITES:" not in head,
          "a top-level loop still runs on import")
    check("nor is the node loop", "for rel in NODE_SUITES:" not in head)
    # Behavioural half: actually import it, in a child, and time it.  The
    # structural check above could be satisfied by a guard around a loop that
    # some other module-level call still starts.
    t0 = time.time()
    probe = ("import sys, time; sys.path.insert(0, r'%s'); "
             "from _probe import run_suites as R; "
             "print(len(R.SUITES), len(R.NODE_SUITES))" % ROOT)
    # A timeout is the SLOWEST possible way to fail this check, and it is the
    # way the defect actually presents: the import never returns because it is
    # running suites.  Catch it and turn it into a named failure, or the nail
    # dies in a traceback and reads like a broken nail instead of a red one.
    try:
        p = subprocess.run([sys.executable, "-X", "utf8", "-c", probe],
                           cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        timed_out = False
    except subprocess.TimeoutExpired:
        p = None
        timed_out = True
    dt = time.time() - t0
    check("importing it in a child is quick (%.2f s)" % dt, not timed_out and dt < 20.0,
          "the import was still running after %.0f s -- it started the suites" % dt)
    if p is None:
        print()
        print("RUNNER CONTRACT: THE IMPORT RAN A SUITE INSTEAD OF RETURNING")
        return 1
    check("and prints only the two list sizes",
          p.returncode == 0 and p.stdout.strip().count(" ") == 1,
          (p.returncode, p.stdout.strip()[:120], p.stderr.strip()[:120]))
    parts = p.stdout.split()
    total_ok = (len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()
                and int(parts[0]) > 100 and int(parts[1]) == 1)
    check("so the lists are readable without a run", total_ok, parts)

    print()
    print("=== B. a failure REPORT is not the word FAIL in a sentence")
    from _probe import run_suites as R  # now inert
    sentence = "  ok   a FAIL at any column is recognised"
    gate = "  37 have a failure gate"
    ident = "IDS_FAILED_TO_OPEN_FILE"
    passing = "SUITES: ALL PASSED"
    for name, text in (("the nail-hygiene sentence", sentence),
                       ("the gate-count sentence", gate),
                       ("an identifier containing FAILED", ident),
                       ("the all-passed line", passing)):
        check("%s is not counted as a report" % name,
              R._FAIL_RE.search(text) is None, text)

    # The report shapes, each one copied from a suite that prints it.
    reports = (
        ("two-space report", "  FAIL a :: b"),
        ("unindented report", "FAIL a :: b"),
        ("trailing report", "a :: FAIL"),
        # Named so this file's own output does not contain the literal shape it
        # is checking: the first version called this line "the CHECK(S) FAILED
        # summary", and the runner then read THAT line as a report and reded a
        # green suite.  The same distinction, one level down.
        ("a count summary", "NAIL HYGIENE: 2 CHECK(S) FAILED -> ['x']"),
        ("the tech.effect summary",
         "FAILURES: 1 -> ['packed value not whole is refused']"),
        # From `_probe/test_effect_append.py`.  This arm was missing until an
        # audit of every registered suite's printed literals found it -- the
        # loosening had let one real report shape through.
        ("a bracketed report", "  [FAIL] the cursor is not advanced :: 0 vs 11"),
    )
    for name, text in reports:
        check("%s is still caught" % name, R._FAIL_RE.search(text) is not None, text)

    print()
    print("=== C. the registered lists point at files that exist")
    missing = []
    for rel in list(R.SUITES) + list(R.NODE_SUITES):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            missing.append(rel)
    check("every registered suite is on disk", not missing, missing)
    check("the node list is exactly the page harness",
          [os.path.basename(x) for x in R.NODE_SUITES] == ["ui_page_harness.js"],
          R.NODE_SUITES)
    dupes = [r for r in R.SUITES if R.SUITES.count(r) > 1]
    check("no suite is registered twice", not dupes, sorted(set(dupes)))

    print()
    if FAILS:
        print("RUNNER CONTRACT: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("RUNNER CONTRACT: IMPORTING IT IS INERT, AND A REPORT IS TOLD FROM A SENTENCE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
