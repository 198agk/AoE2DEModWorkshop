# -*- coding: utf-8 -*-
"""What does an availability BUILD actually emit, per action and per space?

`_probe/test_full_sweep.py` asserts, for every availability case, that
`plan["edit_count"] == 0` and `plan["mod_contains_dat"] is False` -- i.e. that
this intent never ships a `.dat`.  The schema disagrees: `unit.availability`
declares a `dat_half` for `grant` only, with `write_operations: 2`.

One of the two was stale.  The plan is a PROMISE about disk; the build is the
truth.  This probe builds all four cases into a scratch directory and lists what
lands, so the argument is about bytes rather than about belief.

★ Two questions that used to be conflated here, and conflating them produced
three false alarms in the first run of this probe:

    does a `.dat` FILE exist in the mod?   -> yes, for every availability mod
    did a `.dat` BYTE change?              -> only when the grant recipe ran

Any mod writing under `resources/_common/dat/` must carry
`empires2_x2_p1.dat` or the game fails to start (`mod/emitter.py`), so the file
is always present; when only JSON changed it is byte-identical to the base game
and the manifest calls it a CARRIER.  Comparing "file exists" against
`changes_dat` therefore blames the plan for the emitter's storage rule.

Cases (mirroring the sweep):
  unit.availability grant  / British / 41
  unit.availability revoke / Goths   / 41
  tech.availability grant  / Goths   / 3
  tech.availability revoke / British / 3
"""
import hashlib
import os
import shutil
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                            # noqa: E402
import aoe2mod.dat.parser as P                          # noqa: E402

OUT = os.path.join(ROOT, "_probe", "out_avail_build")
CASES = [("unit.availability", {"unit": 41, "civ": "British", "action": "grant"}),
         ("unit.availability", {"unit": 41, "civ": "Goths", "action": "revoke"}),
         ("tech.availability", {"tech": 3, "civ": "Goths", "action": "grant"}),
         ("tech.availability", {"tech": 3, "civ": "British", "action": "revoke"})]


def inflate(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    d = zlib.decompressobj(-15)
    return d.decompress(blob) + d.flush()


tk = A.open_toolkit()
base_raw, _how = P.load_dat(tk.dat_path)
base_sha = hashlib.sha256(base_raw).hexdigest()
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

bad = []
for i, (intent, fields) in enumerate(CASES):
    case = dict(fields)
    case["intent"] = intent
    label = "%s.%s" % (intent, fields["action"])
    plan = tk.plan(case)
    dest = os.path.join(OUT, "case%d" % i)
    man = tk.build(case, out_dir=dest, title="avail probe",
                   author="DSH probe", description="plan/build agreement probe")

    on_disk = []
    for dirpath, _dirs, files in os.walk(dest):
        for fn in files:
            fp = os.path.join(dirpath, fn)
            on_disk.append((os.path.relpath(fp, dest).replace(os.sep, "/"),
                            os.path.getsize(fp)))
    dat_rel = "resources/_common/dat/empires2_x2_p1.dat"
    has_dat = any(rel == dat_rel for rel, _ in on_disk)
    changed = bool(has_dat) and \
        hashlib.sha256(inflate(os.path.join(dest, dat_rel))).hexdigest() != base_sha

    print("=" * 74)
    print("%s   civ=%s" % (label, fields["civ"]))
    print("  plan : edit_count=%s changes_dat=%s mod_contains_dat=%s "
          "dat_is_carrier=%s"
          % (plan.get("edit_count"), plan.get("changes_dat"),
             plan.get("mod_contains_dat"), plan.get("dat_is_carrier")))
    print("  build: dat_half edits=%s  files=%d"
          % (len((man.get("dat_half") or {}).get("edits") or ()), len(on_disk)))
    for rel, size in sorted(on_disk):
        print("    %-62s %10d B" % (rel, size))
    print("  .dat FILE in mod : %s" % has_dat)
    print("  .dat BYTES changed : %s" % changed)

    # The plan is a promise; the build is the truth.  Where they disagree, the
    # plan is what has to change -- a user reading the preview is told what will
    # land on disk.
    if bool(plan.get("mod_contains_dat")) != has_dat:
        bad.append((label, "plan says mod_contains_dat=%s but a .dat file on "
                           "disk=%s" % (plan.get("mod_contains_dat"), has_dat)))
    n_edits = len((man.get("dat_half") or {}).get("edits") or ())
    if int(plan.get("edit_count") or 0) != n_edits:
        bad.append((label, "plan edit_count=%s vs the recipe's %d edit(s)"
                    % (plan.get("edit_count"), n_edits)))
    if bool(plan.get("changes_dat")) != changed:
        bad.append((label, "plan changes_dat=%s but a .dat BYTE changed=%s"
                    % (plan.get("changes_dat"), changed)))
    if bool(man.get("dat_is_carrier")) != (has_dat and not changed):
        bad.append((label, "manifest dat_is_carrier=%s but file=%s changed=%s"
                    % (man.get("dat_is_carrier"), has_dat, changed)))

print()
print("=" * 74)
print("plan/build disagreements: %d" % len(bad))
for label, why in bad:
    print("  BAD %-32s :: %s" % (label, why))
print("AVAILABILITY BUILD TRUTH: %s"
      % ("PLAN MATCHES DISK" if not bad else "PLAN CONTRADICTS DISK"))
sys.exit(1 if bad else 0)
