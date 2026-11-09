# -*- coding: utf-8 -*-
"""The exact contract case: a reference that RESOLVES but whose change is a
no-op because the record does not store that field.

Unit 406 (树木 H) plans `edit_count=0`.  Does build() return a dict saying so,
or does it write a mod that changes nothing?
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
import aoe2mod.api as A
from aoe2mod.intent.compiler import IntentError

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "scratch", "s10")

CASES = [
    ("tree_no_attack", {'intent': 'unit.stat', 'unit': r'树木 H',
                        'stat': 'displayed_attack', 'delta': 1}),
    ("organ_d_no_attack", {'intent': 'unit.stat', 'unit': 'ORGAN_D',
                           'stat': 'displayed_attack', 'delta': 1}),
    ("archer_delta0", {'intent': 'unit.stat', 'unit': '步弓手',
                       'stat': 'hit_points', 'delta': 0}),
]

tk = A.Toolkit(ROOT)
for tag, it in CASES:
    print("--", tag)
    try:
        p = tk.plan(it)
        print("   plan : edit_count=%r desc=%r" % (p.get("edit_count"), p.get("description")))
    except IntentError as e:
        print("   plan RAISED:", e)
        continue
    d = os.path.join(OUT, tag)
    try:
        man = tk.build(it, d, title=tag, author="kv", overwrite=True)
    except IntentError as e:
        print("   build RAISED:", e)
        print("   files left:", os.listdir(d) if os.path.isdir(d) else None)
        continue
    print("   build: edit_count=%r changes_dat=%r dat_identical_to_base=%r"
          % (man.get("edit_count"), man.get("changes_dat"),
             man.get("dat_identical_to_base")))
    print("   build warnings:", man.get("warnings"))
    print("   verification.ok=%r changed=%r claimed=%r"
          % (man["verification"]["ok"], man["verification"]["changed_bytes"],
             man["verification"]["claimed_bytes"]))
    print("   files on disk:", sorted(
        os.path.relpath(os.path.join(dp, f), d)
        for dp, _, fs in os.walk(d) for f in fs))
    print()
