"""Reference answer for a sprite rename, straight from the toolkit plan.

`mode` is not something the sentence says -- it is a key on the intent dict
(`aoe2mod/api.py:797 _reskin_mode` reads `r.raw["mode"]`), which is why passing it
through `pins` did nothing. So ask the toolkit for the plan directly, with the
same intent shape the page would send.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import aoe2mod.api as A

tk = A.open_toolkit()
tk._ensure()

for sentence_mode in ("copy", "rename"):
    for target, donor in ((4, 8), (1810, 594), (74, 8)):
        intent = {
            "intent": "unit.sprite",
            "unit": target,
            "donor": donor,
            "mode": sentence_mode,
        }
        plan = tk.plan(intent)
        print("=" * 72)
        print("mode=%s  target=%s donor=%s" % (sentence_mode, target, donor))
        for k in ("shape", "sprite_mode", "editable", "edit_count", "file_count",
                  "records", "changes_dat", "mod_contains_dat", "description",
                  "reason", "target_stems", "donor_stems", "target_count"):
            if k in plan:
                print("  %-16s %s" % (k, json.dumps(plan[k], ensure_ascii=False)[:260]))
        rt = plan.get("retarget")
        if rt:
            print("  retarget         %s" % json.dumps(rt, ensure_ascii=False)[:600])
        for w in plan.get("warnings") or ():
            print("  warn: %s" % w)
