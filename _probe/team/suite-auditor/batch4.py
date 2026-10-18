# -*- coding: utf-8 -*-
"""Batch 4: (a) does the verify_surgical mutant also survive the *other*
caller, (b) what do the UNREGISTERED suites actually do on this machine,
(c) the SKIP-and-exit-0 suite demonstrated.

Usage: python batch4.py [label ...]
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
    # (label, suite, target, old, new, why)
    ("m21_verify_surgical_panel_wire",
     "_probe/test_panel_wire.py",
     "aoe2mod/game/buildpanel.py",
     '    ok = info["outside_is_untouched"]',
     "    ok = True",
     "the same tautology mutant, against the SECOND caller of "
     "verify_surgical -- does test_panel_wire notice what test_buildpanel "
     "did not?"),

    # ---- baseline runs (target "-" = no patch).  These answer "is the
    # unregistered coverage even real on this machine?"
    ("b01_unregistered_repaint",
     "_probe/test_repaint.py", "-", "-", "-",
     "the only end-to-end unit.art/repaint suite, NOT in run_suites.py"),
    ("b02_unregistered_retarget",
     "_probe/test_retarget.py", "-", "-", "-",
     "the retarget plan suite, NOT in run_suites.py"),
    ("b03_unregistered_plan_matches_build",
     "_probe/test_plan_matches_build.py", "-", "-", "-",
     "the plan/build agreement sweep, NOT in run_suites.py"),
    ("b04_registered_smoke5_design",
     "_probe/test_smoke5_design.py", "-", "-", "-",
     "a REGISTERED suite whose artifact is absent -- does it go green?"),
    ("b05_registered_test_validity",
     "_probe/test_test_validity.py", "-", "-", "-",
     "the meta-pin on the validity tool, REGISTERED"),
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
    fails = [ln for ln in lines if "FAIL" in ln or "PROBLEM" in ln]
    rec = {"label": label, "suite": suite, "mutation": target,
           "exit": code, "fail_lines": len(fails),
           "tail": lines[-3:], "why": why}
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
    with open(os.path.join(OUT, "batch4.json"), "w", encoding="utf-8") as fh:
        json.dump(recs, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
