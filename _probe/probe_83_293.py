# -*- coding: utf-8 -*-
"""Why does 83 <- 293 refuse, when their families cover each other 10/10?"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A
from aoe2mod.intent import reskin as R

tk = A.open_toolkit()
tk._ensure()

p = tk.plan({"intent": "unit.sprite", "unit": 83, "donor": 293,
             "whole_family": True})
print("editable:", p.get("editable"))
print("reason  :", p.get("reason"))
print("skipped :", p.get("skipped"))
print()
print("=== what reskin.plan says directly ===")
rep = R.plan(tk.game_root, tk._stats["graphics"], tk._parsed[1], 83, 293)
print("ok    :", rep.get("ok"))
print("reason:", rep.get("reason"))
print("conflicts:", len(rep.get("conflicts") or ()))
for c in (rep.get("conflicts") or ())[:6]:
    print("   ", c)
print("skipped:", (rep.get("skipped") or ())[:6])
