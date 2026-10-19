# -*- coding: utf-8 -*-
"""probe_icon_sections.py -- the raw shape of icons.json's two unit sections.

The tie-break probe (`probe_icon_section_rule.py`) assumed `Units` owns 000-999
and `Buildings` owns 000-116.  A leftover line contradicted that (`BuildingIcons`
keys seemed to run past 999), so this probe stops guessing and prints:

  * every section, its key count, and its key RANGE (as integers),
  * the value forms, so the caller knows when a material name is a UNIT material
    sitting in the Buildings section (the case `a33_icons_resolve.py` flagged),
  * the overlap count per section pair.

No conclusions -- just the shape, so the product code can be written against it.
"""
from __future__ import print_function

import codecs
import io
import json
import os
import re
import sys

WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
_MAT_RE = re.compile(r"^(Unit|Building|Icon)icons?(\d+)(.*)$", re.I)


def main():
    with io.open(os.path.join(WID, "icons.json"), encoding="utf-8-sig") as fh:
        icons = json.load(fh)

    print("sections: %d" % len(icons))
    unit_sections = {}
    for name in sorted(icons):
        sec = icons[name] or {}
        keys = [k for k in sec]
        nums = sorted(int(k) for k in keys if str(k).isdigit())
        srcs = {}
        for k in keys:
            v = sec[k]
            m = _MAT_RE.match(v or "")
            srcs[m.group(1).lower() if m else "(other)"] = \
                srcs.get(m.group(1).lower() if m else "(other)", 0) + 1
        print("\n  %-24s keys=%-5d numeric=%-5d range=%s"
              % (name, len(keys), len(nums),
                 ("%d..%d" % (nums[0], nums[-1])) if nums else "-"))
        print("      value kinds: %s" % ", ".join("%s=%d" % kv for kv in sorted(srcs.items())))
        if name in ("Units", "Buildings"):
            unit_sections[name] = sec

    u = unit_sections.get("Units") or {}
    b = unit_sections.get("Buildings") or {}
    uo, bo = set(u) & set(b), None
    print("\nUnits/Buildings overlap: %d keys" % len(uo))
    over_999_u = sorted(int(k) for k in u if k.isdigit() and int(k) > 999)
    over_999_b = sorted(int(k) for k in b if k.isdigit() and int(k) > 999)
    print("  Units keys > 999: %d %s" % (len(over_999_u), over_999_u[:12]))
    print("  Buildings keys > 999: %d %s" % (len(over_999_b), over_999_b[:12]))

    # the specific claim a33 made: a UNIT material inside the Buildings section
    inside = [(k, b[k]) for k in sorted(b) if str(b[k]).lower().startswith("uniticon")]
    print("\n  Buildings entries whose value is a UNIT material: %d" % len(inside))
    for k, v in inside[:14]:
        print("    %-5s -> %s" % (k, v))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
