# -*- coding: utf-8 -*-
"""Verify every batch2 anchor is unique before running it."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import batch2  # noqa: E402

for label, suite, target, old, new, why in batch2.MUTATIONS:
    p = os.path.join(ROOT, target)
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    sp = os.path.join(ROOT, suite)
    print("%-30s target:%-3d suite:%s" % (label, s.count(old),
                                          os.path.isfile(sp)))
