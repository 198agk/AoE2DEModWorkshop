# -*- coding: utf-8 -*-
"""Keep the audit as a nail: no registered suite may print an unrecognised report.

The loosening in `_FAIL_RE` is only safe if every shape the suites can actually
print is still recognised.  Reading those strings by hand once is a measurement;
making it a file is a guarantee.  `_probe/test_effect_append.py`'s
`[FAIL] name :: detail` is the case that proved the difference.

The rule: take the string literals each suite prints, keep the ones that look
like a report (contain `::` or open with FAIL-ish text), and require every one of
them to match.  Prose and summaries are exempt by not looking like reports --
`CIVTECHTREES READER: 2 FAILED` is a summary and DOES match, which is fine.
"""
import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from _probe import run_suites as R  # noqa: E402

FAILS = []
WORDY = re.compile(r"fail|refus", re.I)


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILS.append(name)


_LABEL = re.compile(r"^([A-Z][A-Z0-9 _()/.\-]{2,}):")
_SUMMARY = re.compile(
    r"\bCHECK\(S\)\s+FAILED\b"
    r"|\bFAILURES:\s*(?:\d|%[sdr])"
    r"|\[\s*FAIL\s*\]"
    r"|\bFAIL\s+[^\s]+\s*::")
_FAIL_WORDS = ("FAIL", "FAILED", "FAILURE", "FAILURES", "FAILS")


def is_quiet_by_convention(text):
    """The two line shapes that are not reports, stated as conventions.

    NOT "does the rule miss it" -- that would be the audit asking the thing it is
    auditing.  These are the conventions every suite in this tree writes to:

      * a passing check starts with `ok`, and may quote any shape;
      * a sign-off starts with an ALL-CAPS label and a colon.  A failure WORD is
        not a label, so `FAILURES: 1 -> [...]` and `FAILED: name` stay reports;
        a label has no digits, so `FAILED 3 CHECK(S):` stays a report; and a line
        carrying a summary marker stays a report whatever its prefix says, so
        `NAIL HYGIENE: 2 CHECK(S) FAILED -> [...]` is still caught.
    """
    stripped = text.lstrip()
    if stripped.startswith("ok "):
        return True
    if _SUMMARY.search(stripped):
        return False
    m = _LABEL.match(stripped)
    if not m:
        return False
    label = m.group(1).strip()
    return label not in _FAIL_WORDS and not any(c.isdigit() for c in label)


def looks_like_report(text):
    if is_quiet_by_convention(text):
        return False
    if "::" in text:
        return True
    return text.lstrip().upper().startswith(("FAIL", "[FAIL", "FAILED", "FAILURE"))


def literals(rel):
    path = os.path.join(ROOT, rel)
    try:
        src = io.open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
    except (SyntaxError, OSError):
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if len(node.value) <= 400:
                out.append(node.value)
    return out


def liters_that_matter(rel):
    """Literals from a suite, skipping this file's own vocabulary.

    `test_fail_shapes.py` holds regexes whose text starts with `fail` (`fail|refus`),
    and the shape test below reads them as reports -- the audit reporting itself.
    That is the same confusion the audit exists to catch, one level up: a string
    that DESCRIBES a report is not a printed report.  Excluded by name, with this
    note, rather than by a cleverer heuristic: a heuristic that quietly skips
    strings would also skip the ones I need to see.
    """
    if os.path.basename(rel) == "test_fail_shapes.py":
        return []
    return literals(rel)


def main():
    print("=== A. every suite's printed report shapes are recognised")
    missed = []
    scanned = 0
    shapes = {}
    for rel in R.SUITES:
        if not rel.lower().endswith(".py"):
            continue
        scanned += 1
        for text in liters_that_matter(rel):
            if not looks_like_report(text) or not WORDY.search(text):
                continue
            shapes.setdefault(text, []).append(rel)
            if R._FAIL_RE.search(text) is None:
                missed.append((os.path.basename(rel), text))
    check("the scan reached the registered python suites", scanned > 100, scanned)
    check("and found report shapes at all", len(shapes) > 5, len(shapes))
    check("no report shape escapes the rule", not missed,
          [(n, t[:60]) for n, t in missed[:4]])

    print()
    print("=== B. prose that merely mentions the word is still ignored")
    prose = (
        ("the nail-hygiene sentence", "  ok   a FAIL at any column is recognised"),
        ("the gate-count sentence", "  37 have a failure gate"),
        ("an identifier", "IDS_FAILED_TO_OPEN_FILE"),
        ("the all-passed line", "SUITES: ALL PASSED"),
    )
    for name, text in prose:
        check("%s is not a report" % name, R._FAIL_RE.search(text) is None, text)

    print()
    print("=== C. and the shapes a real failure takes are caught")
    caught = (
        "  FAIL a :: b",
        "FAIL a :: b",
        "a :: FAIL",
        "NAIL HYGIENE: 2 CHECK(S) FAILED -> ['x']",
        "FAILURES: 1 -> ['x']",
        "  [FAIL] the cursor is not advanced :: 0 vs 11",
        "  FAILED: both halves stay in step",
    )
    for text in caught:
        check("caught %r" % text[:44], R._FAIL_RE.search(text) is not None, text)

    print()
    if FAILS:
        print("FAIL SHAPES: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    # NOT `FAIL SHAPES: ...`.  A verdict that starts with the word FAIL is the
    # one line shape a runner cannot tell from a report -- this suite cost a
    # whole 143-suite run on 2026-10-26 by exiting 0 and still being counted
    # red.  The guard is fixed too; this rename keeps the log readable.
    print("REPORT SHAPES: EVERY REPORT SHAPE THE SUITES CAN PRINT IS RECOGNISED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
