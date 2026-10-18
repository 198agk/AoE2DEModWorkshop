# -*- coding: utf-8 -*-
"""CLAIM 3 final: plan description/edit_count/changes_dat vs build's own report.

Also adds a GRANT that really changes something, so the availability strategy is
represented by a successful build and not only by a refusal.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, r"D:\Software\AI\帝国项目")
import aoe2mod.api as A
from aoe2mod.intent.compiler import IntentError

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s7")

EXTRA = [
    ("grant_longbow_to_aztecs",
     {'intent': 'unit.availability', 'unit': '长弓兵', 'civ': 'AZTECS', 'action': 'grant'}),
    ("revoke_archer_britons",
     {'intent': 'unit.availability', 'unit': '步弓手', 'civ': 'BRITONS', 'action': 'revoke'}),
]


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    tk = A.Toolkit(ROOT)

    print("=== plan(description) vs build(resolved) on the 13 s3 cases ===")
    rows = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "scratch", "s3", "_all.json"), encoding="utf-8"))
    agree = 0
    for r in rows:
        p = r.get("plan") or {}
        m = r.get("manifest") or {}
        pd, bd = p.get("description"), m.get("resolved")
        pe, be = p.get("edit_count"), m.get("edit_count")
        pc, bc = p.get("changes_dat"), m.get("changes_dat")
        same_desc = (pd == bd) if (pd and bd) else None
        if same_desc:
            agree += 1
        print("  %-20s desc_same=%-5s edits %s/%s dat %s/%s"
              % (r["tag"], same_desc, pe, be, pc, bc))
        if same_desc is False:
            print("      plan :", pd)
            print("      build:", bd)
    print("  descriptions identical: %d/%d" % (agree, len(rows)))

    print()
    print("=== availability builds that really change something ===")
    for tag, it in EXTRA:
        base = os.path.join(WORK, tag)
        try:
            p = tk.plan(it)
            print("  --", tag)
            print("     plan : editable=%r edit_count=%r changes_dat=%r dat_is_carrier=%r civ_count=%r"
                  % (p.get("editable"), p.get("edit_count"), p.get("changes_dat"),
                     p.get("dat_is_carrier"), p.get("civ_count")))
            print("     plan description:", p.get("description"))
        except IntentError as e:
            print("  --", tag, "PLAN RAISED:", e)
            continue
        try:
            man = tk.build(it, base, title=tag, author="kv")
        except IntentError as e:
            print("     BUILD RAISED:", e)
            continue
        ver = man.get("verification") or {}
        print("     build: edit_count=%r changes_dat=%r dat_is_carrier=%r mod_contains_dat=%r"
              % (man.get("edit_count"), man.get("changes_dat"),
                 man.get("dat_is_carrier"), man.get("mod_contains_dat")))
        print("     build resolved:", man.get("resolved"))
        print("     files: %d ->"
              % len(man.get("files") or []),
              [f["rel"] for f in man.get("files") or []])
        print("     ver.ok:", ver.get("ok"),
              " dat_half:", json.dumps(man.get("dat_half") or {}, ensure_ascii=False)[:300])
        print("     proven:")
        for s in ver.get("proven") or []:
            print("       -", s)
        print("     not_proven:")
        for s in ver.get("not_proven") or []:
            print("       -", s)
        json.dump(man, open(os.path.join(WORK, tag + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
