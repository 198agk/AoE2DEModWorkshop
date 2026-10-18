# -*- coding: utf-8 -*-
"""Second mutation batch: intents not covered by batch 1 (unit.stat, tech.*,
carrier flags) plus a CONTROL that should be caught.

Usage: python batch2.py [label ...]
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mutate  # noqa: E402

OUT = os.path.join(HERE, "mutations")

MUTATIONS = [
    ("m11_node_status_claims_all",
     "aoe2mod/tests/test_availability_e2e.py",
     "aoe2mod/game/civtechtrees.py",
     "    if not found:\n        return None",
     '    if not found:\n        return "ResearchedCompleted"',
     "a civ that does NOT have a node now reports that it does"),

    ("m12_int_delta_dropped",
     "_probe/test_declared_resources.py",
     "aoe2mod/intent/compiler.py",
     '    new = (before + amount) if op == "delta" else amount',
     "    new = amount",
     "every integer stat edit becomes an absolute write, silently ignoring "
     "'delta' -- the whole point of unit.stat/tech.research_time deltas"),

    ("m13_dat_identical_always_true",
     "_probe/test_dat_carrier.py",
     "aoe2mod/mod/emitter.py",
     '        "dat_is_carrier": dat_carrier,',
     '        "dat_is_carrier": True,\n'
     '        "dat_identical_to_base": True,',
     "the manifest claims the shipped .dat is byte-identical even when it is "
     "not (a mod that says it changed nothing)"),

    ("m14_effect_edit_unrecorded",
     "_probe/test_dat_half_count.py",
     "aoe2mod/intent/datgrant.py",
     '    report["edits"].append({"what": "effect+tech",',
     '    _ = ({"what": "effect+tech",',
     "the recipe stops recording the effect+tech edit it made (CONTROL: the "
     "declared-count contract should notice)"),

    ("m15_control_docstring_only",
     "_probe/test_mechanism_gate.py",
     "aoe2mod/game/civtechtrees.py",
     "this civ gives ``node_id`` IN THE GIVEN SPACE, or ``None``.",
     "this civ gives ``node_id`` IN THE GIVEN ID SPACE, or ``None``.",
     "CONTROL: a docstring-only change must NOT break the suite.  If this "
     "'fails', the harness is reporting on the patch rather than the code."),
]


def run_one(label, suite, target, old, new, why):
    root = mutate.fresh(os.path.join(OUT, "run_" + label))
    try:
        if target != "-":
            mutate.patch(root, target, old, new)
        code, out = mutate.run(root, suite)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    log = os.path.join(OUT, label + ".log")
    with open(log, "w", encoding="utf-8", newline="") as fh:
        fh.write("SUITE: %s\nMUTATION: %s\nOLD: %r\nNEW: %r\nWHY: %s\n\n%s"
                 % (suite, target, old, new, why, out))
    lines = [x.rstrip() for x in out.strip().splitlines() if x.strip()]
    fails = [ln for ln in lines if "FAIL" in ln]
    rec = {"label": label, "suite": suite, "mutation": target,
           "exit": code, "fail_lines": len(fails),
           "tail": lines[-2:], "why": why}
    print(json.dumps(rec, ensure_ascii=False))
    sys.stdout.flush()
    return rec


def main():
    want = set(sys.argv[1:])
    os.makedirs(OUT, exist_ok=True)
    recs = []
    for m in MUTATIONS:
        if want and m[0] not in want:
            continue
        recs.append(run_one(*m))
    with open(os.path.join(OUT, "batch2.json"), "w", encoding="utf-8") as fh:
        json.dump(recs, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
