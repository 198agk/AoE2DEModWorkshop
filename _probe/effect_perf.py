# -*- coding: utf-8 -*-
"""How long does the effect sweep take, before and after caching the walks?

`test_api.py`'s 8d section walks 41 techs and plans every one of their commands.
That used to stop finishing because `effects()` re-walked 1,510 tech records and
1,500 effects (10,500 commands) on every single call.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT]

from aoe2mod import api  # noqa: E402

tk = api.open_toolkit()

t0 = time.time()
tk.describe(4)
tk.describe(22)
print("warm load: %.2fs" % (time.time() - t0))

t0 = time.time()
for x in range(0, 1510, 37):
    tk.effects(x)
print("41 effects() calls: %.2fs" % (time.time() - t0))

t0 = time.time()
reachable = 0
commands = 0
for x in range(0, 1510, 37):
    for row in tk.effects(x)["rows"]:
        commands += 1
        try:
            if tk.plan({"intent": "tech.effect", "tech": x,
                        "command": row["index"], "delta": 1})["edit_count"] > 0:
                reachable += 1
        except Exception:
            pass
print("41 effects() + %d plans: %.2fs (%d reachable)"
      % (commands, time.time() - t0, reachable))
