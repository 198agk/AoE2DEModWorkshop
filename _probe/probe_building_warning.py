"""What warning does the user actually get when the inherited building is
unreachable from the RECEIVER?

`probe_building_reach.py` measured 1,659 unit grants and 253 tech grants where
the copied `Building ID` appears nowhere in the receiving civ's tree -- so the
granted thing has no place to be produced. No donor choice fixes most of it
(0 fixable in the unit space), so it is inherent to the data and the honest
product move is to SAY SO rather than to pick cleverer.

`grant` already emits `inherited Building ID=45 from the donor row` (Chinese
since 2026-10-20: 「建筑编号」是从捐赠方那一行照抄下来的). This prints that warning
next to what the receiver can actually reach, to decide whether the generic
wording is enough or the change is worth a receiver-aware sentence.

Read-only.  Prints, asserts nothing.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    trees = CT.load_trees(GAME)
    civs = sorted(trees)

    # find a concrete unreachable case in the unit space and in the tech space
    for label, ut, rowfn in (("Unit", CT.UNIT_USE_TYPES, CT.unit_rows),
                             ("Tech", CT.TECH_USE_TYPES, CT.tech_rows)):
        nodes = sorted({r.get("Node ID") for c in civs for r in rowfn(trees[c])
                        if isinstance(r.get("Node ID"), int)})
        print("\n=== %s space ===" % label)
        shown = 0
        for n in nodes:
            dc, donor = CT.donor_row(trees, n, use_types=ut)
            if donor is None:
                continue
            db = str(donor.get("Building ID"))
            for civ in civs:
                if CT.can_build(trees[civ], n, ut):
                    continue
                mine = {str(r.get("Node ID")) for r in CT.rows_of(trees[civ])}
                if db in mine:
                    continue
                # this is an unreachable case -- see the warnings the product gives
                probe = {k: (list(v) if isinstance(v, list) else v)
                         for k, v in trees[civ].items()}
                probe.pop("path", None)
                _row, warns = CT.grant(probe, n, donor, use_types=ut)
                print("  receiver %-14s node %-5d donor %-12s Building ID=%s"
                      % (civ, n, dc, db))
                print("    warnings the user sees: %s" % warns)
                print("    buildings the receiver reaches: %s"
                      % sorted(mine)[:12])
                shown += 1
                break
            if shown >= 3:
                break
        print("  (shown %d)" % shown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
