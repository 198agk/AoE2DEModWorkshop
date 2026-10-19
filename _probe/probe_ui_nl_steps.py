# -*- coding: utf-8 -*-
"""Why the four sentences in test_ui_nl.py fail -- print what each step sees.

Not a test: the point is to see the span list, the leftover chunk and the
number for one sentence at a time instead of guessing from a final [].
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.semantic import index as SI                      # noqa: E402
from aoe2mod.ui import nl                                     # noqa: E402


def main():
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)
    for text in ("弓箭手攻击力加 2", "城堡血量改成 5000", "弓箭手",
                 "这是什么", "弓箭手木材成本加 10", "村民血量改成 1000",
                 "织布机研究时间减 5"):
        print("=" * 60)
        print("sentence: %r" % text)
        sp = vocab.spans(text)
        print("  spans: %s" % [(s[0].zh, s[1], s[2], len(s[3])) for s in sp])
        print("  number: %r" % (nl._number(text),))
        print("  op: %r" % nl._operation(nl._norm(text)))
        print("  stat: %r" % (nl._first_word(nl._norm(text), nl.STAT_WORDS),))
        print("  res : %r" % (nl._first_word(nl._norm(text), nl.RESOURCE_WORDS),))
        cl = nl.read_clause(text, vocab, civ_names=None, civ_zh=nl.CIV_ZH)
        print("  clause: intent=%r why=%r notes=%r" % (cl.intent, cl.why, cl.notes))
        print("  partial(弓箭手): %s" % [(e.zh, k) for e, k in
                                         vocab.find_partial("弓箭手")][:4])


if __name__ == "__main__":
    main()
