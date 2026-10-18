# -*- coding: utf-8 -*-
"""Confirm each mutation anchor occurs exactly once in the pristine copy."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

ANCHORS = [
    ("aoe2mod/game/buildpanel.py", '    ok = info["outside_is_untouched"]'),
    ("aoe2mod/game/buildpanel.py",
     'return text[:inner_end] + ",\\r\\n" + body + text[inner_end:]'),
    ("aoe2mod/game/buildpanel.py", "        if hit is None:\n            return text, removed"),
    ("aoe2mod/game/buildpanel.py",
     "    if _entry_spans(text, arr_lo, arr_hi, node_id):"),
    ("aoe2mod/game/buildpanel.py", "        removed += 1"),
    ("aoe2mod/game/sprites.py", "        if a and b and a != b:"),
    ("aoe2mod/game/civtechtrees.py",
     '    return st is not None and st != "NotAvailable"'),
    ("aoe2mod/game/civtechtrees.py", "    return out"),
    ("aoe2mod/mod/emitter.py", '    manifest["dat_is_carrier"] = dat_carrier'),
    ("aoe2mod/intent/datgrant.py", '    report["ok"] = True'),
    ("aoe2mod/intent/datgrant.py", "    patched[boff] = slot"),
    ("aoe2mod/intent/datgrant.py",
     '    report["edits"].append({"what": "button",'),
    ("aoe2mod/intent/reskin.py",
     '    rep["ok"] = not (rep["absent_targets"] or rep["not_\
donor"])'),
]

for rel, anchor in ANCHORS:
    p = os.path.join(ROOT, rel)
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    print("%-34s %2d  %r" % (os.path.basename(rel), s.count(anchor),
                             anchor[:70]))
