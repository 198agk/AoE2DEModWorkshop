# -*- coding: utf-8 -*-
"""Which call inside effects() costs the time?"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT]

from aoe2mod import api  # noqa: E402
from aoe2mod.intent import compiler as C  # noqa: E402
from aoe2mod import semantic  # noqa: E402
from aoe2mod.semantic import index as semantic_index  # noqa: E402

tk = api.open_toolkit()
tk._ensure()
t0 = time.time()
ix = semantic_index.index()
print("semantic.index(): %.3fs" % (time.time() - t0))
for i in range(3):
    t0 = time.time()
    semantic_index.index()
    print("  again: %.4fs" % (time.time() - t0))

effs = tk._effect_records()
techs = tk._tech_records()
fan = tk._effect_fanout()
print("effects %d techs %d fanout %d" % (len(effs), len(techs), len(fan)))

t0 = time.time()
for x in range(0, 1510, 37):
    C.effect_rows(effs, techs[x], fanout=fan, ix=ix)
print("effect_rows alone, 41 calls: %.3fs" % (time.time() - t0))

t0 = time.time()
for x in range(0, 1510, 37):
    tk._resolve_tech(x)
print("_resolve_tech, 41 calls: %.3fs" % (time.time() - t0))

t0 = time.time()
for x in range(0, 1510, 37):
    tk.effects(x)
print("effects(), 41 calls: %.3fs" % (time.time() - t0))
