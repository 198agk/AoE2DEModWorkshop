# -*- coding: utf-8 -*-
"""Anchors for batch 3: writer mismatch accounting, int delta, sprite index."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

ANCHORS = [
    ("aoe2mod/dat/writer.py", "                self.mismatches += 1"),
    ("aoe2mod/dat/writer.py", "    new = (before + amount) if op == \"delta\" else amount"),
    ("aoe2mod/intent/compiler.py", "    new = (before + amount) if op == \"delta\" else amount"),
    ("aoe2mod/game/sprites.py", "                self._by_id.setdefault(g[\"id\"], g)"),
    ("aoe2mod/game/buildpanel.py", "    if _entry_spans(text, arr_lo, arr_hi, node_id):"),
    ("_probe/test_dat_edit_routes.py", "route 3 touches only 2 field groups"),
]

for rel, anchor in ANCHORS:
    p = os.path.join(ROOT, rel)
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    print("%-26s %2d  %r" % (os.path.basename(rel), s.count(anchor), anchor[:70]))

for rel in ("_probe/test_dat_edit_routes.py", "aoe2mod/tests/test_emit_mod.py",
            "_probe/test_unit_sprite_chain.py"):
    print("exists %-34s %s" % (rel, os.path.isfile(os.path.join(ROOT, rel))))
