# -*- coding: utf-8 -*-
"""Rewrite stale `Run: $env:PYTHONPATH='D:\\...\\工作区2'` docstring lines in real
test files to the new workspace path.  The files already self-insert ROOT from
__file__, so this is documentation-only.  Excludes _probe/team/** (auditor copies)
and the tools_*_dead_paths scripts (which need the OLD path as their search target).
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# The docstrings are raw strings, so a Windows path separator is written as TWO
# backslash characters in the file.  A single-backslash OLD never matched, which
# is why the first run reported "rewrote 0 files".
OLD = "D:\\\\Software\\\\DeepSeek Harness\\\\工作区2"
NEW = "D:\\\\Software\\\\AI\\\\帝国项目"

SKIP_DIRS = {"team"}
SKIP_NAMES = {
    "tools_fix_dead_paths.py", "tools_fix_dead_paths2.py",
    "tools_fix_dead_paths3.py", "tools_check_dead_paths.py",
    "tools_audit_dead_paths.py", "tools_fix_docstring_paths.py",
}

changed = []
for dirpath, dirnames, filenames in os.walk(HERE):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        if not fn.endswith(".py") or fn in SKIP_NAMES:
            continue
        p = os.path.join(dirpath, fn)
        with io.open(p, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        if OLD not in text:
            continue
        new = text.replace(OLD, NEW)
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
        changed.append(os.path.relpath(p, ROOT))

print("rewrote %d files:" % len(changed))
for c in changed:
    print("  " + c)
