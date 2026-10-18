# -*- coding: utf-8 -*-
"""Which suites mention each declared intent name, and in what form.

Read-only. Prints one line per intent: intent, then the suites that name it,
distinguishing a real plan()/build() call from a mere string in a comment.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCHEMA = os.path.join(ROOT, "aoe2mod", "schema", "intents.json")

with open(SCHEMA, encoding="utf-8") as fh:
    schema = json.load(fh)
names = list(schema["intents"])

files = []
troot = os.path.join(ROOT, "aoe2mod", "tests")
for n in sorted(os.listdir(troot)):
    if n.endswith(".py"):
        files.append(os.path.join(troot, n))
with open(os.path.join(HERE, "suite_list.txt"), encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            files.append(os.path.join(ROOT, line))

STR = re.compile(r"""["'](%s)["']""" % "|".join(re.escape(n) for n in names))

for name in names:
    hits = []
    for p in files:
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        n_str = 0
        n_comment = 0
        for ln in lines:
            if name not in ln:
                continue
            if STR.search(ln):
                n_str += 1
            elif "#" in ln and ln.index("#") < ln.index(name):
                n_comment += 1
        if n_str or n_comment:
            hits.append((os.path.basename(p), n_str, n_comment))
    print(name)
    for base, s, c in sorted(hits, key=lambda x: (-x[1], x[0])):
        print("    %-40s literal=%-3d comment=%d" % (base, s, c))
    if not hits:
        print("    (no suite names this intent)")
print()
print("files scanned: %d" % len(files))
