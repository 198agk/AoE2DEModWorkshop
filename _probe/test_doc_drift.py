"""The ledgers' numbers must match the tree, and this file must be able to say so.

Why this exists as a nail and not as a note: this project's most expensive recurring
failure is not a broken build, it is a sentence that was true on the day it was written.
The suite count has been written down as 23, 31, 43, 88, 93, 95, 96, 97, 99, 100, 101,
104, 105, 108, 110, 111, 112, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125 in
this repo, and at least three of those numbers were wrong when written.

Four things are asserted, and the second is what makes the first worth anything:

  1. every `N 条 py` / `N 条 node` claim presented as the CURRENT count equals the tree;
  2. a claim is only exempt as history when the line is actually dated -- and at least
     one such line exists;
  3. README -- the page a stranger reads first -- names every intent the schema ships.
     No exemption: the schema is today's schema, and a page that lists thirteen of
     fourteen intents is a stranger's only look at what the tool can do.
  4. the schema's own `compile` prose never says a thing was never done without naming a
     date, a `_probe` file or a run in the SAME leaf.  Those keys are read by whoever
     opens `intents.json` (nothing in Python reads them -- measured with grep), and three
     of them still claimed "not measured" after the runs that measured it: the new-unit
     icon, the hand-encoded SLD block, and the tech half of availability.

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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNNER = os.path.join(ROOT, "_probe", "run_suites.py")
#: The ledgers to scan for `N 条 py` claims.  Two of the original four are
#: session-handover notes that stopped being committed on 2026-11-18 (the
#: repository now carries the software only); they are still listed so a local
#: checkout that has them keeps getting scanned, and skipped when absent --
#: the check below asserts the file that everyone always has.
CLAIM_FILES = ("项目状态.md", "_交接说明.md", "_测试钉子清单.md", "README.md")

#: README is the one ledger a clone cannot be without: it is the page a
#: stranger reads first, so its claims are checked even when nothing else is
#: present.
ALWAYS_CLAIMED = ("README.md",)
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
    # Only README is guaranteed: the handover notes are a local working file,
    # not part of what this repository ships.  Asserting all four would fail a
    # fresh clone for the absence of a file that was deliberately not published.
    missing = [n for n in ALWAYS_CLAIMED if not os.path.isfile(os.path.join(ROOT, n))]
    check("the ledger every clone has is here", not missing, missing)
    present_ledgers = [n for n in CLAIM_FILES
                       if os.path.isfile(os.path.join(ROOT, n))]
    check("at least one ledger was actually read", len(present_ledgers) >= 1,
          present_ledgers)

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

    print("\n=== E. README names every intent the schema ships")
    # The schema is today's schema, so this check takes no exemption.  A page that
    # lists thirteen of fourteen intents is not a historical record -- it is a
    # stranger's first (and possibly only) look at what the tool can do.
    import subprocess

    _probe_src = os.path.join(HERE, "tmp_schema_ids.py")
    io.open(_probe_src, "w", encoding="utf-8", newline="").write(SCHEMA_SCRIPT)
    try:
        _out = subprocess.run(
            [sys.executable, "-X", "utf8", "-u", _probe_src],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
    finally:
        try:
            os.remove(_probe_src)
        except OSError:
            pass
    if _out.returncode != 0:
        check("the schema could be read in a child process", False,
              (_out.stderr or "")[-200:])
    else:
        _ids = [ln.strip() for ln in _out.stdout.splitlines() if ln.strip()]
        check("the schema names its intents", len(_ids) >= 10, len(_ids))
        _readme = io.open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
        _missing = [i for i in _ids if i not in _readme]
        check("README mentions every one of them", not _missing, _missing)

    print("\n=== F. schema prose does not assert a thing was never done without"
          " naming the evidence")
    # A tenth-surface version of the same drift: `intents.json`'s `compile` prose is
    # read by whoever opens the file (nothing in Python reads those keys -- measured
    # with `grep`), and three of them still claimed "not measured" / "never confirmed"
    # after the runs that measured it.  The rule is the one the ledgers already use:
    # a claim about absence must sit next to something checkable.
    #
    # Read with `json`, not through `compiler.load_schema()`: this file has to stay
    # cheap enough to run in a suite, and the schema path is a plain file.
    import json

    NEVER = ("no run has", "no run was", "never been confirmed", "never been measured",
             "NOT measured:", "has never been seen")
    EVIDENCE = re.compile(r"20\d\d-\d\d-\d\d|_probe[/\\]|dsh test v\d+")
    _doc = json.load(io.open(os.path.join(ROOT, "aoe2mod", "schema", "intents.json"),
                             encoding="utf-8"))
    _intents = _doc["intents"]
    _bare = []
    _scanned = 0
    for _name in sorted(_intents):
        _block = (_intents[_name] or {}).get("compile") or {}
        for _key, _val in _block.items():
            if not isinstance(_val, str):
                continue
            _low = _val.lower()
            if not any(p.lower() in _low for p in NEVER):
                continue
            _scanned += 1
            if not EVIDENCE.search(_val):
                _bare.append("%s.%s" % (_name, _key))
    check("the schema has compile prose at all", len(_intents) >= 10, len(_intents))
    for _b in _bare:
        print("       bare: %s -- says something was never done, names no date or test"
              % _b)
    check("every never-done claim names a date, a _probe file or a run", not _bare,
          "%d of %d" % (len(_bare), _scanned))

    # The three that were wrong are pinned by the evidence they now cite, so a later
    # rewrite cannot quietly take the proof back out.
    _create = ((_intents["unit.create"] or {}).get("compile") or {}).get(
        "what_it_cannot_do", "")
    _art = ((_intents["unit.art"] or {}).get("compile") or {}).get("why_not_copy", "")
    _tech = ((_intents["tech.availability"] or {}).get("compile") or {}).get(
        "why_no_dat_half", "")
    check("the new-unit icon sentence cites the run that drew it", "v85" in _create,
          _create[:80])
    check("...and no longer says the drawing was never measured",
          "no run has yet" not in _create.lower(), _create[:80])
    check("the hand-encoded art sentence cites the runs that drew it",
          "v71" in _art and "v73" in _art, _art[:80])
    check("...and still says which layer has no encoder", "unknown2" in _art, _art[:80])
    check("the tech-availability sentence cites the unit runs it is contrasted with",
          "v7" in _tech and "v17" in _tech, _tech[:80])
    check("...and no longer claims no recipe was ever confirmed",
          "no recipe here has ever been confirmed" not in _tech.lower(), _tech[:80])

    print()
    if FAILED:
        print("DOC DRIFT: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("DOC DRIFT: %d CHECKS PASSED -- THE LEDGERS' COUNTS ARE THE TREE'S COUNTS, "
          "A DATED RECORD IS STILL RECOGNISED AS ONE, THE README NAMES EVERY "
          "INTENT THE SCHEMA SHIPS, AND AN ABSENCE-CLAIM CARRIES ITS EVIDENCE"
          % OK[0])
    return 0


# Printed by the E section in a child process: the intent ids the schema ships
# today.  It runs out of process because reading the schema pulls in the whole
# compiler, and this file must stay cheap enough to run in a suite.
SCHEMA_SCRIPT = """# -*- coding: utf-8 -*-
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import aoe2mod.intent.compiler as C

schema, _bindings = C.load_schema()
for _name in sorted(schema["intents"]):
    print(_name)
"""


if __name__ == "__main__":
    raise SystemExit(main())
