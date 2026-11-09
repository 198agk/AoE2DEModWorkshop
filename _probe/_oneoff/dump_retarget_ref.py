"""Reference numbers for the sprite retarget, straight from the Python model.

The Rust writer has to reproduce `retarget.plan`'s decision, so this prints the
decision itself: which stems map to which, how many records match, and the
unmapped animations that keep the shipped art.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..")))

from aoe2mod.ui import server as S

GAME = r"d:\games\steam\steamapps\common\AoE2DE"

app = S.App(game_root=GAME)
for text in [
    "让弓兵的样子换成长弓兵",
    "让村民的样子换成绵羊",
    "让民兵的样子换成剑士",
    "让骑士的样子换成游侠",
]:
    got = app.parse(text)
    cl = (got.get("clauses") or [{}])[0]
    prev = cl.get("preview") or {}
    plan = prev.get("plan") or {}
    print("=" * 70)
    print(text)
    print("  intent  :", json.dumps((got.get("intents") or [{}])[0], ensure_ascii=False)[:200])
    print("  desc    :", plan.get("description"))
    print("  edit    :", plan.get("edit_count"), " target_names", plan.get("target_names"),
          " donor_names", plan.get("donor_names"), " civ_count", plan.get("civ_count"))
    print("  stems   :", json.dumps(plan.get("target_stems"), ensure_ascii=False),
          "->", json.dumps(plan.get("donor_stems"), ensure_ascii=False))
    print("  unmapped:", json.dumps(plan.get("unmapped"), ensure_ascii=False)[:300])
