# -*- coding: utf-8 -*-
"""Measure the five intents the screen could not say before this round.

Why this file exists: the sentence reader grew five branches in one step
(attack class, effect by ordinal, sprite donor, art path, and the "research"
verbs for technology availability).  Reading the code tells you the branch is
reachable; it does not tell you what a real sentence turns into.  Every case
below prints the intent AND the preview sentence the player would see, because
a wrong-but-confident answer only shows up in the sentence.

One-off measurement, not a suite.  The permanent versions of these cases live
in `_probe/test_ui_nl.py`.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import aoe2mod.api as A
from aoe2mod.semantic import index as SI
from aoe2mod.ui import nl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    tk = A.open_toolkit(game_root=GAME)
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)
    tk._ensure()
    vocab.call_count = 0

    def effect_count(tid):
        return tk.effect_count(tid)

    print("classes known: %d" % len(nl.class_names()))
    print("class 12 -> %r" % (nl.class_names().get(12),))

    png = os.path.join(ROOT, "_shots", "live_unit83.png")
    print("picture exists: %s (%s)" % (os.path.isfile(png), png))

    cases = [
        # --- unit.attack_class -------------------------------------------
        "步弓手对骑兵攻击加2",
        "步弓手对骑兵防御加2",
        "步弓手对骑兵加2",
        "村民对建筑攻击加10",
        "骑兵的血量改成1000",
        # --- tech.effect --------------------------------------------------
        "织布机第2条效果加5",
        "织布机效果加5",
        "织布机第9条效果加5",
        "科技1效果加5",
        # --- tech.availability with 研究 ---------------------------------
        "印加不能研究织布机",
        "给不列颠解锁研究织布机",
        # --- unit.sprite --------------------------------------------------
        "把村民的样子换成步弓手",
        "村民的样子改成步弓手",
        "把村民的样子换成步弓手，连干活的样子一起换",
        "村民换成1000",
        "把村民的样子换成村民",
        # --- unit.art -----------------------------------------------------
        "给村民换张图 " + png,
        "给织布机换张图 " + png,
        # --- things that must still work ----------------------------------
        "村民血量改成1000",
        "织布机研究时间减5",
        "印加不能造蔷琵侦察兵",
    ]

    for text in cases:
        intents, clauses = nl.read(text, vocab, civ_names=tk.civ_names,
                                   civ_zh=nl.CIV_ZH, effect_count=effect_count)
        print("\n--- %s" % text)
        for cl in clauses:
            if cl.intent is None:
                print("    NO  why=%s" % cl.why)
            else:
                print("    YES %r" % (cl.intent,))
            for n in cl.notes:
                print("        note: %s" % n)
            if cl.intent is None:
                continue
            try:
                p = tk.plan(cl.intent)
                print("        preview: %s | edits=%s"
                      % (p.get("description"), p.get("edit_count")))
            except Exception as exc:
                print("        PLAN FAILED %s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    main()
