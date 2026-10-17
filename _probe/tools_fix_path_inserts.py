# -*- coding: utf-8 -*-
"""Repair the two things the bulk rewrite got wrong.

1. `sys.path.insert(0, _HERE_PATH())` -- `_HERE_PATH()` is the DIRECTORY OF THE
   FILE.  For a probe in `_probe/` that is `_probe/`, which contains no
   `aoe2mod` package, so the import that followed now depends on the caller's
   cwd.  62 files were rewritten this way and the loud failure only shows up
   when someone runs one from a different directory.  The root is two levels up
   from `_probe/`, one level up from `aoe2mod/tests/`, and zero from the repo
   root, so insert the right number of ".." segments.

2. Docstrings that quoted the old path got the same substitution and now read
   `Run:  $env:PYTHONPATH=_HERE_PATH()`, which is not a shell command.  Inside
   prose the truthful replacement is the NEW absolute path, not a lambda call.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = ROOT


def rel_depth(path):
    d = os.path.dirname(os.path.abspath(path))
    rel = os.path.relpath(d, ROOT)
    if rel == ".":
        return 0
    return len(rel.split(os.sep))


def fix_sys_path(text, depth):
    """Point sys.path at the repo root, not at the file's own directory."""
    arg = ("..",) * depth
    target = '_HERE_PATH(%s)' % ", ".join('"%s"' % a for a in arg) if depth else "_ROOT_PATH()"
    pat = re.compile(r"_HERE_PATH\(\)(\s*\)\s*#.*)?")
    n = 0

    def sub(m):
        nonlocal n
        n += 1
        return target + (m.group(1) or "")

    # only on sys.path lines
    out = []
    for line in text.splitlines(True):
        if "sys.path" in line and "_HERE_PATH()" in line:
            line = pat.sub(sub, line)
        out.append(line)
    return "".join(out), n


def fix_docstring_calls(text):
    """Inside a docstring a lambda call is not a path.  Put the real one back."""
    lines = text.splitlines(True)
    out = []
    in_doc = None
    n = 0
    for line in lines:
        if in_doc is not None:
            if "_HERE_PATH()" in line or "_ROOT_PATH()" in line:
                line = line.replace("_HERE_PATH()", REAL).replace("_ROOT_PATH()", REAL)
                n += 1
            out.append(line)
            if in_doc in line:
                in_doc = None
            continue
        started = None
        for d in ('"""', "'''"):
            if d in line:
                started = d
                break
        if started is not None:
            first = line.find(started)
            if started not in line[first + 3:]:
                in_doc = started
            out.append(line)
            continue
        out.append(line)
    return "".join(out), n


def main(argv):
    dry = "--dry" in argv
    fixed_path = fixed_doc = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            # These repair tools contain `_HERE_PATH()` as a PATTERN, not a call.
            if f.startswith("tools_"):
                continue
            try:
                text = io.open(p, encoding="utf-8").read()
            except Exception:
                continue
            if "_HERE_PATH()" not in text and "_ROOT_PATH()" not in text:
                continue
            new, n1 = fix_sys_path(text, rel_depth(p))
            new, n2 = fix_docstring_calls(new)
            if new == text:
                continue
            try:
                compile(new, p, "exec")
            except SyntaxError as exc:
                print("  BAD  %s: %s" % (os.path.relpath(p, ROOT), exc))
                return 1
            rel = os.path.relpath(p, ROOT)
            if n1:
                print("  PATH %-56s %d line(s)" % (rel, n1))
                fixed_path += n1
            if n2:
                print("  DOC  %-56s %d line(s)" % (rel, n2))
                fixed_doc += n2
            if not dry:
                with io.open(p, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new)
    print()
    print("sys.path lines repointed: %d, docstring prose restored: %d%s"
          % (fixed_path, fixed_doc, " (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
