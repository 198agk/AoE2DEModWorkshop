# -*- coding: utf-8 -*-
"""Count the registered suites and name any probe nobody runs.

A registration list is a hand-maintained thing, so it drifts.  This prints the
count and, more usefully, the `test_*.py` files present in `_probe/` that no
runner names -- the same defect that let ten probes rot unrun before.

Four files are named `test_*.py` but are MEASUREMENTS, not assertions: they print
what they saw and exit 0 whether the news is good or bad.  Registering one in a
runner would add a suite that cannot fail -- exactly the "green pin telling the
opposite story" shape this project spent a round removing.  They are declared
below WITH the reason, and the reason is required: a newly orphaned test still
fails this probe, so the exemption list cannot quietly absorb the next one.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: path -> why this file is a measurement rather than a regression pin.  Every
#: entry must also say where its CONCLUSION lives, because a one-off dump with no
#: recorded conclusion is a file nobody can act on.
_NOT_A_SUITE = {
    r"_probe\datparse\test_random_maps.py":
        "prints the RandomMap record widths against genieutils and a synthetic "
        "round-trip; exits 0 either way.  Its conclusion (all five shipped "
        "datasets have count 0, so the reader/writer have no real data to fight) "
        "is recorded in 数据模组能力目录v1.md.",
    r"_probe\scenario_header\test_header_parse.py":
        "walks four shipped .aoe2scenario headers and tries four zlib window "
        "bits.  It prints `FAIL` for the three window bits that are SUPPOSED to "
        "fail, so a runner's FAIL scan would flag a healthy run.  Conclusion "
        "(the scenario body is raw deflate, -15) is in 数据模组能力目录v1.md.",
    r"_probe\schema\test_branch_extract.py":
        "regenerates regen_preview.json so a human can read what the AGE branch "
        "extractor saw; the checked-in tables beside it are built from that "
        "preview.  It has no pass/fail question to ask.",
    r"_probe\survey_scenario\test_asp_roundtrip.py":
        "needs the third-party AoE2ScenarioParser package, which is not "
        "installed in this project's runtime -- it raises ModuleNotFoundError.  "
        "A test that cannot import its subject must not be registered as green.",
}


def named_in(path):
    try:
        text = io.open(path, encoding="utf-8").read()
    except IOError:
        return set()
    return set(re.findall(r"([\w./\\-]+\.py)", text))


def main():
    fast = os.path.join(HERE, "run_suites.py")
    slow = os.path.join(HERE, "run_long.py")
    fast_text = io.open(fast, encoding="utf-8").read()
    body = fast_text.split("SUITES = [", 1)[1].split("]", 1)[0]
    entries = re.findall(r'r"([^"]+)"', body)
    print("run_suites.py registers %d suites" % len(entries))

    dupes = [e for e in set(entries) if entries.count(e) > 1]
    print("duplicates: %s" % (dupes or "none"))

    registered = named_in(fast) | named_in(slow)
    present = set()
    for dirpath, _dirs, files in os.walk(HERE):
        if os.path.basename(dirpath) == "team":
            continue
        for fn in files:
            if fn.startswith("test_") and fn.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                present.add(rel.replace(os.sep, "\\"))

    missing_file = [e for e in entries
                    if not os.path.exists(os.path.join(ROOT, e))]
    print("registered but not on disk: %s" % (missing_file or "none"))

    registered_base = {os.path.basename(r) for r in registered}
    unrun = sorted(p for p in present
                   if os.path.basename(p) not in registered_base
                   and p not in _NOT_A_SUITE)
    excused = sorted(p for p in present
                     if os.path.basename(p) not in registered_base
                     and p in _NOT_A_SUITE)
    print("\n%d test_*.py files exist; %d are named by a runner"
          % (len(present), len(present) - len(unrun) - len(excused)))
    print("declared as measurements, not suites (%d):" % len(excused))
    for p in excused:
        print("  %s -- %s" % (p, _NOT_A_SUITE[p]))
    # An exemption for a file that is gone, or that a runner now names, is a
    # stale claim: it would keep excusing nothing while looking like it explains
    # something.  Same rule as the sweep's _VERIFIED_ELSEWHERE table.
    stale = sorted(p for p in _NOT_A_SUITE
                   if p not in present
                   or os.path.basename(p) in registered_base)
    if stale:
        print("\nSTALE EXEMPTIONS (drop them): %s" % stale)
        return 1
    if unrun:
        print("NOT NAMED BY ANY RUNNER (%d):" % len(unrun))
        for p in unrun:
            print("  %s" % p)
        return 1
    print("every test_*.py is either reachable from a runner or declared a "
          "measurement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
