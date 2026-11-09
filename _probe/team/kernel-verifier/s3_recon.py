# -*- coding: utf-8 -*-
"""CLAIM 3 reconnaissance: what do the candidate intents PLAN to do?

No build here -- just print each plan so I can pick 10+ cases that are cheap
enough to build and varied enough to matter.
"""
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
import aoe2mod.api as A
import os

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"

CASES = [
    ("archer_atk", {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'displayed_attack', 'delta': 2}),
    ("militia_hp", {'intent': 'unit.stat', 'unit': '民兵', 'stat': 'hit_points', 'delta': 10}),
    ("archer_speed", {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'movement_speed', 'delta': 1}),
    ("archer_cost_wood", {'intent': 'unit.cost', 'unit': '步弓手', 'resource': 'wood', 'delta': -5}),
    ("archer_armour", {'intent': 'unit.attack_class', 'unit': '步弓手', 'class_id': 4, 'kind': 'armour', 'delta': 1}),
    ("loom_time", {'intent': 'tech.research_time', 'tech': '织布机', 'delta': -10}),
    ("loom_cost", {'intent': 'tech.cost', 'tech': '织布机', 'resource': 'food', 'delta': -10}),
    ("loom_effect", {'intent': 'tech.effect', 'tech': '织布机', 'command': 0, 'delta': 5}),
    ("archer_grant", {'intent': 'unit.availability', 'unit': '步弓手', 'civ': '阿兹特克', 'action': 'grant'}),
    ("archer_sprite_copy", {'intent': 'unit.sprite', 'unit': '步弓手', 'donor': '长弓兵', 'mode': 'copy'}),
    ("archer_sprite_rename", {'intent': 'unit.sprite', 'unit': '步弓手', 'donor': '长弓兵', 'mode': 'rename'}),
]

tk = A.Toolkit(ROOT)
for tag, it in CASES:
    print("=" * 78)
    print(tag, json.dumps(it, ensure_ascii=False))
    try:
        p = tk.plan(it)
    except Exception as e:
        print("  RAISED %s: %s" % (type(e).__name__, e))
        continue
    for k in sorted(p):
        v = p[k]
        s = json.dumps(v, ensure_ascii=False, default=str)
        if len(s) > 220:
            s = s[:220] + "...<%d>" % len(s)
        print("  %-22s %s" % (k, s))
