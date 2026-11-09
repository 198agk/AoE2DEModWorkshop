# -*- coding: utf-8 -*-
"""Two loose ends.

(1) Find a unit record that genuinely CANNOT carry a stat, so claim 4's
    "a stat the unit type does not store" case is exercised for real.
(2) Does the delta=0 build TELL the caller it shipped a no-op?
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

tk = A.Toolkit(ROOT)

print("=== (1) hunt for a record that stores no attack field ===")
print("  tk.search('树') ->", json.dumps(tk.search("树", limit=6), ensure_ascii=False))
probe_ids = [406, 413, 1001, 1002, 1003, 1004, 1873, 1747, 2195]
for uid in probe_ids:
    try:
        d = tk.describe(uid)
    except IntentError as e:
        print("  id %-5s describe raised: %s" % (uid, e))
        continue
    try:
        p = tk.plan({'intent': 'unit.stat', 'unit': uid,
                     'stat': 'displayed_attack', 'delta': 1})
    except IntentError as e:
        print("  id %-5s %-14s plan RAISED: %s" % (uid, d["name"], e))
        continue
    print("  id %-5s %-14s plan edit_count=%-4s desc=%s"
          % (uid, d["name"], p.get("edit_count"), p.get("description")))

print()
print("=== (2) delta=0 manifest: does it warn about being a no-op? ===")
it = {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 0}
man = tk.build(it, os.path.join(HERE, "scratch", "s8", "zero"), title="z",
               author="kv", overwrite=True)
for k in ("warnings", "dat_identical_to_base", "dat_is_carrier", "changes_dat",
          "edit_count", "dat_sha256", "dat_raw_bytes"):
    print("  %-22s %r" % (k, man.get(k)))
print("  verification:", json.dumps({k: v for k, v in man["verification"].items()
                                    if k != "unclaimed_missing"},
                                   ensure_ascii=False)[:400])
print("  unclaimed_missing len:", len(man["verification"]["unclaimed_missing"]))
