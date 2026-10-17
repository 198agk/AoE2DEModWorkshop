"""Is a Chronicles civ systematically the donor, and is the Building ID real?

Two follow-ups on `probe_tech_donor_choice.py`:

1. `donor_row` picks `ready[0]` = the alphabetically first civ that already has
   the tech.  `ACHAEMENIDS` sorts first among the 62, and ACHAEMENIDS is one of
   the six Chronicles civilizations, which the earlier name-id work showed use
   the alternate `405xxx`/`407xxx` localisation block.  If ACHAEMENIDS is the
   donor for most grants, every granted tech inherits Chronicles row data.  That
   is a *systematic* bias hiding inside a rule that reads as neutral.

2. The `Building ID` mismatch (351 of 10369): does the receiving civ's tree
   even CONTAIN that building?  A tech filed under a building the civ cannot
   build is unreachable, not merely mis-decorated.  Check the receiver's own
   tech-tree layer for the building node, in either list.

Read-only.  Prints measurements, asserts nothing.
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TU = CT.TECH_USE_TYPES
CHRONICLES = ("ACHAEMENIDS", "ATHENIANS", "MACEDONIANS", "PURU", "SPARTANS",
              "THRACIANS")


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)
    nodes = sorted({r.get("Node ID") for c in civs
                    for r in CT.tech_rows(trees[c])
                    if isinstance(r.get("Node ID"), int)})

    # --- 1. who is the donor, across every grant the UI could offer? ---
    donors = collections.Counter()
    chron_grant = chron_total = 0
    for n in nodes:
        c, _r = CT.donor_row(trees, n, use_types=TU)
        if c is None:
            continue
        for civ in civs:
            if CT.can_build(trees[civ], n, TU):
                continue
            donors[c] += 1
            chron_total += 1
            if c in CHRONICLES:
                chron_grant += 1
    print("grants offered by the UI: %d" % chron_total)
    print("donors chosen (top 12): %s" % donors.most_common(12))
    print("  ... where the donor is a CHRONICLES civ: %d (%.1f%%)"
          % (chron_grant, 100.0 * chron_grant / max(1, chron_total)))
    print("  distinct civs ever chosen as donor: %d of %d"
          % (len(donors), len(civs)))
    never = [c for c in civs if c not in donors]
    print("  civs that would NEVER be chosen as a donor: %d %s"
          % (len(never), never))

    # --- 2. is the mismatched Building ID a building the receiver lacks? ---
    print("\n--- building reachability ---")
    real, benign, nobs = 0, 0, 0
    samples = []
    for n in nodes:
        dc, donor = CT.donor_row(trees, n, use_types=TU)
        if donor is None:
            continue
        db = str(donor.get("Building ID"))
        for civ in civs:
            if CT.can_build(trees[civ], n, TU):
                continue
            mine = CT.tech_rows(trees[civ])
            bs = {str(r.get("Building ID")) for r in mine}
            if not bs or db in bs:
                continue
            # does this civ's tree contain that building at all?
            allrows = CT.rows_of(trees[civ])
            has_bldg = any(str(r.get("Node ID")) == db and
                           r.get("Use Type") == "Building" for r in allrows)
            # also accept it appearing as any node id in the tree
            has_any = any(str(r.get("Node ID")) == db for r in allrows)
            if has_bldg or has_any:
                benign += 1
            else:
                real += 1
                if len(samples) < 10:
                    samples.append((civ, n, db, has_any))
    print("Building ID not among its own tech rows: %d" % (real + benign))
    print("  ... but the building IS elsewhere in its tree (cosmetic): %d"
          % benign)
    print("  ... and the building is ABSENT from its tree entirely: %d" % real)
    for civ, n, db, _ in samples:
        print("   %-14s node %-5d Building ID=%s -- not in its tree" % (civ, n, db))

    # --- 3. what would a smarter rule pick? ---
    # Majority variant instead of "alphabetically first able civ".
    print("\n--- majority-variant rule ---")
    maj_bad = 0
    for n in nodes:
        rows = [(c, CT.row_for(trees[c], n, TU)) for c in civs]
        rows = [(c, r) for c, r in rows if r is not None]
        if not rows:
            continue
        keys = collections.Counter(
            tuple(sorted((k, str(v)) for k, v in r.items()
                         if k != "Node Status")) for _c, r in rows)
        top = keys.most_common(1)[0][0]
        rep = None
        for c, r in rows:
            if tuple(sorted((k, str(v)) for k, v in r.items()
                            if k != "Node Status")) == top:
                rep = (c, r)
                break
        db = str(rep[1].get("Building ID"))
        for civ in civs:
            if CT.can_build(trees[civ], n, TU):
                continue
            bs = {str(r.get("Building ID")) for r in CT.tech_rows(trees[civ])}
            if bs and db not in bs:
                maj_bad += 1
    print("Building ID mismatches under MAJORITY donor: %d" % maj_bad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
