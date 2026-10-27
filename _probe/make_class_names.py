# -*- coding: utf-8 -*-
"""Export the unit-class names the attack_class sentence needs.

`nl._class_in` requires the class name to sit IMMEDIATELY AFTER 对, and that
position rule is load-bearing: matching a class name anywhere would fire on
"骑兵的血量改成1000", where the class is the ENTITY rather than the target of a
bonus. It also takes the longest name, so 攻城武器 does not lose to a prefix.

Output: `_golden/class_names.json`  ->  { "<class id>": ["中文名", "English"] }
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "_golden", "class_names.json")


def main():
    from aoe2mod.ui import nl
    table = nl.class_names()
    out = {str(k): list(v) for k, v in table.items()}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("wrote %s (%.1f KB), %d classes"
          % (OUT, os.path.getsize(OUT) / 1024.0, len(out)))
    for probe in ("0", "4", "23", "47"):
        if probe in out:
            print("  class %-4s %s" % (probe, out[probe][:3]))
    # The one the project's own example uses.
    for k, v in out.items():
        if "骑兵" in v:
            print("  骑兵 -> class", k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
