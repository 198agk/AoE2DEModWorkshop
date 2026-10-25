"""The ledgers' numbers must match the tree, and this file must be able to say so.

Why this exists as a nail and not as a note: this project's most expensive recurring
failure is not a broken build, it is a sentence that was true on the day it was written.
The suite count has been written down as 23, 31, 43, 88, 93, 95, 96, 97, 99, 100, 101,
104, 105, 108, 110, 111, 112, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125 in
this repo, and at least three of those numbers were wrong when written.

Two things are asserted, and the second is the one that makes the first worth anything:

  1. every `N 条 py` / `N 条 node` claim presented as the CURRENT count equals the tree;
  2. a claim is only exempt as history when the line is actually dated -- and at least
     one such line exists.

Without (2) the file could report a clean 0 because the dated-record rule stopped
matching (reporting every record as drift) or because the files stopped being read at
all.  Both were live failure modes: the first version printed `current count drift: 0`
and returned 0 unconditionally, and the text-slicing version of the registration reader
silently dropped two entries when a comment contained `]`.

Deliberately NOT asserted: the exact count itself.  Pinning `125` here would make this
file need editing every time a suite is added -- the thing it exists to prevent.
"""
import ast
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNNER = os.path.join(ROOT, "_probe", "run_suites.py")
CLAIM_FILES = ("项目状态.md", "_交接说明.md", "_测试钉子清单.md", "README.md")
DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")
CLAIM_RE = re.compile(r"(\d+)\s*条\s*(py|node)")
HISTORY_PHRASES = ("当时", "曾", "原来", "历史", "长到", "写成了", "那轮跑的",
                   "现在注册")

FAILED = []
OK = [0]


def check(name, cond, detail=""):
    if cond:
        OK[0] += 1
        print("  ok   %s" % name)
    else:
        FAILED.append(name)
        print("  FAIL %s%s" % (name, (" :: " + str(detail)) if detail else ""))


def registered():
    """(python entries, node entries) read with the parser, never by slicing text."""
    tree = ast.parse(io.open(RUNNER, encoding="utf-8").read())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("SUITES", "NODE_SUITES"):
                    out[target.id] = [e.value for e in node.value.elts
                                      if isinstance(e, ast.Constant)]
    return out.get("SUITES", []), out.get("NODE_SUITES", [])


def claims():
    rows = []
    for name in CLAIM_FILES:
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            continue
        for i, line in enumerate(io.open(path, encoding="utf-8").read().splitlines(), 1):
            for m in CLAIM_RE.finditer(line):
                rows.append((name, i, int(m.group(1)), m.group(2), line.strip()))
    return rows


def is_dated(text):
    return any(p in text for p in HISTORY_PHRASES) or DATE_RE.search(text) is not None


def main():
    print("=== A. the registration table is readable both ways")
    pys, nodes = registered()
    check("the runner registers well over a hundred python suites", len(pys) > 100,
          len(pys))
    check("and exactly one node suite", len(nodes) == 1, nodes)
    names = [p.replace("/", "\\").rsplit("\\", 1)[-1] for p in pys]
    check("no suite is registered twice", len(names) == len(set(names)),
          [n for n in set(names) if names.count(n) > 1])
    absent = [p for p in pys if not os.path.isfile(os.path.join(ROOT, p))]
    check("every registered file exists", not absent, absent)
    # The slice bug dropped entries silently, so the property to assert is coverage of
    # BOTH roots -- not "everything is under _probe", which stopped being true when the
    # aoe2mod/tests suites were registered (116 vs 125; this line was the wrong one).
    check("every entry looks like a python suite path",
          all(isinstance(p, str) and p.endswith(".py") and len(p) > 8 for p in pys),
          [p for p in pys if not (isinstance(p, str) and p.endswith(".py"))][:3])
    _under_probe = [p for p in pys if "_probe" in p]
    _under_pkg = [p for p in pys if "aoe2mod" in p]
    check("the parsed set covers both roots, so no entry was dropped",
          _under_probe and _under_pkg
          and len(_under_probe) + len(_under_pkg) == len(pys),
          "%d under _probe, %d under aoe2mod, %d total"
          % (len(_under_probe), len(_under_pkg), len(pys)))

    print("\n=== B. the claim files are there to be read")
    missing = [n for n in CLAIM_FILES if not os.path.isfile(os.path.join(ROOT, n))]
    check("all four ledgers exist", not missing, missing)

    print("\n=== C. current counts match the tree")
    rows = claims()
    check("the ledgers contain claims at all", len(rows) > 10, len(rows))
    wrong = []
    dated = 0
    for name, line_no, n, kind, text in rows:
        want = len(pys) if kind == "py" else len(nodes)
        if n == want:
            continue
        if is_dated(text):
            dated += 1
            continue
        wrong.append("%s:%d %d %s (now %d) %s" % (name, line_no, n, kind, want, text[:70]))
    for w in wrong:
        print("       drift: %s" % w)
    check("no undated claim disagrees with the tree", not wrong, len(wrong))

    print("\n=== D. the dated-record rule is still doing work")
    check("at least one claim is exempt as a dated record", dated > 0, dated)
    check("...and the exemption is narrower than the whole set", dated < len(rows),
          "%d of %d" % (dated, len(rows)))

    print()
    if FAILED:
        print("DOC DRIFT: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("DOC DRIFT: %d CHECKS PASSED -- THE LEDGERS' COUNTS ARE THE TREE'S COUNTS, "
          "AND A DATED RECORD IS STILL RECOGNISED AS ONE" % OK[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
