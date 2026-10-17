"""Print readable exe context around every DAT-layer path template.

Purpose: the in-game test of 2026-10-14 showed a mod-supplied
`resources/_common/dat/CivTechTrees/BRITONS.json` had NO effect while the
`.dat` in the same mod did.  The question is WHERE the engine looks for a
mod's copy of a DAT-storage-point file -- so we need the exact strings and
their neighbours, printed readably rather than as raw bytes.
"""

import os
import re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"

NEEDLES = [
    b"CivTechTrees/%s.json",
    b"civTechTrees.json",
    b"futuravailableunits.json",
    b"paphosfutureavailableunits.json",
    b"civilizations.json",
    b"linkedTechs.json",
    b"resources\\_common\\dat",
    b"resources/_common/dat",
    b"empires2_x2_p1.dat",
    b"use_modes_path_for_mods",
    b"storage_point_list",
    b"_common\\dat",
]

RUN = re.compile(rb"[\x20-\x7e]{4,}")


def runs_near(b, i, before=300, after=400):
    """Printable runs in the window around offset i."""
    lo = max(0, i - before)
    hi = min(len(b), i + after)
    out = []
    for m in RUN.finditer(b[lo:hi]):
        s = m.group().decode("ascii", "replace")
        out.append((lo + m.start(), s))
    return out


def main():
    b = open(EXE, "rb").read()
    print("exe %d B" % len(b))
    for needle in NEEDLES:
        n = b.count(needle)
        print()
        print("=" * 78)
        print("%-36r x%d" % (needle.decode("ascii", "replace"), n))
        if not n:
            continue
        i = 0
        shown = 0
        while shown < 2:
            i = b.find(needle, i)
            if i < 0:
                break
            print("  @0x%08x" % i)
            for off, s in runs_near(b, i):
                mark = ">>" if i >= off and i < off + len(s) else "  "
                print("    %s 0x%08x  %s" % (mark, off, s[:200]))
            i += 1
            shown += 1


if __name__ == "__main__":
    main()
