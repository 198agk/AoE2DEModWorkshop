# -*- coding: utf-8 -*-
"""Are the remaining mentions of the dead workspace executable code or prose?

The rewrite scripts deliberately left docstrings and comments alone: those are a
record of where the project lived, and rewriting them would falsify history.

This check walks EVERY line of each file -- not just the matching ones -- so a
docstring that opened several lines earlier is still recognised as a docstring
when the match arrives.  An earlier version only looked at matching lines, so a
continuation line inside a module docstring read as code.  That is the same
mistake this project keeps paying for: a predicate that is true of the sample
being tested but not of the thing it claims to describe.
"""
import collections
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAT = re.compile(r"DeepSeek Harness[\\/]+工作区2")
TRIPLE = ('"""', "'''")


def classify(lines):
    """Yield (lineno, line, kind) for every line, tracking docstring state."""
    in_doc = None
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if in_doc is not None:
            yield i, s, "docstring"
            if in_doc in line:
                in_doc = None
            continue
        started = None
        for d in TRIPLE:
            if d in line:
                started = d
                break
        if started is not None:
            # does it close on the same line?
            first = line.find(started)
            if started not in line[first + 3:]:
                in_doc = started
            yield i, s, "docstring"
            continue
        if s.startswith("#"):
            yield i, s, "comment"
        elif s.startswith(("$", ">>>")) or "PYTHONPATH=" in s:
            yield i, s, "shell_line"
        elif s.startswith(("python ", "& $py", "pwsh ")):
            yield i, s, "shell_line"
        else:
            yield i, s, "code"


def main():
    kinds = collections.Counter()
    code = []
    total = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            try:
                text = io.open(p, encoding="utf-8").read()
            except Exception:
                continue
            rel = os.path.relpath(p, ROOT)
            for i, s, kind in classify(text.splitlines()):
                if not PAT.search(s):
                    continue
                total += 1
                kinds[kind] += 1
                if kind == "code":
                    code.append((rel, i, s))

    print("mentions of the dead workspace total: %d" % total)
    for k, n in kinds.most_common():
        print("  %-12s %d" % (k, n))
    print()
    if code:
        print("EXECUTABLE references still pointing at a directory that does not exist:")
        for rel, i, s in code:
            print("    %s:%d  %s" % (rel, i, s[:110]))
        return 1
    print("no executable line references the dead workspace.")
    print("(the rest are the history: docstrings, comments, and the shell lines")
    print(" quoted inside them.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
