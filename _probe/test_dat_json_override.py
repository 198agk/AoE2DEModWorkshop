# -*- coding: utf-8 -*-
"""Has ANY mod ever demonstrated a `.dat`-layer JSON override working in game?

Why this question
-----------------
`unit.availability` and `tech.availability` write ONLY JSON under
`resources/_common/dat/`.  The 2026-10-14 in-game test of a rewritten
`CivTechTrees/BRITONS.json` had no effect, and two cheap explanations are now
refuted (depth, form/name).  Before narrowing further, ask a cheaper and more
general question:

    is there any mod in this corpus whose ONLY dat-layer content is JSON?

If every mod that touches `dat/` also ships a `.dat`, then no observation in
this corpus can attribute an in-game effect to a JSON override -- every
candidate effect is explainable by the `.dat` beside it.  That does not prove
JSON overrides fail; it proves the ability rests on an untested mechanism.

This is the same mistake the mechanism probes were built to catch: "the
mechanism is present" (three mods ship `linkedTechs.json`) is not "the mechanism
works" -- presence is not contrast.
"""
import io
import json
import os
import sys

MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
DAT_REL = os.path.join("resources", "_common", "dat")

FAILURES = []


def check(cond, label):
    print("[%s] %s" % ("PASS" if cond else "FAIL", label))
    if not cond:
        FAILURES.append(label)


def dat_layer_files(mod_dir):
    """Every file a mod places under the DAT storage root, with its name."""
    base = os.path.join(mod_dir, DAT_REL)
    out = []
    if not os.path.isdir(base):
        return out
    for dp, _dn, fns in os.walk(base):
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), base)
            out.append(rel)
    return sorted(out)


rows = []
for root, _dirs, files in os.walk(MODS):
    if "info.json" in files:
        rel = os.path.relpath(root, MODS)
        if rel == ".":
            continue
        rows.append((rel, dat_layer_files(root)))
rows.sort()

print("=" * 76)
print("every mod in the profile corpus that touches the DAT storage root")
print("=" * 76)
print("%-46s %-7s %-7s %s" % ("mod", "n .dat", "n json", "files"))
print("-" * 76)

dat_only = []
json_only = []
mixed = []
for name, fs in rows:
    if not fs:
        continue
    nd = sum(1 for f in fs if f.lower().endswith(".dat"))
    nj = len(fs) - nd
    print("%-46s %-7d %-7d %s" % (name[:46], nd, nj, fs))
    if nd and not nj:
        dat_only.append(name)
    elif nj and not nd:
        json_only.append(name)
    else:
        mixed.append(name)

print()
print("=" * 76)
print("A -- what the corpus can and cannot demonstrate")
print("=" * 76)
print("    mods with a .dat but no JSON under dat/ : %d  %s" % (len(dat_only), dat_only))
print("    mods with JSON but no .dat              : %d  %s" % (len(json_only), json_only))
print("    mods with BOTH                          : %d  %s" % (len(mixed), mixed))
check(len(rows) > 0, "the corpus was enumerated (%d mod(s) touch the DAT root)"
      % len(rows))

# The decisive shape: to attribute an effect to a JSON override, a mod must
# carry that JSON AND NOT a .dat (otherwise the .dat explains it).
print()
print("=" * 76)
print("B -- mods that would let us attribute an effect to JSON ALONE")
print("=" * 76)
clean = [n for n in json_only]
print("    candidates (JSON under dat/, no .dat) : %d  %s" % (len(clean), clean))
# "third-party" means a mod this project did NOT create.  It is NOT a name
# prefix test: the directory is `local\aoe2mod Smoke2 BuildPanel`, so
# `startswith("aoe2mod")` never matches and the check silently passes for the
# wrong reason.  Provenance is the containing folder.
third_party = [n for n in clean if n.lower().startswith("subscribed")]
print("    ...of which third-party               : %d  %s" % (len(third_party), third_party))
for n in clean:
    print("        %s -> %s" % (n, dict(rows)[n]))

# The one candidate is this project's own smoke test, whose only in-game run
# never started (the `.gpv` popup).  So it is not independent evidence either.
ours = [n for n in clean if n.lower().startswith("local")]
check(len(third_party) == 0 and len(clean) == len(ours),
      "the only JSON-only mod is this project's own, so the corpus holds no independent evidence")

# and the ones that DO ship JSON are all confounded by a .dat beside them
print()
print("=" * 76)
print("C -- the mods that ship dat-layer JSON, and their confound")
print("=" * 76)
for n, fs in rows:
    js = [f for f in fs if not f.lower().endswith(".dat")]
    if not js:
        continue
    nd = sum(1 for f in fs if f.lower().endswith(".dat"))
    print("    %s" % n)
    print("        json : %s" % js)
    print("        .dat : %d  -> %s" %
          (nd, "a .dat ships too, so any effect is ambiguous"
           if nd else "NO .dat -- this one WOULD be evidence"))

print()
print("=" * 76)
print("D -- are those shipped JSON files even different from the game's copy?")
print("=" * 76)
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
import hashlib


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


changed, identical, absent, compared = [], [], [], 0
for n, fs in rows:
    for f in fs:
        if f.lower().endswith(".dat"):
            continue
        compared += 1
        mine = os.path.join(MODS, n, DAT_REL, f)
        base = os.path.join(GAME, DAT_REL, f)
        if not os.path.exists(base):
            absent.append((n, f))
            print("    %-40s %-32s BASE MISSING" % (n[:40], f))
            continue
        a, b = sha(mine), sha(base)
        state = "identical to base" if a == b else "DIFFERS from base"
        (identical if a == b else changed).append((n, f))
        print("    %-40s %-32s %s  (%s vs %s)" % (n[:40], f, state, a, b))

print()
print("    dat-layer JSON files that differ from the game's copy : %d" % len(changed))
print("    ...that are byte-identical to the game's copy         : %d" % len(identical))
print("    ...with no base file to compare against               : %d" % len(absent))
check(len(changed) + len(identical) + len(absent) == compared,
      "every shipped dat-layer JSON was bucketed exactly once (%d compared)"
      % compared)
# A JSON file identical to base is not an override attempt at all.
for n, f in identical:
    print("        NOTE: %s ships %s unchanged -- not an override attempt" % (n, f))

print()
if FAILURES:
    print("FAILURES: %d" % len(FAILURES))
    for f in FAILURES:
        print("  - %s" % f)
    sys.exit(1)
print("DAT-LAYER JSON OVERRIDE: no mod in this corpus isolates a JSON override of")
print("the DAT storage layer -- every one that ships such JSON also ships the .dat")
print("that explains any observed effect.  So the JSON-override path (which is the")
print("ONLY path `unit.availability` and `tech.availability` have) rests on a")
print("mechanism no observation here has ever demonstrated.")
print("NOT PROVEN: that JSON overrides are ignored.  What is proven is that nothing")
print("in this corpus can show them working, so a positive result needs one.")
