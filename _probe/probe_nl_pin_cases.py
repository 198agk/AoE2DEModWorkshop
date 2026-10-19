# -*- coding: utf-8 -*-
"""Measure the exact sentences the new branches should accept and refuse.

Written before pinning anything: every assertion added to `test_ui_nl.py` has to
be a sentence whose answer was OBSERVED, otherwise the test encodes what I hoped
the parser does.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from aoe2mod.semantic import index as SI
from aoe2mod.ui import nl

idx = SI.index()
vocab = nl.Vocabulary(idx.units, idx.techs)


def fake_effects(tech_id):
    # Loom (22) has three commands; most technologies are not this one.
    return {22: 3, 0: 0}.get(tech_id, 1)


def read(text):
    return nl.read(text, vocab, civ_names=None, civ_zh=nl.CIV_ZH,
                   effect_count=fake_effects)


CASES = [
    # attack_class
    "步弓手对骑兵攻击加2",
    "步弓手对骑兵防御加2",
    "步弓手对骑兵加2",
    "步弓手对骑兵攻击力减3",
    "骑兵的血量改成1000",
    "城堡对骑兵攻击加2",
    # tech.effect
    "织布机第2条效果加5",
    "织布机效果加5",
    "织布机第9条效果加5",
    "织布机第1条效果改成10",
    "织布机效果减2",
    # tech.availability via 研究
    "印加不能研究织布机",
    "给不列颠解锁研究织布机",
    "印加可以研究织布机吗",
    # unit.sprite ordering
    "把村民的样子换成步弓手",
    "把步弓手的样子换成村民",
    "村民的样子换成步弓手",
    "把村民的样子换成步弓手，连干活的样子一起换",
    "把村民的样子换成步弓手 连干活的样子一起换",
    "把村民的样子换成村民",
    "把织布机的样子换成步弓手",
    "把村民的样子换成步弓手，血量改成1000",
    # unit.art
    "给村民换张图 D:\\pics\\a.png",
    "给织布机换张图 D:\\pics\\a.png",
    "村民换张图",
]

for text in CASES:
    intents, clauses = read(text)
    print("\n--- %s" % text)
    for cl in clauses:
        print("    %s %r" % ("YES" if cl.intent else "NO ", cl.intent or cl.why))
        for n in cl.notes:
            print("        note: %s" % n)
