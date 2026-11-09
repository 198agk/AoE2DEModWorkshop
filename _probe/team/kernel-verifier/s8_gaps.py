# -*- coding: utf-8 -*-
"""Last gaps: (1) does the delta=0 manifest SAY it is a no-op?
(2) where does a dat+json bundle keep its availability verdict?
(3) the exact wording of the in_place_patch absence."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
import aoe2mod.api as A

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"


def show(tag, man):
    print("  --", tag)
    print("     warnings        :", man.get("warnings"))
    print("     dat_identical_to_base:", man.get("dat_identical_to_base"))
    print("     dat_is_carrier  :", man.get("dat_is_carrier"))
    print("     changes_dat     :", man.get("changes_dat"))
    print("     edit_count      :", man.get("edit_count"))
    print("     top-level keys with 'proven':",
          [k for k in man if "proven" in k])


print("=== (1) the delta=0 no-op manifest ===")
p = os.path.join(HERE, "scratch", "s4b", "delta0")
if os.path.isdir(p):
    print("  files on disk:", sorted(os.listdir(p)))
    print("  info.json:", open(os.path.join(p, "info.json"), encoding="utf-8").read())

print()
print("=== (2) dat+json bundle: where is the availability verdict? ===")
man = None
for cand in ("bundle_dat_plus_json",):
    q = os.path.join(HERE, "scratch", "s5", cand)
    print("  dir exists:", os.path.isdir(q), q)
    if os.path.isdir(q):
        print("  files:", sorted(os.listdir(q)))

tk = A.Toolkit(ROOT)
intents = [{'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 5},
           {'intent': 'unit.availability', 'unit': '长弓兵', 'civ': 'AZTECS',
            'action': 'grant'}]
man = tk.build_bundle(intents, os.path.join(HERE, "scratch", "s5b", "mix"),
                      title="mix", author="kv", overwrite=True)
print("  verification keys :", sorted(man["verification"]))
print("  verification.proven present   :", "proven" in man["verification"])
print("  verification.not_proven present:", "not_proven" in man["verification"])
av = man.get("availability")
if isinstance(av, dict):
    print("  availability keys :", sorted(av))
    print("  availability.proven:", bool(av.get("proven")))
    print("  availability.not_proven:", bool(av.get("not_proven")))
    if "civs" in av:
        cv = av["civs"]
        if isinstance(cv, dict):
            cv = list(cv.items())
        else:
            cv = [("<list>", cv)]
        for civ, v in cv:
            if isinstance(v, dict):
                print("    %s keys: %s proven=%r not_proven=%r"
                      % (civ, sorted(v), bool(v.get("proven")), bool(v.get("not_proven"))))
            else:
                print("    %s -> %r" % (civ, v))
    aver = av.get("verification")
    if isinstance(aver, dict):
        print("  availability.verification keys:", sorted(aver))
        print("  availability.verification.has proven:", "proven" in aver,
              " not_proven:", "not_proven" in aver)
json.dump(man, open(os.path.join(HERE, "scratch", "s5b", "mix.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

print()
print("=== (3) in_place_patch plan() has no verification-shaped keys ===")
p1 = tk.plan({'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 1})
print("  unit.stat plan keys:", sorted(p1))
print("  has 'editable':", "editable" in p1, " has 'changes_dat':", "changes_dat" in p1)
p2 = tk.plan({'intent': 'tech.research_time', 'tech': '织布机', 'delta': -1})
print("  tech plan keys:", sorted(p2))
