# -*- coding: utf-8 -*-
"""Check anchors for the second mutation batch."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

ANCHORS = [
    ("aoe2mod/game/civtechtrees.py", '    return text.encode("utf-8")'),
    ("aoe2mod/intent/compiler.py",
     '    new = (before + amount) if op == "delta" else amount'),
    ("aoe2mod/intent/compiler.py", "def _apply(op, amount, kind, before):"),
    ("aoe2mod/game/civtechtrees.py",
     '        if (isinstance(e, dict) and e.get("Use Type") in use_types\n'
     '                and e.get("Node ID") == node_id):'),
    ("aoe2mod/game/civtechtrees.py", '    return st is not None and st != "NotAvailable"'),
    ("aoe2mod/game/civtechtrees.py", "def tech_rows("),
    ("aoe2mod/game/civtechtrees.py", '    return (list(tree.get(UNITS_KEY) or []) + list(tree.get(BUILDINGS_KEY) or []))'),
]

for rel, anchor in ANCHORS:
    p = os.path.join(ROOT, rel)
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    print("%-26s %2d  %r" % (os.path.basename(rel), s.count(anchor), anchor[:78]))
