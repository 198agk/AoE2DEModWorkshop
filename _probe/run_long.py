"""Run the long regressions in one pass and print one line each.

These take ~20 minutes combined (test_full_sweep relocates the 85 MB tech
section once per tech.effect case, ~50 s each), so they are deliberately kept
out of run_suites.py.  Run this in the background.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

SUITES = [
    ("aoe2mod\\tests\\test_roundtrip.py", "BYTE-EXACT"),
    ("_probe\\sweep_tech_effect.py", "CLEAN"),
    ("_probe\\test_facade_contract.py", "8 / 8"),
    ("_probe\\datparse\\verify_artifact.py", "VALID"),
    ("_probe\\verify_tech_cost_artifact.py", "VALID"),
    ("_probe\\verify_agevariant_artifact.py", "VALID"),
    ("_probe\\test_full_sweep.py", "AGREE"),
]

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"

fails = []
for rel, want in SUITES:
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        print("%-46s MISSING" % os.path.basename(rel))
        fails.append(rel)
        continue
    r = subprocess.run([PY, path], cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = r.stdout.decode("utf-8", "replace").strip().splitlines()
    tail = out[-1].strip() if out else ""
    hit = want.lower() in r.stdout.decode("utf-8", "replace").lower()
    print("%-46s exit=%d %s %s"
          % (os.path.basename(rel), r.returncode, "OK " if hit else "?? ", tail))
    if r.returncode != 0 or not hit:
        fails.append(rel)

print()
if fails:
    print("LONG SUITES: FAILED -> %s" % fails)
    sys.exit(1)
print("LONG SUITES: ALL PASSED")
