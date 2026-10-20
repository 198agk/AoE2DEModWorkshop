# -*- coding: utf-8 -*-
"""Why does the preview promise an edit the build then refuses as nonexistent?

`probe_player_refusals.py` found a real disagreement:

    步弓手对骑兵攻击加300   preview: 「步弓手 基础攻击·骑兵 +300」 editable=True
                            build:   IntentError: 步弓手 没有「基础攻击」这项可以改
                                     （这类单位没有存这一项）

Two possibilities, and they need opposite fixes:

  A. the PREVIEW is optimistic -- it counts a target the write path would drop,
     so the number it shows is not what the build does.  Then the preview is
     the liar, exactly like `tech.research_time delta 0` was.
  B. the WRITE path is dropping a target it should keep, and the "does not
     store one" reason is a misdiagnosis for a value that really is out of
     range.  Then a legal edit is impossible and the message sends the player
     looking for the wrong thing.

This prints both sides on the same intent so the answer is not a guess.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import aoe2mod.api as A
from aoe2mod.intent import compiler as C

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

CASES = [
    ("fits the byte", {"intent": "unit.attack_class", "unit": 4, "class_id": 12,
                       "kind": "attack", "delta": 2}),
    ("over the byte", {"intent": "unit.attack_class", "unit": 4, "class_id": 12,
                       "kind": "attack", "delta": 300}),
    ("class the unit lacks", {"intent": "unit.attack_class", "unit": 4,
                              "class_id": 12, "kind": "attack", "delta": 2,
                              "value": 5}),
]


def main():
    tk = A.open_toolkit(game_root=GAME)
    tk._ensure()
    for label, intent in CASES:
        print("=" * 70)
        print(label, intent)
        pl = tk.plan(intent)
        print("  plan.description :", pl.get("description"))
        print("  plan.editable    :", pl.get("editable"))
        print("  plan.edit_count  :", pl.get("edit_count"))
        print("  plan.civ_count   :", pl.get("civ_count"))
        print("  plan keys        :", sorted(pl.keys()))
        # the write path, on the same data
        try:
            man = tk.build(intent, os.path.join(os.environ.get("TEMP", "."),
                                                "dsh_attack_probe"),
                           title="probe", author="dsh", overwrite=True)
            print("  build            : ok, edits=%s" % man.get("edit_count"))
        except Exception as exc:                   # noqa: BLE001
            print("  build            : %s: %s" % (type(exc).__name__, exc))
    print()
    print("what the schema says about attack_class:")
    import json
    schema = json.load(open(os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))),
        "aoe2mod", "schema", "intents.json"), encoding="utf-8"))
    for it in schema["intents"]:
        if it["id"] == "unit.attack_class":
            print(json.dumps(it, ensure_ascii=False, indent=2)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
