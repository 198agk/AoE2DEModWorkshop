# -*- coding: utf-8 -*-
"""What the UI needs to match Chinese words to ids, and nothing else.

Prints: the civ names the API reports, whether the semantic index resolves a
few Chinese unit names, and the zh labels the schema already carries for the
stats a UI is allowed to touch.  Designing a word list against guesses is the
mistake this file exists to prevent.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.intent import compiler as C                         # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    tk = A.open_toolkit(game_root=GAME)
    print("civ_names (%d):" % len(tk.civ_names))
    print(json.dumps(tk.civ_names, ensure_ascii=False))

    print("\nsearch for a few Chinese words:")
    for q, kind in (("村民", "unit"), ("弓箭手", "unit"), ("剑士", "unit"),
                    ("织布机", "tech"), ("蔷琵", "unit"), ("蔷琵侦察兵", "unit")):
        hits = tk.search(q, kind=kind, limit=4)
        print("  %-8s %-4s -> %s" % (q, kind,
              [(h["id"], h["name"]) for h in hits]))

    intents, bindings = C.load_schema()
    print("\nunit.stat stat options and the zh label the schema gives them:")
    for opt in intents["intents"]["unit.stat"]["fields"]["stat"]["options"]:
        print("  %-26s %r" % (opt, C.STAT_ZH.get(opt) if hasattr(C, "STAT_ZH") else None))


if __name__ == "__main__":
    main()
