# -*- coding: utf-8 -*-
"""Why can a row say editable=True while plan() refuses the same command?"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT]

from aoe2mod import api  # noqa: E402
from aoe2mod.intent import compiler as C  # noqa: E402

tk = api.open_toolkit()

for tech, cmd in ((999, 6), (1369, 5), (1369, 6)):
    e = tk.effects(tech)
    row = e["rows"][cmd]
    print("tech %d cmd %d" % (tech, cmd))
    for k in ("type", "type_label", "operation", "scope", "attribute",
              "attribute_label", "target_kind", "target", "target_label",
              "value", "editable", "reason"):
        print("   %-16s %r" % (k, row.get(k)))
    for delta in (1, 0, -1, 2):
        try:
            p = tk.plan({"intent": "tech.effect", "tech": tech,
                         "command": cmd, "delta": delta})
            print("   delta %+d -> edit_count %s  %s"
                  % (delta, p["edit_count"], p["description"]))
        except C.IntentError as exc:
            print("   delta %+d -> REFUSED %s" % (delta, exc))
