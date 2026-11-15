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
    # The upgrade corpus: ten cases, each with base/mod/new copies of the 93 MB
    # inflated .dat -- ~335 MB on disk and 125 s to build.  _out/ is ignored, so
    # on a fresh clone or a restored workspace it is simply absent, and
    # test_upgrade_guard.py exits 2 with "SKIP no fixtures", which this runner
    # would then record as a failure of the suite rather than of the setup.
    ("_probe\\make_upgrade_fixtures.py",
     "_out\\_upgrade_fixtures\\mod_touches_a\\expect.json"),
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
    # ---- five suites that existed on disk but were named by NO runner --------
    # These started the shipped shell, or walked the 93 MB .dat twice, which is
    # why they were left out of run_suites.py -- and then out of every runner.
    # `probe_suite_registry.py` reported ten orphans on 2026-11-01; five are fast
    # and were registered there, these five belong here.
    #
    # `test_dat_baseline_reverse` is the only one that proves the baseline CHECKER
    # can go red at all: a checker that cannot fail has never been tested.
    ("_probe\\test_dat_baseline_reverse.py", "REVERSE OK"),
    # The double-clicked release, measured as a product: parses, previews, builds,
    # installs, and answers the icon route.  Every other suite tests the checkout;
    # this one tests what the player runs.
    ("_probe\\test_e2e_shipped.py", "SHIPPED E2E: ALL PASSED"),
    ("_probe\\test_pages_shipped.py", "PAGE GATE: ALL PASSED"),
    # The icon route against the decoder, pixel for pixel, at three sizes.  It was
    # red for a month for two reasons that were both the probe's own: it read
    # `max=` while the route reads `size=`, and it treated a unit id as an icon id.
    ("_probe\\test_icon_parity.py", "pixel-identical"),
    # Rebuild round-trip against a COPY of the profile.  It used to build the
    # moment the socket answered, seconds before the 93 MB parse finished, and
    # reported the engine's honest refusal as a product defect.
    ("_probe\\test_rebuild.py", "REBUILD: ALL PASSED"),
    # ---- the upgrade engine, which had no runner at all ----------------------
    # Both of these sat on disk, green, named by NOTHING from the day they were
    # written (2026-11-09, found by probe_suite_registry.py).  They belong here
    # rather than in run_suites.py for the honest reason: 487 s and 111 s, since
    # each one inflates several 93 MB streams.
    #
    # test_upgrade is the only proof that an author's edits SURVIVE an official
    # patch -- ten cases, one per way the two sides can disagree (both edited the
    # same field, official added a unit, the mod added one, the mod removed one, a
    # tech field, a tech whole-record, byte-identical, cross-generation).  Without
    # it "一键更新" was a button with no gate behind it.
    ("_probe\\test_upgrade.py",
     "UPGRADE: THE MOD'S EDITS SURVIVED THE PATCH, EVERY CASE"),
    # The other half: every refusal is explained, and every length difference is
    # judged rather than guessed.  The two suites disagree about what "done" means
    # on purpose -- one says the edits came across, the other says nothing was
    # written silently when they could not be.
    ("_probe\\test_upgrade_guard.py",
     "GUARD: EVERY REFUSAL IS EXPLAINED, EVERY LENGTH IS JUDGED"),
    # ---- two probes that only ever ran by hand -------------------------------
    # Written 2026-11-11 out of one user sentence, 「我根本用不明白你这个工具」,
    # and then named by no runner -- probe_suite_registry.py found them on
    # 2026-11-12 as the last two orphans in the tree.  Both drive the SHIPPED
    # exe through Playwright (start the bundle, wait for ready, open a record),
    # which is tens of seconds and a port apiece; that is why they belong here
    # and not in run_suites.py.
    #
    # test_first_fold measures geometry: the first editable input must be above
    # the panel's bottom edge at 1264x821.  It is the regression guard for the
    # 271 px of record-level chrome that once pushed every field below y=1029.
    ("_probe\\test_first_fold.py",
     "FIRST FOLD PROBE: THE FIRST EDITABLE ROW IS ON SCREEN WHEN THE EDITOR OPENS"),
    # test_soft_edit measures the shared-column contract: a soft column takes a
    # write, warns that the value is shared, and no row degrades to a dead
    # label.  It used to print its verdict and exit 0 either way -- fixed
    # 2026-11-12, because a runner reading the exit code would have called a
    # red probe OK.
    ("_probe\\test_soft_edit.py",
     "SOFT EDIT PROBE: ALL GREEN"),
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
