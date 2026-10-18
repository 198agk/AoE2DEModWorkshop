# -*- coding: utf-8 -*-
"""Which test_*.py / probe_*.py files exist but are NOT in run_suites SUITES?"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

with open(os.path.join(HERE, "suite_list.txt"), encoding="utf-8") as fh:
    registered = set(ln.strip().replace("\\", "/") for ln in fh if ln.strip())

probe = os.path.join(ROOT, "_probe")
tests = os.path.join(ROOT, "aoe2mod", "tests")

cands = []
for d, rel in ((probe, "_probe"), (tests, "aoe2mod/tests")):
    for n in sorted(os.listdir(d)):
        if not n.endswith(".py"):
            continue
        if not (n.startswith("test_") or n.startswith("probe_")):
            continue
        cands.append(rel + "/" + n)

missing = [c for c in cands if c not in registered]
print("registered: %d   candidate files: %d   unregistered: %d"
      % (len(registered), len(cands), len(missing)))
for c in missing:
    print("  NOT RUN: %s (%d B)" % (c, os.path.getsize(os.path.join(ROOT, c))))
