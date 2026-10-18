# -*- coding: utf-8 -*-
"""CLAIM 5: does the build manifest carry verification.proven / .not_proven?

Builds one data mod and one sprite mod into fresh dirs, then walks the WHOLE
manifest (nested) looking for the two keys and quotes them.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, r"D:\Software\AI\帝国项目")
import aoe2mod.api as A

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s5")

CASES = [
    ("dat_archer_atk", {'intent': 'unit.stat', 'unit': '步弓手',
                        'stat': 'displayed_attack', 'delta': 2}),
    ("sprite_copy", {'intent': 'unit.sprite', 'unit': '步弓手',
                     'donor': '长弓兵', 'mode': 'copy'}),
    ("sprite_rename", {'intent': 'unit.sprite', 'unit': '步弓手',
                       'donor': '长弓兵', 'mode': 'rename'}),
]


def find_keys(obj, want, path="man"):
    """Every (path, value) where a dict key equals one of `want`."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = "%s.%s" % (path, k)
            if k in want:
                out.append((p, v))
            out.extend(find_keys(v, want, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5]):
            out.extend(find_keys(v, want, "%s[%d]" % (path, i)))
    return out


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    tk = A.Toolkit(ROOT)
    report = {}
    for tag, it in CASES:
        out = os.path.join(WORK, tag)
        print("=" * 92)
        print(tag, json.dumps(it, ensure_ascii=False))
        try:
            man = tk.build(it, out, title=tag, author="kv", description="claim5")
        except Exception as e:
            print("  BUILD RAISED %s: %s" % (type(e).__name__, e))
            report[tag] = {"raised": str(e)}
            continue
        print("  manifest top-level keys:", sorted(man))
        ver = man.get("verification")
        print("  man['verification'] present :", ver is not None)
        if isinstance(ver, dict):
            print("  man['verification'] keys    :", sorted(ver))
        hits = find_keys(man, {"proven", "not_proven"})
        print("  proven/not_proven anywhere  :", [(p, type(v).__name__) for p, v in hits])
        for p, v in hits:
            print("  --- %s ---" % p)
            print("     ", json.dumps(v, ensure_ascii=False, indent=1)[:2000])
        report[tag] = {"top_keys": sorted(man),
                       "verification": ver,
                       "found": [p for p, _ in hits]}
        json.dump(man, open(os.path.join(WORK, tag + "_manifest.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1,
                  default=str)
    json.dump(report, open(os.path.join(WORK, "_s5.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
