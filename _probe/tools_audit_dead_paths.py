# -*- coding: utf-8 -*-
"""Classify every hardcoded reference to the dead workspace path.

Why
---
The workspace moved from `D:\\Software\\DeepSeek Harness\\工作区2` (inside the
application install directory, wiped by an update) to `D:\\Software\\AI\\帝国项目`.
Roughly 170 `.py` files still name the old directory.  They fail in two very
different ways and only one of them is loud:

  * `sys.path.insert(<dead>)` -- harmless only while the package also resolves
    from the real workspace; it silently imports whatever IS on the real path,
    which is what we want, but it is a lie about the source.
  * `os.path.join(<dead>, ...)` used as OUTPUT -- this is the dangerous one.
    The script writes into a directory that no longer exists, Python raises,
    or (worse) an `os.makedirs` recreates it and the result lands somewhere
    nobody looks while the script exits 0.

This script only CLASSIFIES.  The rewrite is a separate step so that the two
can be reviewed apart.
"""
import collections
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEAD = re.compile("DeepSeek Harness" + re.escape(os.sep) + "工作区2")
# The logs render the separator loosely, so accept both spellings.
DEAD_ANY = re.compile(r"DeepSeek Harness[\\/]+工作区2")


def classify(line):
    s = line.strip()
    if s.startswith("#"):
        return "comment"
    if "sys.path.insert" in s:
        return "path_insert"
    if "sys.path" in s and "=" in s:
        return "path_insert"
    if re.search(r"\b(OUT|OUTDIR|DST|DEST|TARGET_DIR|OUTPUT)\s*=", s):
        return "output_const"
    if re.search(r"\bopen\s*\(", s):
        return "open_call"
    if "os.makedirs" in s or "makedirs" in s:
        return "makedirs"
    if "os.path.join" in s:
        return "join"
    return "other"


def main():
    kinds = collections.Counter()
    samples = collections.defaultdict(list)
    per_file = collections.Counter()
    total_files = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            try:
                txt = io.open(p, encoding="utf-8").read()
            except Exception:
                continue
            hits = 0
            for ln, line in enumerate(txt.splitlines(), 1):
                if DEAD_ANY.search(line):
                    hits += 1
                    k = classify(line)
                    kinds[k] += 1
                    rel = os.path.relpath(p, ROOT)
                    if len(samples[k]) < 12:
                        samples[k].append((rel, ln, line.strip()[:120]))
            if hits:
                total_files += 1
                per_file[os.path.relpath(p, ROOT)] = hits

    print("files naming the dead workspace: %d" % total_files)
    print("total lines                   : %d" % sum(kinds.values()))
    print()
    for k, n in kinds.most_common():
        print("%-14s %d" % (k, n))
    print()
    for k in ("output_const", "open_call", "makedirs", "join", "other",
              "path_insert", "comment"):
        if not samples[k]:
            continue
        print("--- %s (%d)" % (k, kinds[k]))
        for rel, ln, s in samples[k]:
            print("    %s:%d  %s" % (rel, ln, s))
        print()
    worst = per_file.most_common(10)
    print("most-affected files:")
    for rel, n in worst:
        print("    %3d  %s" % (n, rel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
