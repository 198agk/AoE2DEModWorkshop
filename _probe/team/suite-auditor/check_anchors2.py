# -*- coding: utf-8 -*-
"""Confirm each mutation anchor occurs exactly once in the pristine copy."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

ANCHORS = [
    ("aoe2mod/mod/emitter.py", '        "dat_is_carrier": dat_carrier,'),
    ("aoe2mod/mod/emitter.py",
     '    manifest["changes_dat"] = False if dat_carrier else (dat_bytes is not None)'),
    ("aoe2mod/intent/reskin.py",
     '    rep["ok"] = not (rep["absent_targets"] or rep["not_the_donor"])'),
    ("aoe2mod/intent/reskin.py", "def read_payload("),
    ("aoe2mod/game/civtechtrees.py", "def serialize(tree):"),
    ("aoe2mod/game/civtechtrees.py", '    return text.encode("utf-8")'),
    ("aoe2mod/game/civtechtrees.py", "def node_status("),
    ("aoe2mod/game/buildpanel.py", "def serialize_bytes("),
    ("aoe2mod/game/buildpanel.py", "def load_panel("),
    ("aoe2mod/api.py", "def _plan_availability("),
]

for rel, anchor in ANCHORS:
    p = os.path.join(ROOT, rel)
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    print("%-28s %2d  %r" % (os.path.basename(rel), s.count(anchor), anchor[:74]))
