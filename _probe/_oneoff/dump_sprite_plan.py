"""What the reference says "让弓兵的样子换成长弓兵" should rewrite.

The Rust build rewrites a frozen villager->sheep map and ignores the sentence.
Before replacing that with a real decision I need the reference answer: how many
files, and which ones. Anything else is guessing with a running server.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from aoe2mod.ui.server import App


def show(sentence):
    app = App()
    got = app.parse(sentence, pins=pins)
    clause = (got.get("clauses") or [{}])[0]
    plan = ((clause.get("preview") or {}).get("plan")) or {}
    print("=" * 70)
    print(sentence)
    print("  intent : %s" % json.dumps((got.get("intents") or [{}])[0], ensure_ascii=False))
    for k in ("shape", "sprite_mode", "target_id", "donor_id", "edit_count",
              "file_count", "records", "editable", "changes_dat", "dat_is_carrier",
              "mod_contains_dat", "description", "reason"):
        if k in plan:
            print("  %-16s %s" % (k, json.dumps(plan[k], ensure_ascii=False)[:300]))
    if plan.get("target_stems") or plan.get("donor_stems"):
        print("  target_stems %s" % plan.get("target_stems"))
        print("  donor_stems  %s" % plan.get("donor_stems"))
    for w in plan.get("warnings") or ():
        print("  warn: %s" % w)
    for n in clause.get("notes") or ():
        print("  note: %s" % n)


MODE = os.environ.get("SPRITE_MODE") or ""
def show2(sentence):
    app = App()
    pins = {"mode": MODE} if MODE else {}
    got = app.parse(sentence, pins=pins)
    clause = (got.get("clauses") or [{}])[0]
    plan = ((clause.get("preview") or {}).get("plan")) or {}
    print("=" * 70)
    print("%s   [mode=%s]" % (sentence, plan.get("sprite_mode")))
    for k in ("shape", "sprite_mode", "edit_count", "file_count", "records", "editable",
              "changes_dat", "mod_contains_dat", "description", "reason", "retarget",
              "target_stems", "donor_stems", "target_count"):
        if k in plan:
            print("  %-16s %s" % (k, json.dumps(plan[k], ensure_ascii=False)[:400]))
    for w in plan.get("warnings") or ():
        print("  warn: %s" % w)

for s in sys.argv[1:] or ["让弓兵的样子换成长弓兵"]:
    show2(s)
