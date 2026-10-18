# -*- coding: utf-8 -*-
"""Batch 6: the two registered baselines batch4 never reached (b03 timed out).

  b04 -- _probe/test_smoke5_design.py   : a REGISTERED suite whose artifact is absent
  b05 -- _probe/test_test_validity.py   : the meta-pin on the validity tool

Usage: python batch6.py
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
    ("b04_registered_smoke5_design",
     "_probe/test_smoke5_design.py",
     "a REGISTERED suite whose artifact (_probe/out_smoke5) does not exist "
     "on this machine -- does it go green while asserting nothing?"),
    ("b05_registered_test_validity",
     "_probe/test_test_validity.py",
     "the meta-pin on the test-validity tool, REGISTERED -- is its "
     "judgement actually asserted on hand-built logs?"),
]


def run_one(label, suite, why):
    root = mutate.fresh(os.path.join(OUT, "run_" + label))
    try:
        code, out = mutate.run(root, suite)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    with open(os.path.join(OUT, label + ".log"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("SUITE: %s\nWHY: %s\n\n%s" % (suite, why, out))
    lines = [x.rstrip() for x in out.strip().splitlines() if x.strip()]
    fails = [ln for ln in lines if "FAIL" in ln or "PROBLEM" in ln]
    rec = {"label": label, "suite": suite, "exit": code,
           "fail_lines": len(fails), "tail": lines[-3:], "why": why}
    print(json.dumps(rec, ensure_ascii=False))
    sys.stdout.flush()
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    recs = [run_one(*m) for m in MUTATIONS]
    with open(os.path.join(OUT, "batch6.json"), "w", encoding="utf-8") as fh:
        json.dump(recs, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
