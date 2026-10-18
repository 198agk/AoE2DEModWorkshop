# -*- coding: utf-8 -*-
"""Anchors for the third mutation batch (intent-targeted)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

ANCHORS = [
    ("aoe2mod/game/civtechtrees.py",
     "    found = set()\n    for e in _rows(tree):"),
    ("aoe2mod/game/civtechtrees.py",
     "    if not found:\n        return None"),
    ("aoe2mod/game/civtechtrees.py",
     "    return [e for e in _rows(tree)"),
    ("aoe2mod/intent/compiler.py",
     '    if kind == "float":\n'
     '        new = (before + amount) if op == "delta" else float(amount)'),
    ("aoe2mod/mod/emitter.py",
     '    manifest["changes_dat"] = False if dat_carrier else (dat_bytes is not None)'),
    ("aoe2mod/intent/datgrant.py",
     '    report["edits"].append({"what": "effect+tech",'),
]

for rel, anchor in ANCHORS:
    p = os.path.join(ROOT, rel)
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    print("%-24s %2d  %r" % (os.path.basename(rel), s.count(anchor), anchor[:76]))
