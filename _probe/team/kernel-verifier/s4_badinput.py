# -*- coding: utf-8 -*-
"""CLAIM 4: bad input is refused readably, and refusals write nothing.

For each malformed/impossible intent:
  * does plan() refuse?  with what message?
  * does build() refuse?  with what message?
  * do the two agree?
  * did any files appear on disk?

Contract under test (from the task): a reference that cannot be RESOLVED must
raise; a reference that resolves to a NO-OP must return a dict saying so.
"""
import json
import os
import shutil
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
import aoe2mod.api as A
# The refusal type is NOT re-exported by aoe2mod.api (its __all__ is
# ["Toolkit", "open_toolkit"]), so a caller must reach into the compiler module
# to catch it.  Noted in the report as a minor API-surface defect.
from aoe2mod.intent.compiler import IntentError

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s4")

CASES = [
    ("nonexistent_unit_name",
     {'intent': 'unit.stat', 'unit': '不存在的单位XYZ', 'stat': 'hit_points', 'delta': 1}),
    ("nonexistent_unit_id",
     {'intent': 'unit.stat', 'unit': 999999, 'stat': 'hit_points', 'delta': 1}),
    ("nonexistent_tech_name",
     {'intent': 'tech.research_time', 'tech': '不存在的科技XYZ', 'delta': -1}),
    ("unknown_intent_name",
     {'intent': 'unit.bogus', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 1}),
    ("missing_required_unit",
     {'intent': 'unit.stat', 'stat': 'hit_points', 'delta': 1}),
    ("missing_delta_and_value",
     {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points'}),
    ("both_delta_and_value",
     {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points',
      'delta': 1, 'value': 5}),
    ("unknown_stat",
     {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'armour', 'delta': 1}),
    ("overflow_negative_delta",
     {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': -100000}),
    ("overflow_value",
     {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'value': 40000}),
    ("unknown_civ_scope",
     {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 1,
      'civs': ['NOPE']}),
    ("unknown_civ_availability",
     {'intent': 'unit.availability', 'unit': '步弓手', 'civ': 'NOPE', 'action': 'grant'}),
    ("unknown_resource",
     {'intent': 'tech.cost', 'tech': '织布机', 'resource': 'faith', 'delta': -1}),
    ("stat_unit_does_not_store",
     {'intent': 'unit.stat', 'unit': '兵营', 'stat': 'displayed_attack', 'delta': 1}),
    ("unknown_donor",
     {'intent': 'unit.sprite', 'unit': '步弓手', 'donor': '不存在兵种XYZ', 'mode': 'copy'}),
    ("donor_equals_target",
     {'intent': 'unit.sprite', 'unit': '步弓手', 'donor': '步弓手', 'mode': 'copy'}),
    ("unknown_effect_command",
     {'intent': 'tech.effect', 'tech': '织布机', 'command': 99, 'delta': 1}),
    ("picture_missing",
     {'intent': 'unit.art', 'unit': '步弓手',
      'picture': r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\nope.png"}),
    ("not_a_dict", "unit.stat 步弓手"),
    ("empty_dict", {}),
    ("delta_zero_noop",
     {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 0}),
    ("grant_already_held",
     {'intent': 'unit.availability', 'unit': '步弓手', 'civ': 'AZTECS', 'action': 'grant'}),
    ("tech_cost_absent_resource",
     {'intent': 'tech.cost', 'tech': '织布机', 'resource': 'food', 'delta': -10}),
]


def files_under(d):
    out = []
    for root, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f)
            out.append((os.path.relpath(p, d).replace("\\", "/"), os.path.getsize(p)))
    return sorted(out)


def call(fn, *a, **kw):
    try:
        return {"ok": True, "value": fn(*a, **kw)}
    except IntentError as e:                 # the documented refusal type
        return {"ok": False, "type": "IntentError", "msg": str(e)}
    except Exception as e:
        return {"ok": False, "type": type(e).__name__, "msg": str(e),
                "tb": traceback.format_exc().splitlines()[-3:]}


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    tk = A.Toolkit(ROOT)
    rows = []
    for tag, it in CASES:
        out = os.path.join(WORK, tag)
        print("=" * 92)
        print(tag, json.dumps(it, ensure_ascii=False) if not isinstance(it, str) else it)
        p = call(tk.plan, it)
        b = call(tk.build, it, out, title=tag, author="kv", description="claim4")
        left = files_under(out) if os.path.isdir(out) else []
        row = {"tag": tag, "intent": it,
               "plan_ok": p["ok"], "build_ok": b["ok"],
               "plan_type": p.get("type"), "build_type": b.get("type"),
               "plan_msg": p.get("msg"), "build_msg": b.get("msg"),
               "leftover_files": left}
        if p["ok"]:
            pv = p["value"] or {}
            row["plan_says"] = {k: pv.get(k) for k in
                                ("description", "editable", "edit_count", "reason",
                                 "file_count")
                                if k in pv}
        if b["ok"]:
            bv = b["value"] or {}
            row["build_says"] = {k: bv.get(k) for k in
                                 ("resolved", "edit_count", "dat_file_bytes",
                                  "files", "mod_dir") if k in bv}
        rows.append(row)
        print("  plan  :", "OK " + json.dumps(row.get("plan_says"), ensure_ascii=False)
              if p["ok"] else "RAISE [%s] %s" % (p.get("type"), p.get("msg")))
        print("  build :", "OK " + json.dumps(row.get("build_says"), ensure_ascii=False)
              if b["ok"] else "RAISE [%s] %s" % (b.get("type"), b.get("msg")))
        if left:
            print("  FILES LEFT ON DISK:", left)
        # did they say the same thing?
        if not p["ok"] and not b["ok"]:
            same = (p.get("msg") or "").strip() == (b.get("msg") or "").strip()
            print("  messages identical        :", same)
            if not same:
                print("    plan :", p.get("msg"))
                print("    build:", b.get("msg"))
        if p["ok"] and not b["ok"]:
            print("  *** PLAN PROMISED, BUILD REFUSED ***")
        if not p["ok"] and b["ok"]:
            print("  *** PLAN REFUSED, BUILD WROTE ***")
    json.dump(rows, open(os.path.join(WORK, "_s4.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
