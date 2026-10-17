"""Does the .dat ever name an `_x2` file, or is the x2 half derived?"

The v13 probe reported that 233 of 466 target names are never named by a
graphics record -- exactly half, which smells like the x2 siblings rather than
waste.  If records only ever name `_x1` and the engine appends `_x2`, then:
  * a copy-based reskin must ship BOTH (the engine will ask for x2), which is
    what v12 did, so those 233 files are not waste at all;
  * a retarget-based reskin needs the donor's `_x2` to exist on disk, which it
    does because the donor is shipped art.
This distinguishes the two and fixes a claim before it reaches a report.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402

def main():
    tk = A.open_toolkit()
    tk._ensure()
    names = [(g.get("file") or "") for g in tk._stats["graphics"]]
    names = [n for n in names if n]
    x1 = [n for n in names if n.endswith("_x1")]
    x2 = [n for n in names if n.endswith("_x2")]
    other = [n for n in names if not (n.endswith("_x1") or n.endswith("_x2"))]
    print("records with a file string: %d" % len(names))
    print("  ending _x1: %d" % len(x1))
    print("  ending _x2: %d   <-- if 0, x2 is DERIVED, never named" % len(x2))
    print("  neither   : %d  e.g. %s" % (len(other), other[:4]))
    # For every named _x1, does the _x2 sibling exist on disk?
    import aoe2mod.game.sprites as SP
    gdir = SP.graphics_dir(tk.game_root)
    on_disk = set(SP.disk_files(tk.game_root))
    miss = [n for n in x1 if (n[:-3] + "_x2") not in on_disk]
    print("named _x1 files whose _x2 sibling is MISSING on disk: %d" % len(miss))
    return 0


if __name__ == "__main__":
    sys.exit(main())
