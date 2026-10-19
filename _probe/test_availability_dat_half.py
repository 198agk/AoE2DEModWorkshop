# -*- coding: utf-8 -*-
"""A plan's claim about the `.dat` half must match what lands on disk.

`unit.availability` used to write no `.dat` byte at all, so the preview could
hard-code `edit_count=0` / `changes_dat=False`, and `_probe/test_full_sweep.py`
asserted exactly that.  Once the in-game-proven `datgrant` recipe was wired to
`grant`, those became false statements about a file the build really edits --
and because the sweep runs only in `run_long.py` (~2 h), the contradiction
survived every fast run.

Three DISTINCT questions live here and conflating them is what went wrong:

  changes_dat        did a `.dat` byte change?
  mod_contains_dat   does the mod folder carry `empires2_x2_p1.dat`?
  edit_count         how many `.dat` write operations were performed?

For an availability mod they answer differently: every JSON override lives under
`resources/_common/dat/`, and a mod that overrides that folder without the `.dat`
makes the game fail to start (`mod/emitter.py`), so the emitter ALWAYS carries a
`.dat` -- byte-identical to the base game unless the recipe ran.  So
`mod_contains_dat` is True for all four actions while `changes_dat` is True for
one.

This test answers each question against DISK rather than against another
declaration, so a plan that drifts is caught by bytes.
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
from aoe2mod.intent import compiler as C                # noqa: E402
import aoe2mod.dat.parser as P                          # noqa: E402

OUT = os.path.join(ROOT, "_probe", "out_avail_dat_half")
CASES = [("unit.availability", "grant", {"unit": 41, "civ": "British"}),
         ("unit.availability", "revoke", {"unit": 41, "civ": "Goths"}),
         ("tech.availability", "grant", {"tech": 3, "civ": "Goths"}),
         ("tech.availability", "revoke", {"tech": 3, "civ": "British"})]

fails = []


def check(label, ok, detail=""):
    print("  [%s] %-62s %s" % ("PASS" if ok else "FAIL", label, detail))
    if not ok:
        fails.append(label)


def inflate(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    d = zlib.decompressobj(-15)
    return d.decompress(blob) + d.flush()


print("=" * 78)
print("AVAILABILITY: DOES THE PLAN TELL THE TRUTH ABOUT THE `.dat` HALF?")
print("=" * 78)

tk = A.open_toolkit()
intents_schema, _bindings = C.load_schema()
base_raw, _how = P.load_dat(tk.dat_path)
base_sha = hashlib.sha256(base_raw).hexdigest()
print("base .dat: %d raw bytes" % len(base_raw))

if os.path.isdir(OUT):
    shutil.rmtree(OUT)

for intent, action, fields in CASES:
    case = dict(fields)
    case["intent"] = intent
    case["action"] = action
    label = "%s.%s" % (intent, action)
    print()
    print("-" * 78)
    print("%s  (%s)" % (label, fields["civ"]))

    plan = tk.plan(case)
    dest = os.path.join(OUT, "%s_%s" % (intent.split(".")[0], action))
    man = tk.build(case, out_dir=dest, title="dat half probe", author="DSH probe",
                   description="plan/disk agreement", overwrite=True)

    # --- what actually landed -------------------------------------------
    dat_rel = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")
    dat_abs = os.path.join(dest, dat_rel)
    on_disk_dat = os.path.isfile(dat_abs)
    if on_disk_dat:
        raw = inflate(dat_abs)
        disk_sha = hashlib.sha256(raw).hexdigest()
        dat_changed = disk_sha != base_sha
        delta = len(raw) - len(base_raw)
    else:
        dat_changed, delta = False, 0
    edits = man.get("dat_half") or {}
    n_edits = len(edits.get("edits") or ())

    check("%s: a .dat IS on disk" % label, on_disk_dat)
    check("%s: plan mod_contains_dat matches disk" % label,
          bool(plan.get("mod_contains_dat")) == on_disk_dat,
          "plan=%s disk=%s" % (plan.get("mod_contains_dat"), on_disk_dat))
    check("%s: plan changes_dat matches the bytes" % label,
          bool(plan.get("changes_dat")) == dat_changed,
          "plan=%s disk_changed=%s delta=%+d"
          % (plan.get("changes_dat"), dat_changed, delta))
    check("%s: plan edit_count matches the build's dat_half edits" % label,
          int(plan.get("edit_count") or 0) == n_edits,
          "plan=%s build=%d" % (plan.get("edit_count"), n_edits))
    check("%s: manifest dat_is_carrier agrees with the bytes" % label,
          bool(man.get("dat_is_carrier")) == (on_disk_dat and not dat_changed),
          "carrier=%s changed=%s" % (man.get("dat_is_carrier"), dat_changed))

    # The declaration is what the preview reads, so the schema must be the one
    # saying whether a `.dat` half exists -- not a hard-coded decision.
    dh = (intents_schema["intents"][intent]["compile"].get("dat_half") or {})
    declared = action in (dh.get("actions") or ())
    check("%s: plan changes_dat follows compile.dat_half.actions" % label,
          bool(plan.get("changes_dat")) == declared,
          "actions=%s" % (dh.get("actions") or []))
    if declared:
        _decl_n = int(((dh.get("write_operations_by_action") or {})
                       .get(action, dh.get("write_operations"))) or 0)
        check("%s: the declared write_operations equals the edits performed" % label,
              _decl_n == n_edits,
              "declared=%s performed=%d"
              % (_decl_n, n_edits))

    # Two DIFFERENT absences, and conflating them is how `tech.availability` came
    # to declare `mod_contains_dat: false` while every build shipped a `.dat`:
    #
    #   * the schema declares a `.dat` half but EXCLUDES this action
    #     -> the builder must say why it will not write one.  NO availability
    #     action is in this state any more: `unit.availability` excluded `revoke`
    #     until `dsh test v17` (2026-10-19) confirmed the disable recipe, and the
    #     branch is kept because the schema is allowed to refuse an action again
    #     (and because a refusal without a reason is the failure mode this file
    #     exists to catch);
    #   * the schema declares no `.dat` half AT ALL (tech.availability, both
    #     actions) -> there is nothing to refuse, and what must be true instead is
    #     that the `.dat` on disk is an unedited carrier.
    if declared is False and dh:
        check("%s: the refusal to write a .dat half carries a reason" % label,
              bool((man.get("dat_half") or {}).get("reason")),
              str((man.get("dat_half") or {}).get("reason"))[:60])
    elif not dh:
        check("%s: with no `.dat` half declared, the shipped .dat is a carrier" % label,
              bool(man.get("dat_is_carrier")) and not man.get("changes_dat"),
              "carrier=%s changes_dat=%s"
              % (man.get("dat_is_carrier"), man.get("changes_dat")))
        # ...and the declaration must not claim otherwise.  This is the exact
        # falsehood that was sitting in intents.json: "mod_contains_dat": false.
        check("%s: the schema does not claim the mod is free of a .dat" % label,
              bool((intents_schema["intents"][intent]["compile"]
                    .get("mod_contains_dat"))) == on_disk_dat,
              "schema=%s disk=%s"
              % (intents_schema["intents"][intent]["compile"].get("mod_contains_dat"),
                 on_disk_dat))

print()
print("=" * 78)
print("AVAILABILITY DAT HALF: %s" % ("PLAN MATCHES DISK"
                                     if not fails else "%d FAILURES" % len(fails)))
for f in fails:
    print("  FAILED: %s" % f)
sys.exit(1 if fails else 0)
