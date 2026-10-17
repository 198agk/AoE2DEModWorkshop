"""Dump every storage point the engine declares, and where the flag lives.

`modes/Pompeii/Pompeii.json` is the only shipped file that lists storage points
(`storage_point_list`, 28 entries).  Two things matter for the 2026-10-14 null
result:

  1. WHAT the DAT entry says.  Does it carry `replace`?  Does it carry
     `use_modes_path_for_mods`, and is that flag unique to it?
  2. WHICH entries are known to be mod-overridable in the field.  `strings/` and
     `widgetui/` demonstrably are (the player's own working text and UI mods).
     So if the DAT entry is declared differently from those, that difference is
     the first thing to look at.

HONESTY: a declaration is not engine behaviour.  This prints the declarations
and the exe's own strings; it does not prove which path a mod's file is read
from.
"""

import json
import os
import re

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
POMPEII = os.path.join(ROOT, "modes", "Pompeii", "Pompeii.json")
EXE = os.path.join(ROOT, "AoE2DE_s.exe")


def main():
    d = json.load(open(POMPEII, encoding="utf-8"))
    sp = d["storage_point_list"]
    print("storage points declared by %s: %d" % (POMPEII, len(sp)))
    print()
    keys = {}
    for e in sp:
        for k in e:
            keys[k] = keys.get(k, 0) + 1
    print("key histogram: %s" % keys)
    print()
    print("%-22s %-8s %-46s %s" % ("type", "replace", "path", "other flags"))
    for e in sp:
        other = {k: v for k, v in e.items()
                 if k not in ("type", "replace", "path")}
        print("%-22s %-8s %-46s %s"
              % (e.get("type"), e.get("replace", "-"), e.get("path", ""),
                 json.dumps(other, ensure_ascii=False) if other else ""))

    flagged = [e.get("type") for e in sp if "use_modes_path_for_mods" in e]
    print()
    print("entries carrying use_modes_path_for_mods: %s" % (flagged or "none"))
    replaced = [e.get("type") for e in sp if e.get("replace")]
    print("entries carrying replace=true: %s" % (replaced or "none"))
    print()
    print("The storage points this project has FIELD EVIDENCE for:")
    print("   STRINGS  -- the player runs text mods; they take effect")
    print("   WIDGETUI -- the player runs texture/UI mods; they take effect")
    print("   DAT      -- our own smoke mod's empires2_x2_p1.dat took effect")
    print("These three are declared above; compare the DAT row to STRINGS/WIDGETUI")

    b = open(EXE, "rb").read()
    print()
    print("=" * 74)
    for needle in (b"use_modes_path_for_mods", b"storage_point_list"):
        n = b.count(needle)
        print("%-28r x%d" % (needle.decode(), n))
        i = b.find(needle)
        if i >= 0:
            lo, hi = max(0, i - 200), min(len(b), i + 220)
            print("   @0x%08x" % i)
            for m in re.finditer(rb"[\x20-\x7e]{3,}", b[lo:hi]):
                print("      0x%08x  %s" % (lo + m.start(), m.group().decode()))


if __name__ == "__main__":
    main()
