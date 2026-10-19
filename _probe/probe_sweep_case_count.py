# -*- coding: utf-8 -*-
"""How many cases does _probe/test_full_sweep.py have to compile?  Cheap count."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.intent import compiler as C                    # noqa: E402

schema, _bindings = C.load_schema()
stats = schema["intents"]["unit.stat"]["fields"]["stat"]["options"]
res = schema["intents"]["unit.cost"]["fields"]["resource"]["options"]
cls = schema["intents"]["unit.attack_class"]["fields"]["kind"]["options"]
units = 16                      # len(UNITS) in the sweep
avail = 4
effect = 2
total = units * (len(stats) + len(res) + len(cls)) + avail + effect
print("unit.stat options    : %d" % len(stats))
print("unit.cost resources  : %d" % len(res))
print("attack_class kinds   : %d" % len(cls))
print("per-unit cases       : %d" % (len(stats) + len(res) + len(cls)))
print("total compiled cases : %d  (+%d availability, +%d tech.effect)"
      % (total, avail, effect))
print("at ~50 s each (the module's own estimate): %.1f hours"
      % (total * 50.0 / 3600.0))
