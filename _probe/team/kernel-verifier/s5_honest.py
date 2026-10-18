# -*- coding: utf-8 -*-
"""CLAIM 5: does every build manifest carry verification.proven / .not_proven?

Checked across all four strategies plus the bundle path, so the answer is not
one lucky build.  Quotes each list verbatim.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, r"D:\Software\AI\帝国项目")
import aoe2mod.api as A
from aoe2mod.intent.compiler import IntentError

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s5")

CASES = [
    ("dat_stat", {'intent': 'unit.stat', 'unit': '步弓手',
                  'stat': 'displayed_attack', 'delta': 2}),
    ("dat_tech", {'intent': 'tech.research_time', 'tech': '织布机', 'delta': -1}),
    ("json_avail", {'intent': 'unit.availability', 'unit': '长弓兵',
                    'civ': 'AZTECS', 'action': 'grant'}),
    ("sprite_copy", {'intent': 'unit.sprite', 'unit': '步弓手',
                     'donor': '长弓兵', 'mode': 'copy'}),
    ("sprite_rename", {'intent': 'unit.sprite', 'unit': '步弓手',
                       'donor': '长弓兵', 'mode': 'rename'}),
]


def dump(tag, ver):
    print("  -- %s" % tag)
    if not isinstance(ver, dict):
        print("     verification is %r" % (ver,))
        return
    print("     keys: %s" % sorted(ver))
    for k in ("proven", "not_proven"):
        v = ver.get(k)
        if v is None:
            print("     %s: *** ABSENT ***" % k)
        elif not isinstance(v, list) or not v:
            print("     %s: *** EMPTY / not a list: %r ***" % (k, v))
        else:
            print("     %s: %d entry(ies)" % (k, len(v)))
            for s in v:
                print("        - %s" % s)


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    tk = A.Toolkit(ROOT)

    print("=== single-intent builds ===")
    for tag, it in CASES:
        out = os.path.join(WORK, tag)
        try:
            man = tk.build(it, out, title=tag, author="kernel-verifier")
        except IntentError as e:
            print("  -- %s BUILD RAISED: %s" % (tag, e))
            continue
        dump(tag, man.get("verification"))
        print("     manifest-level keys mentioning proven: %s"
              % [k for k in man if "proven" in k])
        print()

    print("=== bundle builds ===")
    bundles = [
        ("bundle_dat_only", [
            {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 5},
            {'intent': 'unit.stat', 'unit': '民兵', 'stat': 'hit_points', 'delta': 5}]),
        ("bundle_dat_plus_json", [
            {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 5},
            {'intent': 'unit.availability', 'unit': '长弓兵', 'civ': 'AZTECS',
             'action': 'grant'}]),
        ("bundle_json_only", [
            {'intent': 'unit.availability', 'unit': '长弓兵', 'civ': 'AZTECS',
             'action': 'grant'},
            {'intent': 'unit.availability', 'unit': '长弓兵', 'civ': 'MAYANS',
             'action': 'grant'}]),
        ("bundle_sprite", [
            {'intent': 'unit.sprite', 'unit': '步弓手', 'donor': '长弓兵',
             'mode': 'copy'}]),
    ]
    for tag, intents in bundles:
        out = os.path.join(WORK, tag)
        try:
            man = tk.build_bundle(intents, out, title=tag, author="kernel-verifier")
        except IntentError as e:
            print("  -- %s BUILD RAISED: %s" % (tag, e))
            continue
        print("  -- %s" % tag)
        print("     manifest keys: %s" % sorted(man))
        if "verification" not in man:
            print("     verification: *** ABSENT ENTIRELY ***")
        dump(tag, man.get("verification"))
        for extra in ("sprite_verification", "sprites", "per_civ"):
            if extra in man:
                v = man[extra]
                if isinstance(v, dict) and ("proven" in v or "not_proven" in v):
                    print("     (%s carries its own lists)" % extra)
                    dump(tag + "/" + extra, v)
        print()


if __name__ == "__main__":
    main()
