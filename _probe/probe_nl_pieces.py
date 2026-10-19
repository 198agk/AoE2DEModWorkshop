# -*- coding: utf-8 -*-
"""One-off: how does the comma splitter treat a sprite sentence with a tail?"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import aoe2mod.api as A
from aoe2mod.semantic import index as SI
from aoe2mod.ui import nl

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

tk = A.open_toolkit(game_root=GAME)
idx = SI.index()
vocab = nl.Vocabulary(idx.units, idx.techs)
tk._ensure()

for text in [
    "把村民的样子换成步弓手 连干活的样子一起换",
    "把村民的样子换成步弓手，连干活的样子一起换",
    "把村民的样子换成步弓手并且连干活的样子一起换",
    "村民连干活的样子一起换成步弓手",
    "把村民的样子换成步弓手",
]:
    print("\n--- %s" % text)
    print("    pieces: %r" % (_ for _ in ()) if False else "    pieces: %r"
          % (nl._pieces(text, vocab),))
    intents, clauses = nl.read(text, vocab, civ_names=tk.civ_names,
                               civ_zh=nl.CIV_ZH, effect_count=tk.effect_count)
    for cl in clauses:
        print("    %s %r" % ("YES" if cl.intent else "NO ", cl.intent if cl.intent else cl.why))
        for n in cl.notes:
            print("        note: %s" % n)
