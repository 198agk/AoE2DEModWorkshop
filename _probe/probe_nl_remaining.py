# -*- coding: utf-8 -*-
"""What do the five intents the screen cannot say yet need, exactly?

Prints, for each of the five, the smallest valid intent and what `plan()` says
about it -- the sentence the player will read.  Written before touching nl.py so
the wording the parser has to produce is known rather than guessed.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from aoe2mod import api as A

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)

CASES = [
    ("unit.attack_class", {"intent": "unit.attack_class", "unit": 4,
                           "kind": "attack", "class_id": 12, "delta": 2}),
    ("unit.attack_class armour", {"intent": "unit.attack_class", "unit": 4,
                                  "kind": "armour", "class_id": 0, "delta": 1}),
    ("tech.effect", {"intent": "tech.effect", "tech": 22, "command": 0, "delta": 5}),
    ("tech.availability", {"intent": "tech.availability", "tech": 22,
                           "civ": "Incas", "action": "grant"}),
    ("unit.sprite", {"intent": "unit.sprite", "unit": 83, "donor": 4}),
    ("unit.art", {"intent": "unit.art", "unit": 83,
                  "picture": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "_shots", "live_unit83.png")}),
]

for label, intent in CASES:
    print("===", label)
    print("   intent:", json.dumps(intent, ensure_ascii=False))
    try:
        pl = tk.plan(intent)
    except Exception as exc:
        print("   PLAN RAISED %s: %s" % (type(exc).__name__, exc))
        continue
    keep = {k: pl.get(k) for k in ("ok", "editable", "edit_count", "changes_dat",
                                   "description")}
    print("   ", json.dumps(keep, ensure_ascii=False))
    if pl.get("reason"):
        print("    reason:", pl["reason"])
    if pl.get("why"):
        print("    why:", pl["why"])

print()
print("=== the class table a sentence would have to name")
from aoe2mod.intent import compiler as C
tables = C.load_effect_tables()
zh = (tables.get("zh") or {}).get("classes") or {}
en = (tables.get("classes") or {}).get("classes") or {}
for k in sorted(zh, key=lambda x: int(x))[:8]:
    print("   %-4s %-10s %s" % (k, zh[k], en.get(k)))

print()
print("=== 织布机's three commands, as the player would pick one")
eff = tk.effects(22)
for row in eff["rows"]:
    print("   #%d %s %s %s" % (row["index"], row.get("type_label"),
                               row.get("attribute_label"), row.get("target_label")))
