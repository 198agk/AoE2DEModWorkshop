# -*- coding: utf-8 -*-
"""Does an ENGLISH refusal actually reach the screen?  Measure, don't assume.

`aoe2mod/ui/server.py:331` builds the page's `.why` line as
`"%s: %s" % (type(exc).__name__, exc)`, so any `raise IntentError("...")`
becomes visible text.  `test_prose_language.py` only walks `description` /
`reason` / `warnings`, so this surface has never been checked.

This asks the App object DIRECTLY (no socket) for a few sentences a player
could really type, and prints exactly what the page would show in its `.why`
div.  No socket on purpose: the earlier socket version sat at 0 CPU for five
minutes, and the question -- "what text does `_safe_plan` hand the page?" -- is
answerable one call above HTTP.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from aoe2mod.ui import server as S

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

SENTENCES = [
    "织布机第1条效果加5",            # editable path
    "织布机第2条效果改成3",           # armour command: packed byte
    "村民血量改成0",                 # fits
    "村民血量改成-5",                # negative refusal
    "织布机成本加999999",             # int field
    "步弓手对骑兵攻击加300",           # packed byte out of range
    "村民血量改成abc",                # no number
]


def main():
    app = S.App(game_root=GAME)
    for text in SENTENCES:
        got = app.parse(text)
        for c in got.get("clauses") or []:
            pv = c.get("preview") or {}
            line = (pv.get("plan") or {}).get("description") if pv.get("ok") \
                else pv.get("error")
            name = (c.get("intent") or {}).get("intent") or "-"
            print("%-20s intent=%-20s buildable=%-5s -> %s"
                  % (text, name, c.get("buildable"), line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
