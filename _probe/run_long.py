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

# Artifacts produced by a generator rather than checked in.  `.gitignore` excludes
# `_probe/out_*/`, so after a fresh clone -- and after this workspace was restored
# from session logs, which recovered sources but no binaries -- they are absent,
# and the suites that read them fail with a bare FileNotFoundError that says
# nothing about the real cause.  Regenerate them first, and say so.
PREPARE = [
    ("_probe\\datparse\\emit_mod.py",
     "_probe\\datparse\\out_modtest\\ArcherAttackPlus2_probe\\info.json"),
]

SUITES = [
    ("aoe2mod\\tests\\test_roundtrip.py", "BYTE-EXACT"),
    ("_probe\\sweep_tech_effect.py", "CLEAN"),
    ("_probe\\test_facade_contract.py", "8 / 8"),
    ("_probe\\datparse\\verify_artifact.py", "VALID"),
    ("_probe\\verify_tech_cost_artifact.py", "VALID"),
    ("_probe\\verify_agevariant_artifact.py", "VALID"),
    ("_probe\\test_full_sweep.py", "AGREE"),
    # plan/build cross-boundary sweep: relocates the 85 MB tech section once per
    # tech.effect case (~50 s each), so it lives here with the other ~20 min
    # suites rather than in the fast run_suites.py.
    ("_probe\\test_plan_matches_build.py", "AGREE ON EVERY CASE"),
]

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"

for gen, produced in PREPARE:
    if os.path.isfile(os.path.join(ROOT, produced)):
        continue
    path = os.path.join(ROOT, gen)
    if not os.path.isfile(path):
        print("%-46s NO GENERATOR" % os.path.basename(gen))
        continue
    print("%-46s regenerating %s" % (os.path.basename(gen), os.path.basename(produced)))
    r = subprocess.run([PY, path], cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0 or not os.path.isfile(os.path.join(ROOT, produced)):
        print("  generator FAILED (exit=%d): %s"
              % (r.returncode, r.stdout.decode("utf-8", "replace").strip()[-300:]))

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
