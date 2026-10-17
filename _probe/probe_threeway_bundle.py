"""A bundle mixing .dat edits with BOTH availability spaces.

The failure this guards against: `_apply_availability_bundle` and
`_availability_verification` are shared by both id spaces, so a `use_types` that
is dropped in one of them still produces a perfectly shaped answer -- one that
names the wrong entity.  A mixed bundle is the only way to reach all three
strategies in one mod.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
from aoe2mod.game import civtechtrees as CT

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FAILS = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           "" if not detail else " -- %s" % detail))
    if not ok:
        FAILS.append(label)


def main():
    tk = A.open_toolkit(GAME)
    tk._ensure()
    before = {c: len(CT.rows_of(t)) for c, t in tk._trees().items()}

    intents = [
        # a .dat edit
        {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
        # a unit-space row addition
        {"intent": "unit.availability", "unit": 41, "civ": "British",
         "action": "grant"},
        # a tech-space row addition -- same machinery, different namespace
        {"intent": "tech.availability", "tech": 3, "civ": "Goths",
         "action": "grant"},
    ]
    p = tk.plan_bundle(intents)
    print("descriptions: %s" % p["descriptions"])
    check(len(p["availability"]) == 2, "both availability halves are reported",
          str(len(p["availability"])))
    check([n["civ"] for n in p["availability"]] == ["BRITONS", "GOTHS"],
          "one note per civilization, in order",
          str([n["civ"] for n in p["availability"]]))
    check({n["space"] for n in p["availability"]} == {"Unit", "Tech"},
          "the two notes carry DIFFERENT spaces",
          str([n.get("space") for n in p["availability"]]))
    check(p["edit_count"] > 0, "the .dat half contributes edits",
          str(p["edit_count"]))
    # The preview must not have touched the cache, in either space.
    check(all(len(CT.rows_of(tk._trees()[c])) == before[c] for c in before),
          "the preview left every cached tree untouched")

    tmp = tempfile.mkdtemp(prefix="aoe2mod threeway ")
    try:
        out = os.path.join(tmp, "three way")
        man = tk.build_bundle(intents, out, title="Three way",
                              author="aoe2mod probe")
        print("manifest: dat=%s json=%s edit_count=%s"
              % (man.get("mod_contains_dat"), man.get("json_overrides"),
                 man.get("edit_count")))
        check(man["mod_contains_dat"] is True, "the mod carries a .dat")
        check(len(man["json_overrides"]) == 2,
              "and exactly two tree files", str(man["json_overrides"]))
        v = man["verification"]
        check(v["ok"] is True, "the bundle verifies", str(v.get("failures")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print("THREE-WAY BUNDLE: FAILED -> %s" % FAILS)
        return 1
    print("THREE-WAY BUNDLE: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
