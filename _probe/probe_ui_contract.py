# -*- coding: utf-8 -*-
"""What a UI gets back from the four calls it would actually make.

Not a test -- a transcript.  The point is to stop designing the screen against
guesses: print the exact dict keys `search`, `describe`, `plan` and `mods`
return for one concrete request, plus which ones are cheap enough to call on
every keystroke.

Run: PYTHONPATH=<root> python _probe/probe_ui_contract.py
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def _short(obj, depth=0):
    """Stringify without dumping the 63-entry lists into the report."""
    if isinstance(obj, dict):
        if depth > 2:
            return "{...%d keys}" % len(obj)
        return {k: _short(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        if len(obj) > 4:
            return [_short(v, depth + 1) for v in obj[:3]] + ["...+%d more" % (len(obj) - 3)]
        return [_short(v, depth + 1) for v in obj]
    return obj


def main():
    t0 = time.time()
    tk = A.open_toolkit(game_root=GAME)
    print("open_toolkit: %.2fs" % (time.time() - t0))

    t = time.time()
    hits = tk.search("villager", kind="unit")
    print("\nsearch('villager', kind='unit'): %.3fs, %d hits" % (time.time() - t, len(hits)))
    print(json.dumps(hits[:3], ensure_ascii=False, indent=2))

    t = time.time()
    zh = tk.search("村民", kind="unit")
    print("\nsearch('村民', kind='unit'): %.3fs, %d hits" % (time.time() - t, len(zh)))
    print(json.dumps(zh[:3], ensure_ascii=False, indent=2))

    t = time.time()
    d = tk.describe(83, kind="unit")
    print("\ndescribe(83, 'unit'): %.3fs" % (time.time() - t))
    print(json.dumps(_short(d), ensure_ascii=False, indent=2))

    t = time.time()
    p = tk.plan({"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 1000})
    print("\nplan(hit_points=1000): %.3fs" % (time.time() - t))
    print(json.dumps(_short(p), ensure_ascii=False, indent=2))

    t = time.time()
    p2 = tk.plan({"intent": "unit.availability",
                  "unit": 2550, "action": "revoke", "civ": "Incas"})
    print("\nplan(availability revoke, Incas, 2550): %.3fs" % (time.time() - t))
    print(json.dumps(_short(p2), ensure_ascii=False, indent=2))

    t = time.time()
    m = tk.mods()
    print("\nmods(): %.3fs, %d entries" % (time.time() - t, len(m)))
    print(json.dumps(_short(m[:2]), ensure_ascii=False, indent=2))

    print("\nUI CONTRACT: printed above")


if __name__ == "__main__":
    main()
